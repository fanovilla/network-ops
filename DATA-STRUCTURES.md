# Open-source building blocks: rating vs requirements

Candidate libraries/data structures that could back the network-as-code system
(`REQUIREMENTS.md`), rated against the three pillars plus cross-cutting requirements.
Every candidate is judged on the **scale line**: can it serve an MVP (multiple DCs, a few
cloud regions, private links only — `SCOPE.md` D1) and grow to "exhaustive"
(≥1,000 devices / 10k sessions / 1M prefixes, full BGP semantics, X-03)?

Scoring per pillar: `✔✔` excellent fit · `✔` good · `△` partial · `✘` misfit.
Ratings reference requirement IDs (NAC-*, DIA-*, SIM-*, X-*). "V" = fetch-verified
this session; others are from maintained knowledge — re-check before relying.

---

## A. Canonical structured model — the NAC graph/model storage

The data model must be typed, version-aware, diffable, deterministic (NAC-M-02/04/06),
and proviable (NAC-M-09). Tool-agnostic: the canonical model must *not* be locked to a
display or simulation library.

| Candidate | What it is / licence | NAC fit | DIA fit | SIM fit | Scale line | Notes |
|-----------|----------------------|---------|---------|---------|------------|-------|
| **Pydantic v2** [V-ish] | Typed Python records, schema→model, validation (MIT) | `✔✔` (NAC-M-02, NAC-M-09) | `△` (its `graphviz` export exists) | `✔` (records feed engine) | MVP: ideal. Exhaustive: fine for the *inventory* layer; do NOT put 1M prefixes in Pydantic | V2 is compiled (pydantic-core). Perfect for declaring the reference network in code (`model/` in §3 of RESEARCH) |
| **Apache Arrow / Polars** [V] | Columnar tables / dataframes (Apache-2.0 / MIT) | `✔` (observed RIB snapshots, SuzieQ-style) | `△` | `✔✔` (1M prefixes as columns; SIM-S-scale) | MVP: usable; Exhaustive: **the** answer for route-table mass | This is how SuzieQ stores networks (parquet). History/drift = partitioned tables (NAC-I-03) |
| **Protobuf / FlatBuffers / Cap'n Proto** | Cross-language wire schema | `✔` (canonical interchange, part of X-07) | `✘` | `✔` | MVP: unnecessary; Exhaustive: wire format for SDK/API | Overkill at MVP; add when the CLI/API (X-01) needs a versioned protocol |
| **JSON Schema** | Declarative validation doc | `✔` (schema enforcement) | `✘` | `△` | Both tiers OK | Cheap validation for YAML/JSON declarations; pairs with Pydantic |
| **Pyrsistent / immutable dicts** | Persistent data structures (MIT) | `✔` (snapshot of *intent* vs *observed*, NAC-M-03) | `✘` | `△` | MVP: nice; Exhaustive: memory-heavy | Cap at the topology (not RIB) layer |
| **DuckDB / SQLite** | Embedded relational (MIT) | `✔` (join inventory views) | `✘` | `✔` (graph of AS/prefix join queries) | MVP: SQLite; Exhaustive: DuckDB over Arrow | Cheap middle-index between "code declares" and "millions of rows observed" |

**Top pick:** Pydantic v2 for the declared canonical model + **Arrow/Polars** (parquet, SuzieQ-style) for all *observed*/large tables. This mirrors SuzieQ's proven split (declared config vs observed data).

---

## B. Graph representation & traversal (topology engine)

Holds devices/links/AS topology; IGP shortest paths; next-hop reachability; failure
branching. BGP decision series (SIM-F-01..07) runs on top of this graph — the graph
lib is only the substrate.

