# Scope-down decisions

Living document. Each decision narrows the initial requirements (see
`REQUIREMENTS.md`) until we ship an MVP; everything that falls out of scope is recorded
here so it can be re-considered against the full requirements later.

Format of one decision block:

| Field | Value |
|-------|-------|
| Date | YYYY-MM-DD |
| Decision | one-line statement |
| Rationale | why |
| Affects (req IDs) | REQUIREMENTS.md IDs this narrows |
| Consequence for NAC/DIA/SIM | what drops out / stays |
| Revisit triggers | when we might undo this |

---

## D1 — Private networking only

| Field | Value |
|-------|-------|
| Date | 2026-10-17 |
| Decision | Scope the modeled network to **private connectivity only**: private links between on-prem DCs and cloud regions in both directions, and between on-prem DCs. Public internet transit / telco peers / IXPs are out of the initial model. |
| Rationale | The topology that matters for the failure stories in scope is the private underlay/overlay between our DCs and each cloud region. Telco public transit can be added later as summarized connectors without changing the core engine. |
| Affects (req IDs) | NAC-M-02 (AS/peering surface), NAC-I-02 (cloud importers), DIA-P-02 (ranks), DIA-P-07 (layers), SIM-F-10 (summarized telco), SIM-S-07 (blackhole). |

### In scope (must model)

- On-prem DCs (multiple): core/edge/aggregation fabric, inter-DC private links.
- Private cloud connectivity, per cloud provider:
  - AWS **Direct Connect** (dedicated + VIF into VPC/TGW), AWS Transit Gateway.
  - GCP **Cloud Interconnect** (dedicated/partner, VLAN attachments) + VPC peering where relevant.
  - Azure **ExpressRoute** (private peering, MPLS headers) + route advertisements.
- Cloud-side private routing constructs: VPC/TGW route tables, route propagation, cloud
  backbone treated as the cloud's private AS (16509 / 15169 / 8075).
- BGP between our edge routers and the cloud gateways/VLAN attachments (eBGP, multi-VRF
  if per-tenant), iBGP + RR inside our AS, IGP (OSPF) for next-hop resolution.
- Redundant private paths: each DC-to-region private path must exist in ≥2 forms so
  failure questions have a meaningful "next path".

### Out of scope (for now)

- Public internet transit / settlement-free peering / IXP route servers.
- Telco MPLS/other public WAN as a routing element (partners may carry our private
  cloud links, but they are modelled as opaque transport, not BGP participants).
- Internet-egress policy (outbound TE over transit, AS-path prepend for public traffic).
- Routing validation over RouteViews/RIPE RIS for public prefixes (see RESEARCH §5).

### Consequences

- **NAC**: model surface = our AS + cloud ASes/connectors only. Live-import scope =
  Direct Connect / Cloud Interconnect / ExpressRoute state + cloud route tables, plus
  our DC devices. No telco config import in v1.
- **DIA**: ranks collapse to DC-core → DC-edge → cloud regions; telco/IXP layer skipped.
  All paths shown are private; status overlay = private path/session state only.
- **SIM**: "next path A→B" is evaluated over private interconnects; failure library =
  DC link/node, interconnect/VIF/VLAN-attachment, cloud region, inter-DC link. Cloud
  region loss is a first-class scenario; anycast across regions is a natural query.
- Path preference still uses the full BGP decision series from RF-1; the preference
  knobs (local-pref/MED/communities) are now applied to private interconnects only.

### Open decisions (deferred)

- Whether per-tenant separation (VRFs / separate VIFs per environment) is part of the
  model in the first pass, or "one logical private path per DC×region pair".
- Whether inter-DC private fabric uses MPLS/SRTE or plain routed IGP internally.

### Revisit triggers

- When public-path correctness becomes a requirement (the real network's telco partners
  go live in the model).
- When the private model proves insufficient to answer a reported outage question.

---

## Decision log

| # | Date | Statement | Status |
|---|------|-----------|--------|
| D1 | 2026-10-17 | Private networking only (DC↔cloud private links, DC↔DC); public transit/IXP deferred | Active |