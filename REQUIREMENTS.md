# Network Operations — Requirements

Project: a network-as-code system for a hybrid BGP network consisting of two on-prem
datacenters, multiple cloud providers across multiple regions, and multiple telco
partners. Links carry multiple levels of redundancy.

Three pillars:

1. **Network-as-Code (NAC)** — the whole network definition is encoded in code and
   versioned; live configuration can be imported and reconciled into the same model.
2. **Ordered Diagramming (DIA)** — render the whole or any part of the network as an
   *ordered, presentation-controlled* diagram, not a generic graph renderer.
3. **Failure Simulation (SIM)** — simulate a node/link failure and answer "what is the
   next path from node A to node B" with protocol-accurate BGP semantics.

Priorities use MoSCoW: **M**ust, **S**hould, **C**ould, **W**on't.

---

## 1. Network-as-Code

### 1.1 Modelling — canonical data model (NAC-M)

| ID       | Req                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Priority |
|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| NAC-M-01 | The full network definition SHALL be representable as versioned, declarative code (YAML/JSON/HCL or a typed DSL) held in git.                                                                                                                                                                                                                                                                                                                                                         | M        |
| NAC-M-02 | The canonical data model SHALL be vendor-neutral and typed, covering at minimum: autonomous systems (AS), AS relationships, devices (role: core/edge/route-reflector/cloud-gateway/CGNAT), interfaces, loopbacks, point-to-point links, IGP (OSPF/IS-IS areas/levels, metrics), BGP sessions (eBGP + iBGP, full-mesh/RR/client), route-reflector clusters, prefixes and aggregates, and BGP policy (route-maps, prefix-lists, as-path filters, communities, local-pref, MED, weight). | M        |
| NAC-M-03 | The model SHALL separate *intent* (what we declared) from *observed* (what devices actually run) so reconciliation is diffable.                                                                                                                                                                                                                                                                                                                                                       | M        |
| NAC-M-04 | Every field SHALL carry provenance: source (code / live import / manual override), source device, and timestamp.                                                                                                                                                                                                                                                                                                                                                                      | M        |
| NAC-M-05 | The model SHALL be composable so an operator can define the network as modules (per-DC, per-cloud-provider, per-telco-partner) that assemble into one coherent graph.                                                                                                                                                                                                                                                                                                                 | M        |
| NAC-M-06 | Normalization SHALL be deterministic: serialization is sorted and stable so two runs of the same input produce byte-identical output and clean diffs.                                                                                                                                                                                                                                                                                                                                 | S        |
| NAC-M-07 | The model SHALL support tags/attributes for operational grouping (region, DC, provider, role, maintenance window, criticality).                                                                                                                                                                                                                                                                                                                                                       | M        |
| NAC-M-08 | The model SHALL support abstracted representions for cloud connectivity where fine device detail is not applicable (e.g. VPC route tables, transit gateway, cloud provider backbone summarized as an AS/connector).                                                                                                                                                                                                                                                                   | S        |
| NAC-M-09 | Refactoring SHALL be safe: rename/reparent operations must produce zero effective diff in rendered output unless intended.                                                                                                                                                                                                                                                                                                                                                            | S        |

### 1.2 Live configuration import & reconciliation (NAC-I)

