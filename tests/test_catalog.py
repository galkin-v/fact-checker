import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fact_checker.catalog import ChecklistCatalog, ProductNotFoundError


def test_catalog_loads_version_and_product(checklist_path: Path) -> None:
    catalog = ChecklistCatalog.from_path(checklist_path)

    assert catalog.version == "test-v1"
    assert catalog.product_count == 1
    assert [item.id for item in catalog.get("card")] == [7, 8]


def test_catalog_rejects_duplicate_questions(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(
        json.dumps(
            {
                "version": "v1",
                "products": {
                    "card": [
                        {"id": 1, "question": "Same", "answer": "A"},
                        {"id": 2, "question": "Same", "answer": "B"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate questions"):
        ChecklistCatalog.from_path(path)


def test_unknown_product_is_explicit(checklist_path: Path) -> None:
    catalog = ChecklistCatalog.from_path(checklist_path)

    with pytest.raises(ProductNotFoundError):
        catalog.get("missing")
