from __future__ import annotations

import enum


class DeviceRole(str, enum.Enum):
    dc_core = "dc_core"
    dc_edge = "dc_edge"
    dc_aggregation = "dc_aggregation"
    cloud_gateway = "cloud_gateway"
    virtual_edge = "virtual_edge"


class Side(str, enum.Enum):
    declared = "declared"
    imported = "imported"
    overridden = "overridden"


class SessionType(str, enum.Enum):
    ebgp = "ebgp"
    ibgp = "ibgp"


class InterconnectKind(str, enum.Enum):
    direct_connect = "direct_connect"
    cloud_interconnect = "cloud_interconnect"
    expressroute = "expressroute"
    vpn = "vpn"


class PolicyAction(str, enum.Enum):
    permit = "permit"
    deny = "deny"


class SetStatement(str, enum.Enum):
    local_pref = "local_pref"
    med = "med"
    community = "community"
    as_path_prepend = "as_path_prepend"
    weight = "weight"


class LinkType(str, enum.Enum):
    physical = "physical"
    lag = "lag"
    interconnect = "interconnect"