| ID       | Req                                                                                                                                                                                                                                                                                                   | Priority |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| NAC-I-01 | Importers SHALL ingest structured data from multiple platforms into the canonical model: JUNOS, Cisco IOS-XR, Arista EOS, Nokia SR OS, and any platform that can emit NCJSON/OpenConfig/gNMI/NETCONF, batching output, or CLI-parseable structured formats.                                           | M        |
| NAC-I-02 | Cloud importers SHALL ingest VPC route tables, subnet associations, IGW/TGW/WAN gateway state, and transit-provider state for AWS, GCP, and Azure (and backend-agnostic abstraction for others).                                                                                                      | M        |
| NAC-I-03 | An import SHALL produce a diff model (add/remove/change at field granularity) between observed state and the declared model, and SHALL classify each diff as *drift* (observed differs from intent), *unknown* (observed exists in live but not in code), or *unapplied* (declared but not observed). | M        |
| NAC-I-04 | Acceptance/merge SHALL be explicit: the operator decides per-diff, import-as-intent, or reject-and-keep-declared. Automatic propagation into the declared model SHALL be opt-in.                                                                                                                      | M        |
| NAC-I-05 | Imports SHALL be idempotent and support partial/selective import (device, region, provider, AS) with transactional semantics (all-or-nothing per target).                                                                                                                                             | S        |
| NAC-I-06 | The system SHALL detect and surface ambiguities needing human resolution (e.g. two devices claiming the same loopback, conflicting AS at a link end) rather than silently choosing.                                                                                                                   | M        |
| NAC-I-07 | Imported state SHALL be cached with the original raw data retained for audit, and SHALL carry the collection timestamp for staleness reports.                                                                                                                                                         | S        |
| NAC-I-08 | Unreachable/unknown devices on import SHALL be recorded as degraded collection, not as deleted state.                                                                                                                                                                                                 | M        |
| NAC-I-09 | Schema validation SHALL run on every write (declared or imported): type/schema checks plus semantic checks (unique ASN and router-id, valid IPv4/IPv6/netmasks, no dangling object references, prefix containment rules).                                                                             | M        |

---

## 2. Ordered Diagramming

### 2.1 Presentation control (DIA-P)

| ID       | Req                                                                                                                                                                                                                                                                                              | Priority |
|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| DIA-P-01 | Diagrams SHALL be renderable for the whole network or any filtered subset (region, DC, AS, provider, role, tag, session state, prefix association).                                                                                                                                              | M        |
| DIA-P-02 | Layout SHALL be *ordered and human-influenced*, not a black-box graph layout engine. The author can specify: ranks/layers (e.g. DC-core → DC-edge → WAN → telco), per-node grouping containers (DC rooms, provider bubbles, rings per region), and the ordering of nodes within each rank/group. | M        |
| DIA-P-03 | Position overriding SHALL be possible as hard-coded coordinates or as rank/order hints; unspecified elements get placed automatically *within* the declared structure, never against it.                                                                                                         | M        |
| DIA-P-04 | Rendering SHALL be deterministic: identical model input yields byte-identical diagram output across runs and machines.                                                                                                                                                                           | M        |
| DIA-P-05 | Visual encoding SHALL be controllable per class: node shape/color, link style/color/thickness, labels — keyed on status (up/down/degraded), provider, role, region, bandwidth, IGP metric, BGP state.                                                                                            | S        |
| DIA-P-06 | The author SHALL be able to add annotations: free-text, per-object notes, link labels (peer IP, ASN, bandwidth, tunnel/id), legend, and title/footnote.                                                                                                                                          | S        |
| DIA-P-07 | Layers/overlays SHALL be toggleable: physical links, IGP topology, BGP overlay/sessions, and cloud abstraction layer.                                                                                                                                                                            | S        |
| DIA-P-08 | Multiple export targets SHALL be supported: SVG, HTML (interactive) and a text source-of-truth format (e.g. Mermaid/DOT) so diagrams live alongside code and diff cleanly in review.                                                                                                             | S        |
| DIA-P-09 | The renderer SHALL be usable headlessly in CI so generated diagrams are reviewed with the model changes that caused them.                                                                                                                                                                        | S        |
| DIA-P-10 | Layout SHALL be *stable under change*: a small model diff (one link) must not resort/relocate unrelated nodes unless explicit.                                                                                                                                                                   | M        |

### 2.2 Drill-down & interaction (DIA-I)

| ID       | Req                                                                                                                                                                                                               | Priority |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| DIA-I-01 | Interactive output SHALL support drill-down: click a node/AS to show its detail (interfaces, sessions, policies), and click a link to show addresses, ASes, bandwidth and metric.                                 | S        |
| DIA-I-02 | The system SHALL support *path highlighting*: given a source and destination, highlight the current (or simulated) path in the diagram.                                                                           | S        |
| DIA-I-03 | If live state is available, the diagram SHALL overlay operational status (session up/down, routing-table reachability, utilization shading) on demand; without connectivity it still renders from declared state. | C        |

