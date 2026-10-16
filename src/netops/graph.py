from __future__ import annotations

import networkx as nx

from netops.model.core import Link, Topology


def build_igp_graph(topology: Topology) -> nx.Graph:
    graph = nx.Graph()
    for name, device in topology.devices.items():
        graph.add_node(
            name,
            role=device.role.value,
            asn=device.asn,
            router_id=device.router_id,
        )
    active: dict[tuple[str, str], Link] = {}
    for link in topology.links:
        if link.status == "down":
            continue
        key: tuple[str, str] = (link.device_a, link.device_b) if link.device_a < link.device_b else (link.device_b, link.device_a)
        if key in active:
            if link.fate_share_group and link.fate_share_group == active[key].fate_share_group:
                continue
        active[key] = link
    for link in active.values():
        graph.add_edge(
            link.device_a,
            link.device_b,
            name=link.name,
            metric=link.metric,
            bandwidth_gbps=link.bandwidth_gbps,
            fate_share_group=link.fate_share_group,
        )
    return graph


def igp_path(graph: nx.Graph, source: str, target: str) -> list[str]:
    return nx.shortest_path(graph, source, target, weight="metric")