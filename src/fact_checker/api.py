import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import RequestResponseEndpoint

from fact_checker import __version__
from fact_checker.catalog import ChecklistCatalog, ProductNotFoundError
from fact_checker.checker import FactChecker
from fact_checker.config import Settings, get_settings
from fact_checker.logging_config import configure_logging
from fact_checker.model_client import ModelGateway, ModelGatewayError, OpenAIModelGateway
from fact_checker.schemas import ErrorDetail, ErrorResponse, FactCheckRequest, FactCheckResponse

logger = logging.getLogger(__name__)

REQUESTS = Counter(
    "fact_checker_http_requests_total",
    "HTTP requests processed by the service",
    ("method", "path", "status"),
)
LATENCY = Histogram(
    "fact_checker_http_request_duration_seconds",
    "HTTP request latency",
    ("method", "path"),
)


def _error(request: Request, status: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(code=code, message=message),
        request_id=request.state.request_id,
    )
    return JSONResponse(status_code=status, content=payload.model_dump())


def create_app(
    settings: Settings | None = None,
    gateway: ModelGateway | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        catalog = ChecklistCatalog.from_path(resolved_settings.checklist_path)
        model_gateway = gateway or OpenAIModelGateway(resolved_settings)
        app.state.catalog = catalog
        app.state.gateway = model_gateway
        app.state.checker = FactChecker(catalog, model_gateway)
        logger.info(
            "service_started",
            extra={
                "checklist_version": catalog.version,
                "product_count": catalog.product_count,
                "model": model_gateway.model_id,
            },
        )
        try:
            yield
        finally:
            await model_gateway.close()
            logger.info("service_stopped")

    application = FastAPI(
        title="Fact Checker API",
        summary="Checklist-grounded fact checking for consultation transcripts",
        version=__version__,
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id[:128]
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            elapsed = time.perf_counter() - started
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            REQUESTS.labels(request.method, path, str(status)).inc()
            LATENCY.labels(request.method, path).observe(elapsed)
            logger.info(
                "request_completed",
                extra={
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "path": path,
                    "status": status,
                    "duration_ms": round(elapsed * 1000, 2),
                },
            )
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @application.exception_handler(ProductNotFoundError)
    async def product_not_found(request: Request, error: ProductNotFoundError) -> JSONResponse:
        return _error(request, 404, "product_not_found", str(error))

    @application.exception_handler(ModelGatewayError)
    async def model_unavailable(request: Request, error: ModelGatewayError) -> JSONResponse:
        logger.error(
            "model_request_failed",
            extra={"request_id": request.state.request_id, "reason": str(error)},
        )
        return _error(request, 503, "model_unavailable", "fact-checking model is unavailable")

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        validation_issues = [
            {"type": issue["type"], "location": issue["loc"]} for issue in error.errors()
        ]
        logger.info(
            "request_rejected",
            extra={"request_id": request.state.request_id, "errors": validation_issues},
        )
        return _error(request, 422, "invalid_request", "request body failed validation")

    @application.get("/health/live", include_in_schema=False)
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", include_in_schema=False)
    async def readiness(request: Request) -> Response:
        model_gateway = cast(ModelGateway, request.app.state.gateway)
        if await model_gateway.ready():
            return JSONResponse({"status": "ready"})
        return JSONResponse({"status": "not_ready"}, status_code=503)

    @application.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @application.post(
        "/v1/fact-check",
        response_model=FactCheckResponse,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def fact_check(payload: FactCheckRequest, request: Request) -> FactCheckResponse:
        request_id = payload.request_id or request.state.request_id
        request.state.request_id = request_id
        checker = cast(FactChecker, request.app.state.checker)
        return await checker.check(payload.product, payload.text, request_id)

    return application


app = create_app()
