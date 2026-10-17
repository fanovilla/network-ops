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

## D2 — Expand out-of-scope for the MVP

| Field | Value |
|-------|-------|
| Date | 2026-10-17 |
| Decision | Out of scope for now: **VPN** overlays (only dedicated private circuits in-scope), **branches / meet-me rooms**, **DR sites** (model as additional on-prem DC), **customer/partner sites**, **cloud providers beyond AWS/Azure/GCP**, and the **physical/optical layer** (focus on BGP links). |
| Rationale | Keep the modeled surface on dedicated private BGP connectivity; collapse failure analysis to DC/region scope rather than transport detail. |
| Affects (req IDs) | NAC-M-02 (interconnect kinds), NAC-I-02 (provider importers), DIA-P-02 (ranks), SIM-S-02 (failure library), SIM-F-10 (summarized transport). |

### Details & consequences

- Effective interconnect kinds are **Direct Connect / Cloud Interconnect / ExpressRoute**. The `vpn` enum value and `examples/aws-hybrid.yaml` (Batfish `hybrid-cloud-aws` fixture) are retained solely as an **import-corpus drill** for NAC-I-01 — not a representation of the in-scope product (D1 covers only dedicated private circuits).
- **DC / region failure grouping**: `device.site` and `device.region` are introduced as the unit a failure scenario can target (SIM-S-02) — failing a site or region brings down every device in that group. No transport/optical details are modeled; a DC or region is just a grouping of BGP speakers and links.
- **Provider limit (AWS/Azure/GCP)** is a product/app rule, not a model constraint — the model stays extensible for new providers (X-07). **Megaport is added as an interconnect-fabric provider (D3)**, not a cloud provider.
- Not modeled now: IPsec/SD-WAN tunnels, EVPN/VXLAN overlays, DWDM/dark fiber, security appliances (beyond MVE as a BGP edge device), IPAM/subnet hierarchies (deferred to a later scope-down pass).

### Revisit triggers

- Any requirement to model remote/branch connectivity or non-dedicated circuits (re-introduce `vpn`).
- New cloud provider on the real network (relax the AWS/Azure/GCP app rule).
- DR as a distinct site type once BCP planning needs it.

---

## D3 — Megaport MVE (interconnect fabric) in scope

| Field | Value |
|-------|-------|
| Date | 2026-10-17 |
| Decision | Model **Megaport Managed Virtual Edge (MVE) with Palo Alto VM-Series** as part of the private-connectivity surface. MVE is a virtual edge device (NVA) running on Megaport's SDN fabric; on-prem DCs reach it over VXCs; it fans out to AWS via a hosted **Direct Connect** connection (with its virtual interface), to Azure via **ExpressRoute**, and to GCP equivalently. |
| Rationale | Dedicated private circuits often terminate in an MVE rather than your own edge router (per megaport.com docs for AWS/Azure). The MVE is a BGP speaker in the path, so failure/redundancy analysis must see it. |
| Affects (req IDs) | NAC-M-02 (device roles, interconnect kinds), NAC-I-02 (megaport/cloud importers), DIA-P-02 (render MVE layer), SIM-S-02 (MVE/leg failure), SIM-F-10 (Megaport fabric is L2 transport; legs are the BGP reachability units). |

### Modeling

- `DeviceRole.virtual_edge` for MVE/other virtual NVAs; `platform` records the NVA type.
- **`VirtualCrossConnect` (VXC) is a first-class entity**: each VXC has an `a_end` and a `b_end`, each with its own `service`, `location`, `device`/`interface`, `vlan`, `vif`, and `capacity`. The two ends may be in **different Megaport locations**, and each end is independently addressable.
- **VXC is a failure unit** (SIM-S-02): a VXC leg, or one of its locations, can fail on its own — independent of the MVE and of the cloud-side legs — so a DC→MVE, MVE→cloud, or location-level failure is simulated per VXC, not hidden inside a device.
- A BGP session runs over a `vxc` (via `BgpSession.vxc`, alongside `interconnect` for the dedicated-kind termination).
- A full path is a chain: `vxc (dc→mve)` + `vxc (mve→cloud leg)` + optional dedicated `interconnect` (Direct Connect / Cloud Interconnect / ExpressRoute) at the cloud side.
- Megaport runs as `provider` with its own ASN (informational; VXC is L2 transport); the MVE's BGP ASN is a per-deployment parameter. Cloud-side peer ASNs follow the docs: AWS default 64512 (private VIF), Azure fixed 12076.
- BGP MD5 shared keys are deliberately **not** stored in the model.

### Revisit triggers

- Other fabric providers (Equinix Fabric, PacketFabric) — generalize `megaport_vxc` into a `fabric_vxc` kind.
- If firewall/zone semantics of VM-Series ever need modeling (currently it's an opaque BGP edge).

---

## Decision log

| # | Date | Statement | Status |
|---|------|-----------|--------|
| D1 | 2026-10-17 | Private networking only (DC↔cloud private links, DC↔DC); public transit/IXP deferred | Active |
| D2 | 2026-10-17 | Out of scope for MVP: VPN, branches/meet-me rooms, DR-as-site, customer sites, providers beyond AWS/Azure/GCP, physical layer | Active |
| D3 | 2026-10-17 | Megaport MVE (Palo Alto VM-Series) in scope: `virtual_edge` role, `megaport_vxc` kind, eBGP legs to AWS DX / Azure ER | Active |