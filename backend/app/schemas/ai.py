from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

WorkflowAction = Literal[
    "goto", "fill", "click", "select", "check", "press", "wait", "assert", "custom"
]
CaseAction = Literal[
    "goto", "fill", "click", "select", "check", "uncheck", "press", "wait", "assert", "custom"
]
AssertionType = Literal[
    "url", "title", "text", "element_visible", "element_text", "value", "count", "custom"
]
AssertionSource = Literal["user_requirement", "observed_page", "model_inference"]


class WorkflowStep(BaseModel):
    step_no: int = Field(ge=1)
    page_id: int | None = None
    action: WorkflowAction
    target: str = Field(min_length=1)
    value: str | None = None
    description: str | None = None


class WorkflowItem(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str = Field(default="")
    steps: list[WorkflowStep] = Field(min_length=1, max_length=30)
    involved_page_ids: list[int] = Field(default_factory=list)
    uncertainty: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class WorkflowAnalysisResult(BaseModel):
    workflows: list[WorkflowItem] = Field(default_factory=list, max_length=10)


class CaseStep(BaseModel):
    step_no: int = Field(ge=1)
    page_reference: str | None = None
    action: CaseAction
    target: str = Field(min_length=1)
    value: str | None = None
    description: str | None = None


class CaseAssertion(BaseModel):
    assertion_type: AssertionType
    target: str = Field(min_length=1)
    expected: Any = None
    source: AssertionSource
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class CaseItem(BaseModel):
    case_code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=512)
    module: str | None = Field(default=None, max_length=128)
    priority: Literal["P0", "P1", "P2", "P3"] = "P2"
    preconditions: list[str] = Field(default_factory=list)
    related_page_ids: list[int] = Field(default_factory=list)
    steps: list[CaseStep] = Field(min_length=1, max_length=30)
    test_data: dict[str, Any] = Field(default_factory=dict)
    expected_result: str = ""
    assertions: list[CaseAssertion] = Field(min_length=1, max_length=20)
    assumptions: list[str] = Field(default_factory=list)


class CaseGenerationResult(BaseModel):
    cases: list[CaseItem] = Field(default_factory=list, max_length=20)


class ScriptGenerationResult(BaseModel):
    filename: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=60000)
    notes: str = ""
    assumptions: list[str] = Field(default_factory=list)


class InferredCause(BaseModel):
    cause: str = Field(min_length=1, max_length=1000)
    evidence: str = Field(default="", max_length=2000)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class FailureAnalysisResult(BaseModel):
    observed_error: str = Field(min_length=1, max_length=4000)
    inferred_causes: list[InferredCause] = Field(default_factory=list, max_length=10)
    suggestions: list[str] = Field(default_factory=list, max_length=10)
    needs_more_info: bool = False