| Candidate | What / licence | NAC fit | DIA fit | SIM fit | Scale line | Notes |
|-----------|----------------|---------|---------|---------|------------|-------|
| **NetworkX** | Pure-Python graphs, algorithms galore (BSD-3) | `✔✔` | `△` | `✔` | MVP: perfect (express in code, k-shortest paths, all_shortest_paths, cut-edge analysis | Exhaustive: **slow**; 1M+ nodes/edges will hurt (X-03). Great for a fast, readable MVP and for test fixtures |
| **igraph** | C-core graph lib, bindings (GPL-2) | `✔` | `△` | `✔` | MVP: fine; Exhaustive: fast (multi-million edges) | The practical escalation path from NetworkX; watch GPL licensing |
| **graph-tool** | Boost-based (GPL-3) | `△` | `△` | `✔` | Exhaustive: fastest Python-wrapped | Heavier dependency; GPL-3; used by AS-topology researchers (right ecosystem for CAIDA graphs) |
| **Petgraph** | Rust graphs (MIT/Apache-2.0) | `✔` | `△` | `✔` | Exhaustive: if we go Rust or FFI | If core sim moves to Rust, this is the substrate |
| **Neo4j / Memgraph / Kuzu** | Graph DBs (GPLv3/commercial · BSL · MIT) | `✔` | `✘` | `△` | Exhaustive: rich path queries (Algo cost) | Kuzu (embedded, MIT) is the OSS-friendly pick; Memgraph is source-available not OSS; Neo4j community GPL. Only needed for the *search* form (SIM-S-08 / chokepoints at 1M prefix × 1000 device scale) |
| **OpenConfig YANG models** [V-ish] | Standardized model trees (Apache-2.0) | `✔` (schema alignment for importers, NAC-I-01) | `✘` | `△` | Both tiers | Not a data structure we query; a contract. Align our canonical model to these where possible |

**Top picks:** **NetworkX** at MVP (readable, expressive, enough for ~50–500 nodes);
**igraph** or Petgraph for exhaustive scale. Keep the graph lib **behind the API** (X-01)
so it can be swapped without touching the canonical model.

---

## C. Config import & normalisation (NAC-I)

| Candidate | What / licence | Fit | Scale line | Notes |
|-----------|----------------|-----|------------|-------|
| **Batfish** [V, 1.5k★] | Config parser→ modeled network → verifier (Apache-2.0); JUNOS, IOS-XE/XR, EOS, NX-OS, Nokia, FRR, **AWS, Azure**; reliability checks, change analysis | `✔✔` — this is the reference for NAC-I and for SIM engine semantics | MVP: run as a service to *parse* real configs; Exhaustive: use it for a second-opinion validation of our own engine | Its `networks/` fixtures (incl. `hybrid-cloud-aws`, `cloud-azure`) are our importer test corpus (RESEARCH §4). Its single-link/single-device failure checks directly mirror SIM-S-02 |
| **SuzieQ** [V, 906★] | Multi-vendor observability; poller → parquet tables; built-in **`path` command (path between two IPs)**, ECMP-at-every-hop, assert framework | `✔` — pattern for NAC-I-03 (diff/drift) and for X-04 (read-only collection) | MVP: adopt its table schemas + poller layering; Exhaustive: its Arrow/parquet store | Reuse its model-to-table normalisation ideas rather than reinventing vendored field names |
| **NAPALM / Nornir / Netmiko** | Multi-vendor config/state collection | `✔` — the *collectors* driving NAC-I-01 | Both | NAPALM gives structured `get_*`; Nornir scales to 1000s of devices (X-03) |
| **gNMI/OpenConfig stack** | Streaming telemetry pull of running/state config | `✔` — preferred live source when devices support it | Both | Best-effort when supported; fall back to batch/CLI else (NAC-I-01/02) |
| **BGPKIT (parser/broker/pybgpkit)** [V] | Rust MRT/BGP table parser + metadata broker (MIT) | `✔` — ingest real RouteViews/RIS tables for validation (RESEARCH §5) | MVP: skip; Exhaustive: yes | Fastest OSS way to replay real tables into our simulator and compare AS paths |

---

## D. Ordered diagram rendering (DIA) — *and only ranked/layered families qualify*

Requirement DIA-P-02/04/10 is **ordered, human-influenced, deterministic, stable**.
Force-directed/spring layouts (Cytoscape.js, d3-force, vis.js default) are excluded on
principle (they are "general graph theory renderers" the requirements explicitly reject).

| Candidate | What / licence | DIA fit | Explicit ordering control | MVP→Exhaustive | Notes |
|-----------|----------------|---------|---------------------------|----------------|-------|
| **Graphviz (dot/neato+rank)** | Layered DAG layout, `rank=same`, subgraphs, stable output (EPL-1.0) | `✔✔` (DIA-P-02 ranks, DIA-P-04 byte-stable, DIA-P-08 SVG) | Ranks, cluster subgraphs, `order` | MVP: **the** fast path (Python `graphviz`); Exhaustive: fine, static output | Deterministic layout matches our CI diagram-diff goal. Ranks map 1:1 to the layer stack in RESEARCH §3.2 |
| **Mermaid** | Text→diagram, flowchart direction + `:::class` styling (MIT) | `✔` — diffable as code, renders in Confluence/wiki (DIA-P-08) | Direction, subgraphs, rough rank-by-insertion | Both | Good second export target; less rigorous than dot for ordering stability |
| **PlantUML** | UML-ish textual diagrams (GPL/ASL) | `✔` — layered top-down, `together { }` | Top/Bottom, `together`, arrows | Both | Fine, slower project; Mermaid usually wins on ecosystem |
| **ELK / elkjs** [V, Eclipse EPL-1.0] | Industrial layout algorithms (layered, hierarchical nodes, ports) | `✔✔` — explicitly layered + nested groups; pushes the "human-order within auto-structure" boundary | Layer constraints, hierarchical containers | MVP: add for interactive; Exhaustive: strong | Computes positions only (we render). Web port exists (elkjs). Best complement to Graphviz for *interactive* HTML (DIA-I-01) |
| **dagre / dagrejs** [V, MIT, 5.8k★] | Directed layered layout for JS; `ranker` options | `✔` — layered, fast; honors graph ranks | Ranker + rank constraints | Interactive HTML; MVP+ | The natural companion to Graphviz in browser export; deterministic |
| **Cytoscape.js / d3-force / vis.js** | Force-directed interactive graphs | `✘` for DIA-P-02 (unordered spring layout) | — | — | Excluded by design; could serve the *interactive explorer* only after layout is fixed by an ordered engine |

**Top pick:** **Graphviz `dot`** as the deterministic source of truth for ranks/clusters
(MVP → Exhaustive, headless, CI-diffable); **ELK/Layered + dagre** inside the web
viewer for interactive drill-down once DIA-I lands.

---

## E. Protocol-accurate BGP simulation (SIM)

| Candidate | What / licence | Fit | Scale line | Notes |
|-----------|----------------|-----|------------|-------|
| **Batfish** [V] | Models BGP/OSPF/static, route-maps/prefix-lists/communities, `traceroute`-like path queries, failure analysis | `✔✔` (SIM-F-01..07 semantics proven) | MVP: maybe too heavy to run as core; Exhaustive: run as a **parity oracle** | We still build our own engine (determinism, provenance, CI) but validate it against Batfish on the same configs (SIM-S-10). Its answer format informs SIM-S-03/04 output |
| **Our own decision-simulator** | New (RFC 4271 + RFC 7938 semantics, SIM-F-01..10) | `✔✔` — this is *the* product | MVP-first, then optimize with igraph substrate / Arrow tables | Deterministic, offline, reviewable in CI (SIM-S-09) — the differentiator Batfish-style tools don't give as a library |
| **FRRouting (FRR)** | Real BGP stack (GPL-2/LGPL) | `△` — a *conformance oracle* via containerlab, too heavy/slow to be our engine | Exhaustive: only for conformance spot-checks | Best ground truth for tricky cases (allowas-in, communities) |
| **ExaBGP / GoBGP** | Live BGP speakers | `✘` for sim (needs live sessions) | — | Wrong tool; useful later for *live* probing |
| **BGPKIT (pybgpkit)** [V] | Real RouteViews/RIS table replay | `✔` — validate predicted vs observed AS paths on public prefixes (RESEARCH §5) | Exhaustive | Only meaningful once public data returns to scope (D1 deferred); still testable now against cloud/private data when available |

---

## F. Diffing, reconciliation, snapshots (NAC-I-03) & determinism

- **DeepDiff / charmonium.diff** — field-level diff of model objects; MVP-grade for NAC-I-03.
- **`git` + sorted serialization (NAC-M-06)** — the real versioning; clean diffs come from
  canonical ordering, which we control in serialization, not from the lib.
- **Polars/Arrow tables with `as-of` history** (SuzieQ pattern) — drift-over-time across
  1M prefixes; the *exhaustive* version of NAC-I-03/I-07.

---

## G. Summary rating matrix

Legend: ✔✔ excellent, ✔ good, △ partial, ✘ misfit, — not applicable.

| Candidate | NAC | DIA | SIM | MVP→Exhaustive | Licence risk |
|-----------|-----|-----|-----|----------------|--------------|
| Pydantic v2 | ✔✔ | — | ✔ | MVP now, inventory later | none (MIT) |
| Arrow/Polars | ✔ | — | ✔✔ | MVP fine, **the** scale path | none (Apache/MIT) |
| NetworkX | ✔✔ | — | ✔ | MVP | none (BSD) |
| igraph | ✔ | — | ✔ | escalation path | GPL-2 ⚠ |
| Graphviz dot | — | ✔✔ | — | all tiers | EPL (fine) |
| ELK / elkjs | — | ✔✔ | — | interactive tier | EPL-1.0 |
| dagre | — | ✔ | — | interactive tier | none (MIT) |
| Mermaid | — | ✔ | — | doc tier | none (MIT) |
| Batfish (+pybatfish) | ✔✔ | — | ✔✔ | import parser + parity oracle | none (Apache-2.0) |
| SuzieQ | ✔ | — | △ | observability pattern | none (Apache-2.0) |
| BGPKIT | ✔ | — | ✔ | validation tier | none (MIT) |
| Kuzu (graph DB) | ✔ | — | △ | only at exhaustive search scale | none (MIT) |
| DuckDB/SQLite | ✔ | — | ✔ | join layer both tiers | none (MIT) |
| NAPALM/Nornir | ✔ | — | — | collectors | Apache-2.0 / BSD |
| Protobuf/FlatBuffers | ✔ | — | — | API tier later | none |

---

## H. Recommended stack (decision)

**Canonical model (NAC):** Pydantic v2 records, serialized sorted/YAML, in git.
Observed/large state: **Polars/Arrow parquet** (SuzieQ-style tables, `namespace`=scenario,
timestamped). Import via **NAPALM/Nornir** collection → **Batfish** parse as a parity
check → normalized into the tables. Diff/reconcile = Pydantic object diff (MVP) over
Arrow history (exhaustive).

**Renderer (DIA):** **Graphviz `dot`** for deterministic, rank/group-controlled output
headlessly (CI). **Mermaid** secondary text export. Interactive (later): **ELK/elkjs**
(or dagre) in the browser for DIA-I drill-down, using the *same* rank/group hints.

**Simulator (SIM):** our own decision engine on **NetworkX** (MVP) → **igraph** substrate
at scale; RIB mass in **Arrow/Polars**; validate vs **Batfish** on identical configs as a
CI parity suite (SIM-S-10), and vs real tables via **BGPKIT** when public data returns.

**One hard rule:** every lib above is an *adapter* behind the SDK boundary (X-01). The
canonical model, the rank/group hints, and the scenario grammar live in *our* code and
must be independently machine-read by each tier (NAC-M-06).

---

### Source verification
Fetch-verified this session: batfish/batfish (Apache-2.0, vendor+cloud list, failure
checks, `networks/` fixtures), BGPKIT org (parser/broker/pybgpkit MIT), netenglabs/suzieq
(Apache-2.0, poller→parquet, `path` command, asserts), eclipse-elk (EPL-1.0, layered +
hierarchical nodes), dagrejs/dagre (MIT, layered JS layout). Remaining candidates are
standard, well-known libraries — URLs revisit before pinning versions.