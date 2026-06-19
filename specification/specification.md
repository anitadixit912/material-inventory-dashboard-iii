# Specification

> **Guidelines**: Read [guidelines.md](./guidelines.md) before executing ANY tasks below.

Check off items as completed.

---

## Design

### Solution Overview

The **Material Stock Intelligence Platform** is a BTP-hosted solution that gives warehouse managers, supply chain planners, and procurement officers a real-time view of inventory health and an AI-powered assistant to diagnose stock issues, check order feasibility, simulate corrective options, and execute approved supply chain actions against SAP S/4HANA Cloud.

---

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    SAP BTP Cloud Foundry (us10)                          │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              material-stock-dashboard-cap                        │    │
│  │   React UI (SAP UI5 Web Components) + CAP Node.js backend        │    │
│  │                                                                  │    │
│  │   GET  /stock/MaterialStockView  (OData v4 — stock data)         │    │
│  │   POST /stock/chat               (AI chatbox action)             │    │
│  └────────────────────────┬─────────────────────────────────────────┘    │
│                           │ A2A HTTP                                     │
│                           ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    nli-stockadv-agent                            │    │
│  │   NLI Stock Advisor — conversational entry point                 │    │
│  │                                                                  │    │
│  │   Tools: get_material_stock · get_atrisk_materials               │    │
│  │          get_sufficient_materials · get_stock_summary            │    │
│  │          get_critical_materials_by_plant · send_email            │    │
│  │                                                                  │    │
│  │   Reads live stock data ◄── CAP /stock/MaterialStockView         │    │
│  └────────────────────────┬─────────────────────────────────────────┘    │
│                           │ A2A HTTP (deep ATP analysis)                 │
│                           ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   inventory-atp-agent                            │    │
│  │   ATP Agentic Copilot — 5 sub-intents, role-based tool policy    │    │
│  │                                                                  │    │
│  │   READ TOOLS                    WRITE TOOLS (approval-gated)     │    │
│  │   ─────────────────────────     ──────────────────────────────   │    │
│  │   get_material_stock            create_stock_transport_order     │    │
│  │   get_demand_elements           convert_planned_order            │    │
│  │   run_atp_check                 adjust_pir                       │    │
│  │   get_planned_orders            flag_po_expedite                 │    │
│  │   propose_corrective_actions                                     │    │
│  │   watchlist_monitor                                              │    │
│  └────────────────────────┬─────────────────────────────────────────┘    │
│                           │ BTP Destination Service (OAuth 2.0)          │
└───────────────────────────┼──────────────────────────────────────────────┘
                            │
                            ▼
          ┌──────────────────────────────────────┐
          │   SAP S/4HANA Cloud Public Edition    │
          │                                      │
          │   API_MATERIAL_STOCK_SRV:v1           │
          │   API_MRP_MATERIALS_SRV_01:v1         │
          │   CE_APIAVAILTOPROMISECHECK_0001:v1   │
          │   API_PLANNED_ORDERS:v1               │
          │   API_PLND_INDEP_RQMT_SRV:v1          │
          │   CE_STOCKTRANSPORTORDER_0001:v1      │
          └──────────────────────────────────────┘
```

---

### Component Inventory

| Component | Technology | CF Route | Health Check |
|---|---|---|---|
| `material-stock-dashboard-cap` | CAP Node.js + React (UI5 WC) | `material-stock-dashboard-cap.cfapps.us10.hana.ondemand.com` | `/stock` → HTTP 200 ✅ |
| `nli-stockadv-agent` | Python, LangGraph, gunicorn | `nli-stockadv-agent.cfapps.us10.hana.ondemand.com` | `/.well-known/agent.json` → HTTP 200 ✅ |
| `inventory-atp-agent` | Python, LangGraph, gunicorn | `inventory-atp-agent.cfapps.us10.hana.ondemand.com` | `/.well-known/agent.json` → HTTP 200 ✅ |

**BTP Services bound to all apps:**

| Service Instance | Type | Purpose |
|---|---|---|
| `proj-vector-destination-service` | SAP Destination Service | S/4HANA OData connectivity with OAuth 2.0 |
| `material-stock-dashboard-xsuaa` | SAP XSUAA | User authentication for CAP dashboard (CAP only) |

---

### E2E Scenario Flows

#### Scenario A — "Why did stock drop?" (Explain_Stock_Drop)

```
User types in chatbox: "Why did FG-001 stock drop in plant 1010?"
  │
  ▼
