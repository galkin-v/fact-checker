from collections.abc import Sequence
from pathlib import Path

import pytest

from fact_checker.config import Settings


class FakeGateway:
    model_id = "test/model"

    def __init__(self, completion: str = "[]", ready: bool = True) -> None:
        self.completion = completion
        self.is_ready = ready
        self.messages: Sequence[dict[str, str]] | None = None
        self.closed = False

    async def complete(self, messages: Sequence[dict[str, str]]) -> str:
        self.messages = messages
        return self.completion

    async def ready(self) -> bool:
        return self.is_ready

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def checklist_path(tmp_path: Path) -> Path:
    path = tmp_path / "checklists.json"
    path.write_text(
        """{
          "version": "test-v1",
          "products": {
            "card": [
              {"id": 7, "question": "Какова стоимость?", "answer": "Бесплатно."},
              {"id": 8, "question": "Каков срок?", "answer": "Один день."}
            ]
          }
        }""",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def settings(checklist_path: Path) -> Settings:
    return Settings(
        checklist_path=checklist_path,
        model_base_url="http://model.test/v1",
        model_id="test/model",
        model_api_key="test-token",
    )
