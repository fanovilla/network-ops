# Research: A Sufficiently Complex BGP Topology for Modeling

Context: we are building a network-as-code system (NAC model + ordered renderer +
protocol-accurate BGP failure simulation, per `REQUIREMENTS.md`) for a hybrid network —
2 on-prem DCs, multiple cloud providers/regions, multiple telco partners, multi-level
redundancy. This doc answers: **which public descriptions/datasets of complex BGP
topologies can we model on, and what is the reference network we will actually seed?**

Terminology: "BGP network" is informal. The correct units are **Autonomous Systems
(ASes)** — interdomain routing (eBGP) between ASes, and iBGP inside one AS. We model a
**multi-AS topology**: our AS, the cloud backbone ASes, and telco/transit ASes.

Reference network topology: **as opposed to an AS-level graph, we also need
router-level and policy-level description.** A believable reference must exercise:
iBGP full-mesh/RR clusters, IGP next-hop resolution, eBGP at edges, route policies
(local-pref/MED/communities), ECMP, and redundancy such that single-failure questions
are interesting.

---

## 1. Candidate sources (verified)

| # | Source | What it gives us | Fit |
|---|--------|------------------|-----|
| 1 | **RFC 7938** — "Use of BGP for Routing in Large-Scale Data Centers", Lapukhov/Premji/Mitchell, 2016 — https://datatracker.ietf.org/doc/html/rfc7938 | A *complete written design* of an EBGP-only Clos fabric: private-ASN allocation scheme (64512–65534, per-tier), single-hop eBGP, `allowas-in`, no route summarization of server subnets (blackhole hazard), ECMP/weighted-ECMP, convergence/failure-scope analysis | **M**: gives us a documented, buildable-at-any-size DCN fabric with the exact policy edge cases our simulator must reproduce |
| 2 | **CAIDA AS Relationships (serial-1/serial-2)** — https://www.caida.org/catalog/datasets/as-relationships/ | Monthly **AS-level graphs of the real Internet edge by AS** with business relation type (**c2p / p2p / s2s**), valley-free paths, **customer cones**, ASRank | **M**: the telco/transit layer. We can select the subgraph around our ASN and get a realistic, policy-governed provider graph to test BGP path preference and valley-free correctness |
| 3 | **Batfish example networks** — https://github.com/batfish/batfish/tree/master/networks (`example`, `hybrid-cloud-aws`, `cloud-azure/…`) | Downloadable **real-looking multi-vendor device configs** (incl. AWS/cloud constructs) that Batfish already parses; a proven reference implementation of config→model→verification we should study and align with | **M**: our NAC importer milestone (NAC-I-01) needs fixture configs; these give us JUNOS/EOS/IOS-XR-style material + cloud semantics without NDAs |
| 4 | **NSDI '18: NetComplete** (El-Hassany et al., ETH) — https://www.usenix.org/conference/nsdi18/presentation/el-hassany | Demonstrates a **declarative network model spanning BGP/OSPF/static + route-maps/ACLs** and configuration synthesis from properties | **S**: prior art for our NAC model shape and for "config as data" semantics |
| 5 | **NSDI '18: Net2Text** (Birkner et al., ETH) — https://www.usenix.org/conference/nsdi18/presentation/birkner | Summarizing **forwarding behavior across hundreds of routers** from routing tables — a model of the "what does the network actually do" query layer | **C**: informs path-query output design (SIM-S-03/04) |
| 6 | **SIGCOMM '21: AnyOpt** — https://conferences.sigcomm.org/sigcomm/2021/ | Anycast performance + **multi-site, multi-transit peering**: 15 sites × 6 transit providers, RTT-modeled catchment prediction | **C**: matches our anycast VIPs + cloud/telco edge; only if we want performance-oriented claims |
| 7 | **Internet Topology Zoo** (Knight et al., IEEE JSAC 2011) — http://www.topology-zoo.org/ | 250+ **real ISP router-level topologies in GraphML** (points-of-presence, backbone, redundancy) | **S**: stress-test the ordered renderer and SIM scale with real shapes; note: it is dated and has no policy/AS data attached |
| 8 | **Meta WAN papers** — "Optimizing Billions of BGP Decision-makings" (Optimal Route Reflection, 2018/2019, engblog) and "Express Backbone" (SIGCOMM '21) | Descriptions of iBGP **full-mesh + RR + IGP-metric-optimal decision** at scale (ORR) — precisely the semantics in SIM-F-01 (eBGP-over-iBGP → IGP metric tiebreak); EB: segment-based WAN planning | **S**: design guidance and experiential expectations, not data |

### 1.1 Confirmed facts captured from the sources

- RFC 7938 (§5.2): a single ASN for the whole Tier-1 (spine), an ASN per cluster of
  Tier-2, an ASN per Tier-3 device; repeated private ASNs across clusters require
  `allowas-in` and rely on AS-path length tiebreakers; server subnets are never
  summarized inside the fabric because a single-link failure blackholes them
  (§5.2.3, §8.2). ECMP fan-out, fate-sharing/LAG and convergence analysis in §6–7.
- CAIDA: relationship model is **c2p / p2p / s2s**; **valid (valley-free) paths** =
  zero+ c2p, then 0–1 p2p, then zero+ p2c; serial-2 adds peering links inferred from
  IX looking-glasses + traceroute (Oct 2015→present, monthly). AUA requires citation.
- Batfish: `networks/` contains `example`, `hybrid-cloud-aws`, `cloud-azure/azure_configs`,
  and an `iptables-firewall` case — directly useful fixture configs.

---

## 2. Gaps — what no single source covers

| Need | Available sources? | Gap |
|------|--------------------|-----|
| Our exact footprint (2 DCs + multi-cloud + telco) | No single public equivalent | **We declare it** (Section 3) |
| Real vendor configs incl. iBGP/RR/policy to *import* | Batfish fixtures (partial; not RR-heavy) | FRRouting/EVE-NG/containerlab generated configs as complement |
| Policy + AS relation truth combined | CAIDA (AS-only) × configs (policy-only) | We join by ASN; treat telco internals as summarized connectors (SIM-F-10) |
| Validation of path predictions | RouteViews http://www.routeviews.org / RIPE RIS (real BGP tables) | We can *validate* our simulator's AS-path output for public prefixes against observed tables |
| Real names/GEO placement | Topology Zoo (dated), PeeringDB https://www.peeringdb.com | PeeringDB gives current IX/peering facts to ground the declared topology |

---

## 3. Recommended reference network ("the model network")

A **synthetic but realistic** multi-AS topology that we fully declare in our data model.
It matches the operator's environment 1:1 in shape, is redactable/exportable, and every
element can be traced to a real-world counterpart.

### 3.1 Scope & size (design targets, X-03)

- Active topology nodes: ~50 routers (2 DCs × core/edge + cloud gateways + of those).
- ASes: our enterprise AS **AS 65100** (private), 3 transit ISPs (AS 1, AS 3356, AS 1299 — real),
  1 regional ISP (AS 174-ish scaled down), 2 IXP peering points (real ASNs for IXP route-servers),
  3 cloud backbone ASes (AWS 16509, GCP 15169, Azure 8075) declared as *summarized connectors*.
- iBGP: full-mesh + 4 route-reflector clusters (2 per DC) + clients; IGP OSPF (single) area 0
  per DC + inter-DC, used for next-hop resolution and the IGP-metric tiebreak.
- Prefixes: 4 DC service aggregates (/20–/22) with anycast VIP subnets + 6 cloud
  import/export prefixes; total addressable ~50 announced prefixes.

### 3.2 Topology (by layer, matching DIA-P-02 ranks)

```
  Layer 1  telco:  AS 3356 + AS 1299 + AS 64600(regional) — transit; 2 IXPs (peering)
  Layer 2  WAN:    inter-DC dark fiber/SRTE bundles, 2×100G each, LAGged
  Layer 3  DC edge: dc1-edge-1..2, dc2-edge-1..2 — eBGP to every telco+IXP, eBGP to clouds
  Layer 4  DC core: dc1-core-1..2, dc2-core-1..2 — iBGP RRs, OSPF backbone
  Layer 5  DC aggr: dcX-agg-1..8 (spine) — iBGP clients, ECMP to edge/core
  Layer 6  cloud:   aws-use1/uw2/euwest, gcp-usc1/euw1, azr-eastus/weu — TGW/VPC route tables
```

Redundancy contract (the interesting part for SIM): every telco peered at ≥2 edge
routers ≥2 DCs; every cloud via ≥2 edge routers and ≥2 regions; inter-DC ≥2 disjoint
links; ECMP on agg→spine so a single link/session/node failure always has ≥1 clean
alternative, but *some* double-failures are fatal by design (to make k-resiliency
analysis meaningful).

### 3.3 Policy semantics baked into the model (consumed by SIM)

- local-pref: cloud-eBGP import **120**, IXP-peer **110**, transit **100**;
  iBGP-learned **100**+IGP metric tiebreak; exit MED from cloud (sim vs).
- AS-path prepend on one transit path for outbound TE; communities for
  no-export/no-advertise tagging; allowas-in + repeated private ASN scheme per RFC 7938
  inside the DC fabric; server subnets NOT summarized (blackhole hazard the SIM must find).
- These values are exactly the knobs SIM-F-01..07 uses; the fixtures document expected
  outcomes (baseline + after each single failure).

---

## 4. How each pillar consumes this

- **NAC**: declare §3 as modules (per-DC, per-cloud, per-telco) → concat into one model;
  import Batfish `hybrid-cloud-aws`/`cloud-azure` configs and CAIDA subgraph as the
  *observed* side to exercise NAC-I-03 diff classification.
- **DIA**: rank/group layout mirrors §3.2; telco layer at top, cloud at bottom; anycast
  VIPs flagged; status overlay works because we model sessions.
- **SIM**: baseline tables computed from §3.3 policy; failure library =
  link/node/session/region + a suite of "expected path change" assertions to lock
  behavior in CI (SIM-S-09/10; milestone §6 in REQUIREMENTS.md).

---

## 5. Recommendations (decisive)

1. **Adopt the §3 reference network as the canonical model** — it is the only source that
   matches the deployed reality (2 DCs × clouds × telcos × redundancy).
2. **Seed NAC fixture configs from Batfish's `example`, `hybrid-cloud-aws`, `cloud-azure`**
   to prove the importer before writing any of our own configs.
3. **Ground the telco/transit layer in CAIDA serial-2** around our ASN (subset, valve-free
   validated) rather than inventing relationships; cite under AUA.
4. **Validate the simulator against RouteViews/RIPE RIS**: replay a public prefix,
   compare predicted AS path to observed tables; cheap and decisive correctness check.
5. **Study NetComplete for the NAC model and ORR for the RR/IGP-metric semantics**; copy
   Batfish's config-parsing strategy (it has already solved multi-vendor).
6. **Do not** try to model telco/cloud internals in fidelity (RFC 7938 gives internal scale;
   SIM-F-10/Non-goals apply).

## 6. Suggested next step

Create `fixtures/` + `model/` sketch: (a) the §3 reference network as the first YAML/DSL
declaration, (b) import-adapters skeleton for Batfish configs, (c) one CI baseline-path
assertion set. This is the REQUIREMENTS.md milestone (§6).

---

### Sources (fetch-verified unless noted)

- RFC 7938, "Use of BGP for Routing in Large-Scale Data Centers" — datatracker.ietf.org/doc/html/rfc7938 (fetched, contents confirmed)
- CAIDA AS Relationships dataset page — caida.org/catalog/datasets/as-relationships/ (fetched; serial-1/2, valley-free, customer cones, AUA)
- Batfish `networks/` directory — github.com/batfish/batfish/tree/master/networks (fetched; example, hybrid-cloud-aws, cloud-azure/azure_configs)
- NSDI '18 NetComplete / Net2Text program entries — usenix.org/conference/nsdi18/technical-sessions (fetched; titles+authors confirmed)
- SIGCOMM '21 AnyOpt entry — conferences.sigcomm.org/sigcomm/2021/program.html (fetched; title/abstract confirmed)
- Internet Topology Zoo — topology-zoo.org (site timed out during research; classic JSAC 2011 dataset, citation standard)
- Meta ORR engblog & Express Backbone (SIGCOMM '21) — known by title; verify URLs before linking
- RouteViews routeviews.org, RIPE RIS, PeeringDB peeringdb.com — well-established public services (not fetched)