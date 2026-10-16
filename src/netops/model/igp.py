from __future__ import annotations

from pydantic import BaseModel, Field


class OspfArea(BaseModel):
    id: str
    metric: int = Field(default=1, ge=1)


class DeviceIgp(BaseModel):
    protocol: str = Field(default="ospf", pattern="^(ospf|isis)$")
    areas: list[str] = Field(default_factory=list)