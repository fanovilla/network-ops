from __future__ import annotations

import ipaddress

from pydantic import BaseModel, Field, field_validator, model_validator

from .bgp import BgpSession, RouteReflectorCluster
from .cloud import (
    CloudProvider,
    CloudRegion,
    PrivateInterconnect,
    RouteTable,
    Subnet,
    TransitGateway,
    Vpc,
)
from .enums import DeviceRole, LinkType
from .igp import DeviceIgp
from .meta import Provenance
from .policy import AsPathFilter, CommunityList, PrefixList, RoutePolicy


def _require_ip(value: str, field: str) -> str:
    try:
        ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValueError(f"{field}: invalid IP address {value!r}") from exc
    return value


def _require_network(value: str, field: str) -> str:
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        raise ValueError(f"{field}: invalid prefix {value!r}") from exc
    return value


class Interface(BaseModel):
    name: str | None = None
    ip: str | None = None
    mtu: int | None = None
    bandwidth_gbps: float | None = None
    status: str = Field(default="up", pattern="^(up|down|degraded)$")
    role: str | None = None
    description: str | None = None

    @field_validator("ip")
    @classmethod
    def _check_ip(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ipaddress.ip_interface(value)
            except ValueError as exc:
                raise ValueError(f"interface.ip: invalid address {value!r}") from exc
        return value


class Device(BaseModel):
    name: str | None = None
    role: DeviceRole
    asn: int
    router_id: str
    platform: str | None = None
    interfaces: dict[str, Interface] = Field(default_factory=dict)
    igp: DeviceIgp | None = None
    labels: list[str] = Field(default_factory=list)
    provenance: Provenance = Field(default_factory=Provenance)

    @field_validator("router_id")
    @classmethod
    def _check_router_id(cls, value: str) -> str:
        return _require_ip(value, "device.router_id")

    @model_validator(mode="after")
    def _name_interfaces(self) -> "Device":
        for name, interface in self.interfaces.items():
            interface.name = name
        return self


class AutonomousSystem(BaseModel):
    asn: int | None = None
    name: str
    type: str = Field(default="private", pattern="^(private|cloud|provider)$")
    labels: list[str] = Field(default_factory=list)


class Link(BaseModel):
    name: str
    device_a: str
    interface_a: str
    device_b: str
    interface_b: str
    metric: int = Field(default=1, ge=1)
    bandwidth_gbps: float | None = None
    fate_share_group: str | None = None
    type: LinkType = LinkType.physical
    status: str = Field(default="up", pattern="^(up|down|degraded)$")


class Prefix(BaseModel):
    prefix: str
    origin_device: str | None = None
    anycast: bool = False
    advertise: bool = True
    local_pref: int | None = Field(default=None, ge=0)
    labels: list[str] = Field(default_factory=list)

    @field_validator("prefix")
    @classmethod
    def _check_prefix(cls, value: str) -> str:
        return _require_network(value, "prefix")


class Topology(BaseModel):
    name: str
    schema_version: str = "0.1.0"
    ases: dict[str, AutonomousSystem] = Field(default_factory=dict)
    devices: dict[str, Device] = Field(default_factory=dict)
    links: list[Link] = Field(default_factory=list)
    prefixes: list[Prefix] = Field(default_factory=list)
    sessions: list[BgpSession] = Field(default_factory=list)
    rr_clusters: list[RouteReflectorCluster] = Field(default_factory=list)
    interconnects: list[PrivateInterconnect] = Field(default_factory=list)
    providers: dict[str, CloudProvider] = Field(default_factory=dict)
    regions: list[CloudRegion] = Field(default_factory=list)
    vpcs: list[Vpc] = Field(default_factory=list)
    transit_gateways: list[TransitGateway] = Field(default_factory=list)
    subnets: list[Subnet] = Field(default_factory=list)
    route_tables: list[RouteTable] = Field(default_factory=list)
    prefix_lists: list[PrefixList] = Field(default_factory=list)
    as_path_filters: list[AsPathFilter] = Field(default_factory=list)
    community_lists: list[CommunityList] = Field(default_factory=list)
    route_policies: list[RoutePolicy] = Field(default_factory=list)
    annotations: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_references(self) -> "Topology":
        for name, device in self.devices.items():
            device.name = name
        for key, asn in self.ases.items():
            asn.asn = int(key)
        errors: list[str] = []

        def require_device(name: str, where: str) -> None:
            if name not in self.devices:
                errors.append(f"{where}: unknown device {name!r}")

        def require_asn(asn: int, where: str) -> None:
            if str(asn) not in self.ases:
                errors.append(f"{where}: unknown ASN {asn}")

        def require_policy(name: str, where: str) -> None:
            known = {p.name for p in self.route_policies}
            if name not in known:
                errors.append(f"{where}: unknown route-policy {name!r}")

        for link in self.links:
            require_device(link.device_a, f"link.{link.name}")
            require_device(link.device_b, f"link.{link.name}")
            if link.device_a in self.devices and link.interface_a not in self.devices[link.device_a].interfaces:
                errors.append(
                    f"link.{link.name}: interface {link.interface_a!r} not on {link.device_a!r}"
                )
            if link.device_b in self.devices and link.interface_b not in self.devices[link.device_b].interfaces:
                errors.append(
                    f"link.{link.name}: interface {link.interface_b!r} not on {link.device_b!r}"
                )

        for device in self.devices.values():
            require_asn(device.asn, f"device.{device.name}")

        for session in self.sessions:
            require_device(session.local_device, f"session.{session.name}")
            require_asn(session.local_asn, f"session.{session.name}")
            require_asn(session.peer_asn, f"session.{session.name}")
            if session.policy_in is not None:
                require_policy(session.policy_in, f"session.{session.name}.policy_in")
            if session.policy_out is not None:
                require_policy(session.policy_out, f"session.{session.name}.policy_out")
            if session.interconnect is not None:
                known = {i.name for i in self.interconnects}
                if session.interconnect not in known:
                    errors.append(
                        f"session.{session.name}: unknown interconnect {session.interconnect!r}"
                    )

        for interconnect in self.interconnects:
            require_device(interconnect.device, f"interconnect.{interconnect.name}")
            if (
                interconnect.device in self.devices
                and interconnect.interface not in self.devices[interconnect.device].interfaces
            ):
                errors.append(
                    f"interconnect.{interconnect.name}: interface {interconnect.interface!r} not on {interconnect.device!r}"
                )
            if interconnect.provider not in self.providers:
                errors.append(
                    f"interconnect.{interconnect.name}: unknown provider {interconnect.provider!r}"
                )

        for prefix in self.prefixes:
            if prefix.origin_device is not None:
                require_device(prefix.origin_device, f"prefix.{prefix.prefix}")

        vpcs = {vpc.name for vpc in self.vpcs}
        for subnet in self.subnets:
            if subnet.vpc not in vpcs:
                errors.append(f"subnet.{subnet.name}: unknown vpc {subnet.vpc!r}")

        for route_table in self.route_tables:
            if route_table.vpc is not None and route_table.vpc not in vpcs:
                errors.append(
                    f"route_table.{route_table.name}: unknown vpc {route_table.vpc!r}"
                )
            if route_table.transit_gateway is not None:
                known = {tg.name for tg in self.transit_gateways}
                if route_table.transit_gateway not in known:
                    errors.append(
                        f"route_table.{route_table.name}: unknown transit gateway {route_table.transit_gateway!r}"
                    )

        for cluster in self.rr_clusters:
            for reflector in cluster.reflectors + cluster.clients:
                require_device(reflector, f"rr_cluster.{cluster.id}")

        if errors:
            raise ValueError("\n".join(errors))
        return self