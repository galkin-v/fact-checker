from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
Transcript = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100_000)
]
RequestId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class FactCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product: ProductName
    text: Transcript
    request_id: RequestId | None = None


class Violation(BaseModel):
    model_config = ConfigDict(frozen=True)

    checklist_id: int
    question: str
    expected_answer: str
    explanation: str


class FactCheckResponse(BaseModel):
    request_id: str
    product: str
    checklist_version: str
    model: str
    status: Literal["complete", "degraded"]
    violations: list[Violation]
    warnings: list[str] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str
