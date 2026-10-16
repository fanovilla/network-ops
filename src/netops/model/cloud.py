from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import InterconnectKind


class CloudProvider(BaseModel):
    name: str
    asn: int


class CloudRegion(BaseModel):
    provider: str
    name: str


class PrivateInterconnect(BaseModel):
    name: str
    kind: InterconnectKind
    provider: str
    region: str
    device: str
    interface: str
    vif: str
    vlan: int | None = None
    capacity_gbps: int = Field(default=10, gt=0)
    ipv4: str | None = None
    status: str = Field(default="up", pattern="^(up|down|degraded)$")


class TransitGateway(BaseModel):
    name: str
    provider: str


class Vpc(BaseModel):
    name: str
    provider: str
    region: str
    cidr: str
    transit_gateway: str | None = None


class RouteTableEntry(BaseModel):
    prefix: str
    target: str
    kind: str = Field(default="propagated", pattern="^(propagated|static)$")


class RouteTable(BaseModel):
    name: str
    vpc: str | None = None
    transit_gateway: str | None = None
    entries: list[RouteTableEntry] = Field(default_factory=list)