---

## 3. Failure Simulation

### 3.1 Fidelity (SIM-F) — protocol-accurate

| ID       | Req                                                                                                                                                                                                                                                                                                                                                     | Priority |
|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| SIM-F-01 | The simulation engine SHALL model the full BGP decision process, not a shortest-path heuristic. Best-path selection SHALL follow the standard series: weight → local-pref → AS-origin → AS-path length → origin type → MED → eBGP-over-iBGP → IGP metric to next-hop → router-id (with whatever vendor-specific order overrides the operator declares). | M        |
| SIM-F-02 | The engine SHALL apply BGP policy (route-maps in/out, prefix-lists, as-path filters, community manipulation incl. NO-EXPORT, local-pref and MED set/change) before evaluating which routes are learned/exported.                                                                                                                                        | M        |
| SIM-F-03 | The engine SHALL honor eBGP export rules (single best eBGP route to eBGP peers; iBGP- and RR-learned routes not re-advertised to iBGP; no-export/community policies).                                                                                                                                                                                   | M        |
| SIM-F-04 | The engine SHALL model ECMP/multipath where configured (AS-path length equal, next-hop reachable, same attributes) and return a set of next-hops with load-sharing weight.                                                                                                                                                                              | M        |
| SIM-F-05 | Next-hop reachability SHALL be resolved against the IGP/static model: an iBGP route is only usable when its next-hop is reachable (IGP metric comparison included per SIM-F-01).                                                                                                                                                                        | M        |
| SIM-F-06 | The engine SHALL model route-reflector clusters / iBGP full-mesh: an RR-client relationship determines route propagation and cluster-list loop prevention.                                                                                                                                                                                              | M        |
| SIM-F-07 | Policy and attributes SHALL be declared in the same model as the topology (NAC-M-02) and consumed by both the renderer and the simulator — no duplicated data.                                                                                                                                                                                          | M        |
| SIM-F-08 | AS-path modeling SHALL include prepends and aspath overrides/atomic aggregates as configured, so the resulting path is what BGP actually computes.                                                                                                                                                                                                      | S        |
| SIM-F-09 | Acceptable inaccuracies: the simulator assumes routers converge (no convergence-order artifacts); route flaps between equally-good paths MAY be simplified to a single stable outcome. Convergence-order simulation is C.                                                                                                                               | S        |
| SIM-F-10 | Where the environment is not fully modeled (cloud backbone, telco internal core beyond its AS), those segments SHALL be declared as summarized AS connectors with tunable cost/policy so path preference through them can be influenced, matching the declaration.                                                                                      | S        |

### 3.2 Scenarios & queries (SIM-S)