material-stock-dashboard-cap  POST /stock/chat
  │  forwards message to nli-stockadv-agent via A2A
  ▼
nli-stockadv-agent
  │  detects deep ATP analysis needed → forwards to inventory-atp-agent
  ▼
inventory-atp-agent — sub-intent: Explain_Stock_Drop
  │
  ├─ [M1] get_material_stock(FG-001, 1010)
  │         └─► API_MATERIAL_STOCK_SRV → A_MaterialStock
  │             returns: unrestricted=120 EA, safety_stock=50 EA
  │             logs: M1.achieved: stock_perception_complete
  │
  ├─ [M1] get_demand_elements(FG-001, 1010)
  │         └─► API_MRP_MATERIALS_SRV_01 → SupplyDemandItems
  │             returns: OrdRes -200 EA on Jul 1, PurOrd +300 EA on Jul 10
  │             logs: M1.achieved: stock_perception_complete (demand layer)
  │
  └─ [M2] Agent synthesises root cause
           logs: M2.achieved: root_cause_identified
           Response: "Stock dropped due to sales order reservation 1000001
                      (-200 EA on Jul 1). Inbound PO 4500001 (+300 EA)
                      arrives Jul 10, restoring cover."
  ▼
User sees root-cause narrative in chatbox
```

#### Scenario B — "Can we confirm this order?" (Check_Order_Feasibility)

```
User: "Can we confirm 300 EA of FG-001 for delivery by July 5?"
  ▼
inventory-atp-agent — sub-intent: Check_Order_Feasibility
  │
  └─ [M3] run_atp_check(FG-001, 1010, qty=300, date=2026-07-05)
           └─► CE_APIAVAILTOPROMISECHECK_0001 → CheckAvailabilityWithoutResvn
               confirmed=300 EA, atp_date=2026-07-05, is_fully_confirmed=true
               logs: M3.achieved: atp_check_complete
  ▼
User sees: "300 EA confirmed for 5 Jul. Order is fully feasible."
```

#### Scenario C — "What are our options?" (Simulate_Options)

```
User: "We have a shortfall of 150 EA by July 3. What can we do?"
  ▼
inventory-atp-agent — sub-intent: Simulate_Options
  │
  ├─ get_planned_orders(FG-001, 1010)   → planned order 0000100001, 500 EA, ends Jul 10
  ├─ get_demand_elements(FG-001, 1010)  → demand context
  │
  └─ [M4] propose_corrective_actions(FG-001, 1010, shortfall=150, date=2026-07-03)
           Rank 1 — Convert Planned Order 0000100001   (7 days, covers 500 EA)
           Rank 2 — Stock Transport Order from 1020    (5 days, needs approval)
           Rank 3 — PIR reduction                      (frees 150 EA, needs approval)
           Rank 4 — Partial fulfillment + backorder
           logs: M4.achieved: options_simulated
  ▼
User sees ranked options with trade-offs and lead times
```

#### Scenario D — "Convert the planned order" (Execute_With_Approval)

```
User: "Convert planned order 0000100001"
  ▼
inventory-atp-agent — APPROVAL GATE triggered
  │
  Agent presents ACTION CARD:
  ┌───────────────────────────────────────────────────┐
  │  ⚠️  Approval Required                            │
  │  Action:    Convert Planned Order                 │
  │  Order:     0000100001  |  Plant: 1010            │
  │  Quantity:  500 EA                                │
  │  Impact:    +500 EA available by 2026-07-10       │
  │  Type "confirm" to proceed or "reject" to cancel  │
  └───────────────────────────────────────────────────┘
  │
User types: "confirm"
  │
  └─ [M5] convert_planned_order(0000100001, "production")
           └─► API_PLANNED_ORDERS → PlannedOrderSchedule
               converted_document_number=PRD0000100001, status=CONVERTED
               logs: M5.achieved: execution_complete
  ▼
User sees: "Planned order converted to PRD0000100001."
```

#### Scenario E — Safety Stock Alert (Protect_Service_Level)

```
Scheduled / proactive check
  ▼
