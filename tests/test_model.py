from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from netops.graph import build_igp_graph
from netops.loader import dump_topology, load_network_dir
from netops.model import Topology

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "reference"


def _minimal() -> dict:
    return {
        "name": "test",
        "ases": {"65100": {"asn": 65100, "name": "x"}},
        "devices": {
            "r1": {
                "role": "dc_edge",
                "asn": 65100,
                "router_id": "10.0.0.1",
                "interfaces": {},
            }
        },
    }


def test_load_reference_network() -> None:
    topo = load_network_dir(FIXTURES)
    assert isinstance(topo, Topology)
    assert len(topo.devices) == 12
    assert len(topo.ases) == 4
    assert len(topo.links) == 18
    assert len(topo.sessions) == 18
    assert len(topo.interconnects) == 4
    assert len(topo.rr_clusters) == 2


def test_sessions_all_resolve() -> None:
    topo = load_network_dir(FIXTURES)
    for session in topo.sessions:
        assert session.local_device in topo.devices
        assert str(session.local_asn) in topo.ases
        assert str(session.peer_asn) in topo.ases
        if session.policy_in:
            assert session.policy_in in {p.name for p in topo.route_policies}


def test_dangling_device_ref_rejected() -> None:
    data = _minimal()
    data["sessions"] = [
        {
            "name": "s-bad",
            "type": "ebgp",
            "local_device": "ghost",
            "local_asn": 65100,
            "peer_asn": 65000,
            "peer": "nobody",
        }
    ]
    with pytest.raises(ValidationError, match="unknown device"):
        Topology.model_validate(data)


def test_dangling_policy_ref_rejected() -> None:
    data = _minimal()
    data["sessions"] = [
        {
            "name": "s-bad",
            "type": "ebgp",
            "local_device": "r1",
            "local_asn": 65100,
            "peer_asn": 65000,
            "peer": "nobody",
            "policy_in": "MISSING",
        }
    ]
    with pytest.raises(ValidationError, match="unknown route-policy"):
        Topology.model_validate(data)


def test_serialization_deterministic() -> None:
    topo = load_network_dir(FIXTURES)
    first = dump_topology(topo)
    second = dump_topology(topo)
    assert first == second
    reloaded = Topology.model_validate_json(topo.model_dump_json())
    assert reloaded.model_dump_json() == topo.model_dump_json()


def test_igp_graph_and_path() -> None:
    topo = load_network_dir(FIXTURES)
    graph = build_igp_graph(topo)
    assert graph.number_of_nodes() == 12
    path = __import__("networkx").shortest_path(graph, "dc1-agg-2", "dc2-core-2", weight="metric")
    assert path[0] == "dc1-agg-2"
    assert path[-1] == "dc2-core-2"
    assert "dc1-core-2" in path or "dc1-core-1" in path