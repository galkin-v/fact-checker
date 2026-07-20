from pathlib import Path

from conftest import FakeGateway

from fact_checker.catalog import ChecklistCatalog
from fact_checker.checker import CompletionParser, FactChecker


def test_parser_repairs_json_without_claiming_full_quality() -> None:
    parsed = CompletionParser().parse('[{"question":"Q","verdict":1,}]')

    assert parsed.results[0].question == "Q"
    assert parsed.degraded is True
    assert "model_output_repaired" in parsed.warnings


async def test_checker_maps_exact_question_to_id(checklist_path: Path) -> None:
    gateway = FakeGateway(
        '[{"question":"Какова стоимость?","verdict":1,'
        '"comment":"Названа неверная цена."},'
        '{"question":"Каков срок?","verdict":0,"comment":"Срок верный."}]'
    )
    checker = FactChecker(ChecklistCatalog.from_path(checklist_path), gateway)

    response = await checker.check("card", "Диалог", "req-1")

    assert response.status == "complete"
    assert [item.checklist_id for item in response.violations] == [7]
    assert response.violations[0].expected_answer == "Бесплатно."
    assert gateway.messages is not None
    assert '"question": "Какова стоимость?"' in gateway.messages[1]["content"]
    assert '"id"' not in gateway.messages[1]["content"]


async def test_checker_ignores_hallucinated_question(checklist_path: Path) -> None:
    gateway = FakeGateway('[{"question":"Выдуманный пункт","verdict":1,"comment":"Ошибка."}]')
    checker = FactChecker(ChecklistCatalog.from_path(checklist_path), gateway)

    response = await checker.check("card", "Диалог", "req-2")

    assert response.violations == []
    assert response.status == "degraded"
    assert response.warnings == ["model_returned_unknown_questions"]


async def test_checker_deduplicates_violations(checklist_path: Path) -> None:
    gateway = FakeGateway(
        '[{"question":"Какова стоимость?","verdict":1,"comment":"Первая."},'
        '{"question":"Какова стоимость?","verdict":1,"comment":"Вторая."}]'
    )
    checker = FactChecker(ChecklistCatalog.from_path(checklist_path), gateway)

    response = await checker.check("card", "Диалог", "req-3")

    assert len(response.violations) == 1
    assert response.violations[0].explanation == "Первая."
