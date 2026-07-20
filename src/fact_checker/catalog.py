import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChecklistItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int = Field(ge=1)
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=8000)


class ChecklistDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(min_length=1, max_length=128)
    products: dict[str, tuple[ChecklistItem, ...]]

    @model_validator(mode="after")
    def validate_products(self) -> "ChecklistDocument":
        if not self.products:
            raise ValueError("the checklist must contain at least one product")

        for product, items in self.products.items():
            if not product.strip():
                raise ValueError("product keys must not be blank")
            if not items:
                raise ValueError(f"product {product!r} has no checklist items")

            ids = [item.id for item in items]
            questions = [item.question for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"product {product!r} contains duplicate IDs")
            if len(questions) != len(set(questions)):
                raise ValueError(f"product {product!r} contains duplicate questions")
        return self


class ProductNotFoundError(LookupError):
    def __init__(self, product: str) -> None:
        self.product = product
        super().__init__(f"unknown product: {product}")


class ChecklistCatalog:
    def __init__(self, document: ChecklistDocument) -> None:
        self._document = document

    @classmethod
    def from_path(cls, path: Path) -> "ChecklistCatalog":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise RuntimeError(f"checklist file does not exist: {path}") from error
        except json.JSONDecodeError as error:
            raise RuntimeError(f"checklist file is not valid JSON: {path}: {error}") from error
        return cls(ChecklistDocument.model_validate(raw))

    @property
    def version(self) -> str:
        return self._document.version

    @property
    def product_count(self) -> int:
        return len(self._document.products)

    def get(self, product: str) -> tuple[ChecklistItem, ...]:
        try:
            return self._document.products[product]
        except KeyError as error:
            raise ProductNotFoundError(product) from error
