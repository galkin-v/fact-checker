import json
from dataclasses import dataclass
from typing import Any, Literal

from json_repair import repair_json
from pydantic import BaseModel, ConfigDict, ValidationError

from fact_checker.catalog import ChecklistCatalog
from fact_checker.model_client import ModelGateway
from fact_checker.prompts import build_messages
from fact_checker.schemas import FactCheckResponse, Violation


class JudgeResult(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    question: str
    verdict: Literal[0, 1]
    comment: str = ""
    algo_trace: dict[str, Any] | None = None


@dataclass(frozen=True)
class ParsedCompletion:
    results: list[JudgeResult]
    degraded: bool
    warnings: list[str]


class CompletionParser:
    def parse(self, raw: str) -> ParsedCompletion:
        warnings: list[str] = []
        degraded = False

        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            try:
                value = repair_json(raw, return_objects=True)
            except Exception:  # json-repair may raise several parser-specific errors
                value = None
            degraded = True
            warnings.append("model_output_repaired")

        if isinstance(value, dict):
            value = [value]
            degraded = True
            warnings.append("model_output_was_not_an_array")

        if not isinstance(value, list):
            if "model_output_unparseable" not in warnings:
                warnings.append("model_output_unparseable")
            return ParsedCompletion(
                results=[],
                degraded=True,
                warnings=warnings,
            )

        results: list[JudgeResult] = []
        for entry in value:
            try:
                results.append(JudgeResult.model_validate(entry))
            except ValidationError:
                degraded = True
                if "model_output_contains_invalid_entries" not in warnings:
                    warnings.append("model_output_contains_invalid_entries")

        return ParsedCompletion(results=results, degraded=degraded, warnings=warnings)


class FactChecker:
    def __init__(
        self,
        catalog: ChecklistCatalog,
        gateway: ModelGateway,
        parser: CompletionParser | None = None,
    ) -> None:
        self._catalog = catalog
        self._gateway = gateway
        self._parser = parser or CompletionParser()

    async def check(self, product: str, text: str, request_id: str) -> FactCheckResponse:
        items = self._catalog.get(product)
        item_by_question = {item.question: item for item in items}
        raw = await self._gateway.complete(build_messages(text, items))
        parsed = self._parser.parse(raw)

        warnings = list(parsed.warnings)
        degraded = parsed.degraded
        violations_by_id: dict[int, Violation] = {}

        for result in parsed.results:
            item = item_by_question.get(result.question)
            if item is None:
                degraded = True
                if "model_returned_unknown_questions" not in warnings:
                    warnings.append("model_returned_unknown_questions")
                continue
            if result.verdict != 1 or item.id in violations_by_id:
                continue

            explanation = result.comment.strip()
            if not explanation:
                degraded = True
                explanation = "Ответ в диалоге противоречит эталонному пункту чеклиста."
                if "model_output_missing_explanations" not in warnings:
                    warnings.append("model_output_missing_explanations")

            violations_by_id[item.id] = Violation(
                checklist_id=item.id,
                question=item.question,
                expected_answer=item.answer,
                explanation=explanation,
            )

        return FactCheckResponse(
            request_id=request_id,
            product=product,
            checklist_version=self._catalog.version,
            model=self._gateway.model_id,
            status="degraded" if degraded else "complete",
            violations=sorted(violations_by_id.values(), key=lambda item: item.checklist_id),
            warnings=warnings,
        )
