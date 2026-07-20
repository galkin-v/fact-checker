from conftest import FakeGateway
from fastapi.testclient import TestClient

from fact_checker.api import create_app
from fact_checker.config import Settings


def test_fact_check_endpoint(settings: Settings) -> None:
    gateway = FakeGateway(
        '[{"question":"Какова стоимость?","verdict":1,"comment":"Неверная цена."}]'
    )
    app = create_app(settings=settings, gateway=gateway)

    with TestClient(app) as client:
        response = client.post(
            "/v1/fact-check",
            headers={"X-Request-ID": "header-id"},
            json={"product": "card", "text": "Клиент и сотрудник обсуждают стоимость."},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "header-id"
    assert response.json()["request_id"] == "header-id"
    assert response.json()["violations"][0]["checklist_id"] == 7
    assert gateway.closed is True


def test_unknown_product_returns_stable_error(settings: Settings) -> None:
    app = create_app(settings=settings, gateway=FakeGateway())

    with TestClient(app) as client:
        response = client.post("/v1/fact-check", json={"product": "none", "text": "Диалог"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "product_not_found"
    assert response.json()["request_id"]


def test_body_request_id_takes_precedence(settings: Settings) -> None:
    app = create_app(settings=settings, gateway=FakeGateway())

    with TestClient(app) as client:
        response = client.post(
            "/v1/fact-check",
            headers={"X-Request-ID": "header-id"},
            json={"product": "card", "text": "Диалог", "request_id": "body-id"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "body-id"
    assert response.json()["request_id"] == "body-id"


def test_readiness_reflects_model_state(settings: Settings) -> None:
    app = create_app(settings=settings, gateway=FakeGateway(ready=False))

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
