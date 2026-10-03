"""Existing binary route contract; no provider, environment or filesystem IO."""

from typing import Literal

from pydantic import BaseModel, Field


class RouterDecision(BaseModel):
    task_type: Literal["qa", "summarize"]
    confidence: float = Field(strict=True, ge=0, le=1, allow_inf_nan=False)
    reasoning: str
