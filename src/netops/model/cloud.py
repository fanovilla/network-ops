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


class VxcEnd(BaseModel):
    service: str
    location: str
    device: str | None = None
    interface: str | None = None
    vlan: int | None = None
    vif: str | None = None
    capacity_gbps: int | None = Field(default=None, gt=0)


class VirtualCrossConnect(BaseModel):
    name: str
    provider: str = Field(default="megaport", pattern="^[a-z0-9_-]+$")
    a_end: VxcEnd
    b_end: VxcEnd
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


class Subnet(BaseModel):
    name: str
    vpc: str
    cidr: str
    availability_zone: str | None = None
    hosts: list[str] = Field(default_factory=list)


class RouteTableEntry(BaseModel):
    prefix: str
    target: str
    kind: str = Field(default="propagated", pattern="^(propagated|static)$")


class RouteTable(BaseModel):
    name: str
    vpc: str | None = None
    transit_gateway: str | None = None
    subnets: list[str] = Field(default_factory=list)
    propagating_vgws: list[str] = Field(default_factory=list)
    entries: list[RouteTableEntry] = Field(default_factory=list)