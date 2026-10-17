# network-ops

Network-as-code for a hybrid BGP network: multiple on-prem datacenters, AWS / Azure /
GCP regions, and dedicated private connectivity — versioned in git, rendered as
ordered diagrams, and analyzed with protocol-accurate failure simulation.

This repo currently provides the **canonical data model** (the source of truth every
pillar consumes) plus the reference network and import fixtures. The ordered renderer
and the BGP decision engine are the next milestones (see `REQUIREMENTS.md` §6).

## Docs

| File | Purpose |
|------|---------|
| [`REQUIREMENTS.md`](REQUIREMENTS.md) | Requirements for the three pillars: Network-as-Code (NAC), ordered diagrams (DIA), BGP-accurate failure simulation (SIM) |
| [`SCOPE.md`](SCOPE.md) | Scope-down decision log (D1–D3): private-only, MVP exclusions, Megaport MVE/VXC |
| [`RESEARCH.md`](RESEARCH.md) | Reference BGP topologies & datasets, and the proposed model network |
| [`DATA-STRUCTURES.md`](DATA-STRUCTURES.md) | Open-source building blocks rated against requirements (Pydantic, NetworkX, Graphviz, …); recommended tiered stack |
| [`examples/`](examples) | Self-contained YAML that documents the full schema and the modeled real patterns |

## Current scope (SCOPE.md)

- **In**: dedicated private connectivity — Direct Connect / Cloud Interconnect /
  ExpressRoute between on-prem DCs and AWS/Azure/GCP, DC↔DC links, and **Megaport
  VXCs + MVE** (Palo Alto VM-Series virtual edge) with independently-failure-able legs.
- **Out (for now)**: public transit/IXP, VPN overlays, branches/meet-me rooms, DR
  sites, customer sites, providers beyond AWS/Azure/GCP, physical/optical layer.

## Install

Requires Python 3.12 (managed with [uv](https://docs.astral.sh/uv/)):

```sh
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
.venv/bin/python -m pytest
```

## Usage

Every network is a set of YAML fragments merged into one validated `Topology`.

```python
from netops.loader import load_network_dir, load_topology, dump_topology
from netops.graph import build_igp_graph, igp_path

# Split-by-module reference network (ases, dc1, dc2, wan, cloud, policy)
topo = load_network_dir("fixtures/reference")

# Or a single all-in-one example
topo = load_topology("examples/megaport-mve.yaml")

print(topo.devices)          # Device(name, role, asn, site, region, interfaces, ...)
print(topo.sessions)         # BgpSession(type, vxc=..., interconnect=..., policy_in=...)
print(topo.vxcs)             # VirtualCrossConnect(a_end, b_end) — two-ended failure units

# Derived NetworkX IGP graph (fate-shared links deduped, down links skipped)
graph = build_igp_graph(topo)
print(" -> ".join(igp_path(graph, "dc1-edge-1", "dc2-edge-3")))

# Deterministic, git-diffable serialization
yaml_text = dump_topology(topo)
```

## Canonical model (`src/netops/model`)

| Module | Types |
|--------|-------|
| `core.py` | `Topology`, `AutonomousSystem`, `Device`, `Interface`, `Link`, `Prefix` |
| `bgp.py` | `BgpSession` (ebgp/ibgp, RR-client, multihop, policy in/out, `interconnect`/`vxc`), `RouteReflectorCluster` |
| `policy.py` | `PrefixList`, `AsPathFilter`, `CommunityList`, `RoutePolicy` (match/set) |
| `igp.py` | `OspfArea`, `DeviceIgp` |
| `cloud.py` | `CloudProvider`, `PrivateInterconnect` (dx/cic/er/vpn), `VirtualCrossConnect` (a_end/b_end), `Vpc`, `TransitGateway`, `Subnet`, `RouteTable` |
| `meta.py` | `Provenance` (declared/imported/overridden — intent vs observed) |
| `enums.py` | roles, session types, interconnect kinds, policy actions |

Properties enforced by the model:

- **Typed validation** on every load/import (NAC-M-09): dangling device/policy/VXC/
  interconnect references are rejected with actionable errors.
- **Determinism** (NAC-M-06): identical input → byte-identical serialization; round-trip
  is stable, so git diffs are clean.
- **Provenance** (NAC-M-04): per-object `side`/`source`/`collected_at` for declared vs
  imported state.
- **Scalable** (X-03): Pydantic for the declared inventory; observed RIB mass moves to
  Arrow/Polars (SuzieQ-style) at exhaustive scale.

## Examples & fixtures

- `examples/network.yaml` — every field of the schema in one file (schema documentation)
- `examples/aws-hybrid.yaml` — Batfish `hybrid-cloud-aws` import-corpus drill (VPN pattern, out of product scope per D2)
- `examples/azure.yaml` — Batfish `cloud-azure` VNet/subnet/VM model
- `examples/megaport-mve.yaml` — Megaport MVE + three VXC legs (D3)
- `fixtures/reference/` — the reference private network (ases/dc1/dc2/wan/cloud/policy)
- `thirdparty/batfish/` — original AWS/Azure config dumps from the Batfish fixture set (Apache-2.0/MIT), kept for importer testing

## Status

- [x] Canonical data model (Pydantic v2) with reference integrity, provenance, determinism
- [x] YAML loader (multi-file merge), deterministic dump, NetworkX graph view
- [x] Reference private-network fixtures + AWS/Azure/Megaport examples, tested
- [ ] Ordered layered renderer (Graphviz `dot` → `rank` per layer, per `DIA-P-02`)
- [ ] BGP decision engine (RFC 4271 + RFC 7938 semantics) with Batfish parity checks (`SIM-F-*`)
- [ ] CLI/SDK surface (`X-01`)

## Layout

```
src/netops/          package: model/, loader.py, graph.py
fixtures/reference/  the reference network (D1 scope)
examples/            schema + real-pattern demonstrations
thirdparty/batfish/  unmodified upstream config dumps
tests/               model/loader/graph/determinism tests
REQUIREMENTS.md, SCOPE.md, RESEARCH.md, DATA-STRUCTURES.md
```