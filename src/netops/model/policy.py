from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import PolicyAction


class PrefixListEntry(BaseModel):
    prefix: str
    ge: int | None = None
    le: int | None = None


class PrefixList(BaseModel):
    name: str
    entries: list[PrefixListEntry] = Field(default_factory=list)


class AsPathFilter(BaseModel):
    name: str
    regex: str


class CommunityList(BaseModel):
    name: str
    communities: list[str] = Field(default_factory=list)


class PolicyMatch(BaseModel):
    prefix_list: str | None = None
    as_path_filter: str | None = None
    community_list: str | None = None


class PolicySet(BaseModel):
    local_pref: int | None = None
    med: int | None = None
    communities: list[str] | None = None
    as_path_prepend: int = 0
    weight: int | None = None


class PolicyStatement(BaseModel):
    order: int
    action: PolicyAction
    match: PolicyMatch | None = None
    set: PolicySet | None = None


class RoutePolicy(BaseModel):
    name: str
    statements: list[PolicyStatement] = Field(default_factory=list)