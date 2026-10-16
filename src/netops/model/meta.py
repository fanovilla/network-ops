from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .enums import Side


class Provenance(BaseModel):
    side: Side = Side.declared
    source: str | None = None
    collected_at: datetime | None = None
    status: str = Field(default="ok", pattern="^(ok|degraded|failed)$")