| ID       | Req                                                                                                                                                                                                                                                                                                                     | Priority |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| SIM-S-01 | Operate against a live or imported snapshot; import must be from the same canonical model used everywhere.                                                                                                                                                                                                              | M        |
| SIM-S-02 | Failure scenarios SHALL be expressible as: device down (whole node incl. all interfaces), interface/link down, single BGP session down, IGP metric change, policy change, AS-path prepend, prefix withdrawal, or cloud region/provider loss. Multiple failures in one scenario SHALL be supported.                      | M        |
| SIM-S-03 | A path query SHALL answer "for prefix/prefix-set, what is the end-to-end path from device A (or AS a) to device B (or AS b)", either under current state or under one or more failure scenarios.                                                                                                                        | M        |
| SIM-S-04 | For each device along a path the engine SHALL report: selected next-hop(s), the exit interface, the decision reason (e.g. "longer local-pref", "shorter AS-path", "lower IGP metric"), and the losing runners-up (so the operator sees *why* the next path was chosen).                                                 | M        |
| SIM-S-05 | The result SHALL show the AS path traversal and device hop sequence so the operator sees which segments cross which providers/telcos.                                                                                                                                                                                   | M        |
| SIM-S-06 | Output SHALL be comparable between baseline and scenario, highlighting only changed hops.                                                                                                                                                                                                                               | S        |
| SIM-S-07 | For each path the engine SHALL flag pathologies: blackhole (route lost, no alternative), forwarding loop, suboptimal preference (e.g. choosing a longer AS-path due to policy), path length exceeding operator threshold, unreachable next-hop, or premature route loss due to communities like NO-EXPORT/NO-ADVERTISE. | M        |
| SIM-S-08 | The system SHALL also answer the *search* form: for a given prefix and source, find which single failures (or failure combos) would cause a blackhole or a path worse than a threshold (k-resiliency analysis).                                                                                                         | S        |
| SIM-S-09 | The engine SHALL be deterministic: same snapshot + same scenario → same result, so simulations are reviewable in CI alongside model changes (regression testing of path outcomes).                                                                                                                                      | M        |
| SIM-S-10 | A scenario SHALL be codifiable as data (code) so the whole test suite (scenarios + expected paths/blackholes) is part of the repo and CI-approved.                                                                                                                                                                      | M        |
| SIM-S-11 | The engine SHALL expose the chokepoint view: for each AS or edge link, how many prefixes rely on it as the sole viable path (impact analysis).                                                                                                                                                                          | C        |

---

## 4. Cross-cutting requirements

| ID   | Req                                                                                                                                                                                                                                      | Priority |
|------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| X-01 | The system SHALL expose a CLI and a programmatic API/SDK (read + mutate), with the same guarantees (validation, diffs, transactions) on both.                                                                                            | M        |
| X-02 | All operations SHALL be versioned/audited in git; history SHALL answer "when and why did this session/prefix change".                                                                                                                    | M        |
| X-03 | The system SHALL support SLA-style scale orders of magnitude beyond current size (design target ≥ 1,000 devices / 10,000 sessions / 1M prefixes) with incremental recompute, so rebuilding the shortest-path and BGP tables is feasible. | S        |
| X-04 | Where the system touches live devices to collect configuration, it SHALL be read-only by default and require explicit credentials/target scope; no default write access.                                                                 | M        |
| X-05 | The system SHALL degrade gracefully on partial data: missing device configs, unknown prefixes, unknown telco internals are reported as *uncertainty* with an impact statement, never silently ignored.                                   | S        |
| X-06 | Rendering and simulation MUST NOT require live connectivity; both work fully offline from the declared model/snapshot.                                                                                                                   | M        |
| X-07 | Extensibility SHALL be pluggable: new vendor importers, new cloud importers, new export formats, and new layout strategies are add-ins rather than forks.                                                                                | S        |
| X-08 | The project SHALL document the data model, the BGP decision pipeline, failure-scenario grammar, and layout-hint grammar in-repo, tested against fixtures from the real network.                                                          | S        |

---

## 5. Non-goals

- Do **not** build a generic graph-drawing engine; layout is ordered and presentation-driven (DIA-P-02).
- Do **not** simulate convergence-time/tiebreak-real-time dynamics or packet loss/arming within a failure window (see
  SIM-F-09).
- Do **not** push configuration changes to devices from this tool; it is declaration, visualization, and analysis only.
- Do **not** model devices below the routing layer in fidelity (no full interface-level MAC/port inventory unless it
  feeds the above).
- Do **not** attempt to model the full internals of telco/cloud backbones; they are summarized connectors with tunable
  behavior.

---

## 6. Definition of Done / acceptance criteria

A requirement is done when: a fixture from the real network (device snapshots, one
failure scenario, one diagram render) passes, and the outcome is deterministic and
reviewable in CI. The first milestone is: import two real router configs from two
different vendors → produce a reconciled model → render a filtered regional diagram →
run one single-link failure and answer "what path does prefix P take from A to B"
with BGP-accurate reasoning.