inventory-atp-agent — sub-intent: Protect_Service_Level
  │
  └─ watchlist_monitor([{material: FG-001, plant: 1010, threshold: 50}])
       ├─ get_material_stock(FG-001, 1010) → unrestricted=45 EA
       └─ 45 < 50 → BREACH
          returns: { alert_type: SAFETY_STOCK_BREACH, breach_severity: HIGH,
                     material: FG-001, plant: 1010,
                     current_stock: 45, threshold: 50 }
  ▼
BTP Notifications layer delivers alert to user
```

---

### Role-Based Tool Policy (inventory-atp-agent)

| Role | Allowed Tools |
|---|---|
| `PLANNER` | All tools (read + write) |
| `SALES_OPS` | `get_material_stock`, `run_atp_check`, `propose_corrective_actions` |
| `CUSTOMER_SERVICE` | `get_material_stock`, `run_atp_check` |
| `PROCUREMENT_MANAGER` | `flag_po_expedite`, `get_demand_elements`, `get_planned_orders` |

Write tools (`create_stock_transport_order`, `convert_planned_order`, `adjust_pir`, `flag_po_expedite`) always require **explicit user confirmation** via approval card before execution.

---

### Observability — Business Milestones

| Milestone | Log Pattern | Where |
|---|---|---|
| M1 — Signal Perception | `M1.achieved: stock_perception_complete` | `get_material_stock`, `get_demand_elements` |
| M2 — Root-Cause Analysis | `M2.achieved: root_cause_identified` | `agent._run_agent()` |
| M3 — ATP Feasibility | `M3.achieved: atp_check_complete` | `run_atp_check` |
| M4 — Options Simulated | `M4.achieved: options_simulated` | `propose_corrective_actions` |
| M5 — Approved Execution | `M5.achieved: execution_complete` | all write tools |

---

### MCP Integration Status

All 6 S/4HANA OData API specs (EDMX) are staged in `specification/inventory-atp-agent/mcps/`. The `generate_mcp_translation` platform endpoint returns HTTP 404 in this environment — `translation.json` files are pending platform availability. Tools are wired directly via `mcp_tools.py`; `mcp-mock.json` provides test doubles.

| API | ORD ID | EDMX | translation.json |
|---|---|---|---|
| Material Stock Read | `sap.s4:apiResource:API_MATERIAL_STOCK_SRV:v1` | ✅ staged | ⏳ pending |
| Material Planning / MRP | `sap.s4:apiResource:API_MRP_MATERIALS_SRV_01:v1` | ✅ staged | ⏳ pending |
| Advanced ATP Check | `sap.s4:apiResource:CE_APIAVAILTOPROMISECHECK_0001:v1` | ✅ staged | ⏳ pending |
| Planned Orders | `sap.s4:apiResource:API_PLANNED_ORDERS:v1` | ✅ staged | ⏳ pending |
| Planned Indep. Requirements | `sap.s4:apiResource:API_PLND_INDEP_RQMT_SRV:v1` | ✅ staged | ⏳ pending |
| Stock Transport Order | `sap.s4:apiResource:CE_STOCKTRANSPORTORDER_0001:v1` | ✅ staged | ⏳ pending |

---

## Solution Setup

- [x] Create asset directory: `mkdir -p assets/material-stock-dashboard-cap/`
- [x] Invoke `setup-solution` skill to create `solution.yaml` and `asset.yaml` files
- [x] Validate `asset.yaml` and `solution.yaml` exist and are well-formed

---

## Asset Implementation

- [x] Execute [specification/material-stock-dashboard-cap/specification.md](./material-stock-dashboard-cap/specification.md) — CAP backend + React UI + OData integration + tests ✅
- [x] Execute [specification/nli-stockadv-agent/specification.md](./nli-stockadv-agent/specification.md) — 6 tools, A2A server, LangGraph agent, CF deployment, tests ✅
- [x] Execute [specification/inventory-atp-agent/specification.md](./inventory-atp-agent/specification.md) — 10 tools, watchlist, milestones, role policy, 56 tests, 85% coverage ✅
- [x] Cross-implementation compatibility check: CAP `/stock/chat` → nli-stockadv-agent → inventory-atp-agent; agents read CAP `/stock/MaterialStockView`; React UI calls CAP only
