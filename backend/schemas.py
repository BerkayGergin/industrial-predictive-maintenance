from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FaultCommand(BaseModel):
    mode: Literal["NONE", "BEARING_WEAR", "MISALIGNMENT", "OVERLOAD", "COOLING_FAILURE"]
    intensity: float = Field(default=1.0, ge=0.0, le=1.0)


class LoadCommand(BaseModel):
    target_load: float = Field(
        description="-1 selects the automatic production load profile; otherwise 0..100 percent.",
        ge=-1.0,
        le=100.0,
    )


class RunningCommand(BaseModel):
    running: bool


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(default="operator", min_length=1, max_length=80)
