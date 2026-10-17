from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import SessionType


class BgpSession(BaseModel):
    name: str
    type: SessionType
    local_device: str
    local_asn: int
    peer_asn: int
    peer: str
    local_ip: str | None = None
    peer_ip: str | None = None
    multihop: bool = False
    allowas_in: bool = False
    rr_client: bool = False
    policy_in: str | None = None
    policy_out: str | None = None
    interconnect: str | None = None
    vxc: str | None = None
    admin_down: bool = False


class RouteReflectorCluster(BaseModel):
    id: str
    reflectors: list[str] = Field(default_factory=list)
    clients: list[str] = Field(default_factory=list)