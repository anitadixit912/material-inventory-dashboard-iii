# E2E Solution Architecture — Material Stock Intelligence Platform

> **Last updated**: 2026-06-18  
> **Deployment target**: SAP BTP Cloud Foundry, region `us10`

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SAP BTP Cloud Foundry (us10)                            │
│                                                                             │
│  ┌──────────────────────────────────┐                                       │
│  │  material-stock-dashboard-cap    │  React UI + CAP Node.js backend       │
│  │  cfapps.us10.hana.ondemand.com   │                                       │
│  │                                  │                                       │
│  │  ┌──────────────┐ ┌───────────┐  │                                       │
│  │  │  React UI    │ │ CAP srv   │  │  OData /odata/v4/stock/               │
│  │  │  (UI5 WC)    │ │ Node.js   │  │  REST  /stock/chat (AI action)        │
│  │  └──────┬───────┘ └─────┬─────┘  │                                       │
│  └─────────│───────────────│────────┘                                       │
│            │               │                                                │
│            │ HTTP          │ HTTP (Agent A2A)                               │
│            │               ▼                                                │
│  ┌─────────│──────────────────────────────────────────────┐                 │
│  │         │         nli-stockadv-agent                   │                 │
│  │         │         cfapps.us10.hana.ondemand.com        │                 │
│  │         │                                              │                 │
│  │         │  LangGraph + ChatLiteLLM (SAP AI Core)       │                 │
│  │         │  Agent card: /.well-known/agent.json         │                 │
│  │         │  Tools: get_stock_summary, chat_with_data    │                 │
│  │         │                                              │                 │
│  └─────────│──────────────────────────────────────────────┘                 │
│            │                                                                │
│            │ HTTP (Agent A2A / direct API)                                  │
│            ▼                                                                │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │                   inventory-atp-agent                            │       │
│  │                   cfapps.us10.hana.ondemand.com                  │       │
│  │                                                                  │       │
│  │  LangGraph + ChatLiteLLM (SAP AI Core)                           │       │
│  │  Agent card: /.well-known/agent.json                             │       │
│  │  Role-based tool policy (PLANNER / SALES_OPS / CS / PROC_MGR)   │       │
│  │                                                                  │       │
│  │  ┌─────────── READ TOOLS ──────────────────────────────────┐    │       │
│  │  │  get_material_stock    → API_MATERIAL_STOCK_SRV         │    │       │
│  │  │  get_demand_elements   → API_MRP_MATERIALS_SRV_01       │    │       │
│  │  │  run_atp_check         → CE_APIAVAILTOPROMISECHECK_0001  │    │       │
│  │  │  get_planned_orders    → API_PLANNED_ORDERS             │    │       │
│  │  │  propose_corrective_actions (orchestrator, no direct API)│    │       │
│  │  │  watchlist_monitor     → calls get_material_stock       │    │       │
│  │  └─────────────────────────────────────────────────────────┘    │       │
│  │                                                                  │       │
│  │  ┌─────────── WRITE TOOLS (approval-gated) ───────────────┐     │       │
│  │  │  create_stock_transport_order → CE_STOCKTRANSPORTORDER  │     │       │
│  │  │  convert_planned_order        → API_PLANNED_ORDERS PATCH│     │       │
│  │  │  adjust_pir                   → API_PLND_INDEP_RQMT_SRV │     │       │
│  │  │  flag_po_expedite             → structured payload       │     │       │
│  │  └─────────────────────────────────────────────────────────┘     │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                         │                                                   │
│                         │ BTP Destination Service (OAuth 2.0)               │
└─────────────────────────│───────────────────────────────────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────────┐
           │  SAP S/4HANA Cloud Public Edition │
           │                                  │
           │  OData APIs:                     │
           │  • API_MATERIAL_STOCK_SRV:v1     │
           │  • API_MRP_MATERIALS_SRV_01:v1   │
           │  • CE_APIAVAILTOPROMISECHECK_0001:v1 │
           │  • API_PLANNED_ORDERS:v1         │
           │  • API_PLND_INDEP_RQMT_SRV:v1   │
           │  • CE_STOCKTRANSPORTORDER_0001:v1│
           └──────────────────────────────────┘
```

---

## 2. Component Inventory

| Component | Technology | CF Route | Health Endpoint |
|---|---|---|---|
| `material-stock-dashboard-cap` | CAP Node.js + React (UI5 WC) | `material-stock-dashboard-cap.cfapps.us10.hana.ondemand.com` | `/stock` |
| `nli-stockadv-agent` | Python, LangGraph, gunicorn | `nli-stockadv-agent.cfapps.us10.hana.ondemand.com` | `/.well-known/agent.json` |
| `inventory-atp-agent` | Python, LangGraph, gunicorn | `inventory-atp-agent.cfapps.us10.hana.ondemand.com` | `/.well-known/agent.json` |

### BTP Services (bound to all apps)

| Service Instance | Type | Purpose |
|---|---|---|
| `proj-vector-destination-service` | SAP Destination Service | S/4HANA OData connectivity with OAuth |
| `material-stock-dashboard-xsuaa` | SAP XSUAA | Authentication for CAP dashboard (CAP only) |

---

## 3. MCP Tool Integration Status

The solution uses 6 SAP S/4HANA OData APIs. The `generate_mcp_translation` platform service returned HTTP 404 (feature unavailable in this environment). All 6 EDMX files are staged in `specification/inventory-atp-agent/mcps/`. MCP tool calls are implemented directly in each tool file via the `mcp_tools.py` pattern; `mcp-mock.json` provides deterministic test doubles.

| API | ORD ID | MCP Translation | Status |
|---|---|---|---|
| Material Stock Read | `sap.s4:apiResource:API_MATERIAL_STOCK_SRV:v1` | `mcps/material-stock-read/` — EDMX staged, `translation.json` pending platform | ⚠️ EDMX ready |
| Material Planning / MRP | `sap.s4:apiResource:API_MRP_MATERIALS_SRV_01:v1` | `mcps/material-planning-data-mrp/` — EDMX staged | ⚠️ EDMX ready |
| Advanced ATP Check | `sap.s4:apiResource:CE_APIAVAILTOPROMISECHECK_0001:v1` | `mcps/advanced-atp-check/` — EDMX staged | ⚠️ EDMX ready |
| Planned Orders | `sap.s4:apiResource:API_PLANNED_ORDERS:v1` | `mcps/planned-orders/` — EDMX staged | ⚠️ EDMX ready |
| Planned Indep. Requirements | `sap.s4:apiResource:API_PLND_INDEP_RQMT_SRV:v1` | `mcps/planned-independent-requirements/` — EDMX staged | ⚠️ EDMX ready |
| Stock Transport Order | `sap.s4:apiResource:CE_STOCKTRANSPORTORDER_0001:v1` | `mcps/stock-transport-order/` — EDMX staged | ⚠️ EDMX ready |

**When `generate_mcp_translation` becomes available**: run the `mcp-translation-file` skill once per EDMX file, then run `setup-solution` to register MCP server assets in `solution.yaml`.

---

## 4. E2E Scenario Flows

### Scenario A — "Why did stock drop?" (Explain_Stock_Drop)

```
User (Browser / Chatbox)
  │  "Why did FG-001 stock drop in plant 1010?"
  ▼
material-stock-dashboard-cap  (POST /stock/chat)
  │  forwards message + context
  ▼
nli-stockadv-agent
  │  decides: deep ATP analysis needed → forwards to inventory-atp-agent
  ▼
inventory-atp-agent  ──► sub-intent: Explain_Stock_Drop
  │
  ├── [M1] get_material_stock(FG-001, 1010)
  │     └─► API_MATERIAL_STOCK_SRV → A_MaterialStock
  │         returns: unrestricted=120 EA, safety_stock=50 EA
  │         logs: M1.achieved: stock_perception_complete
  │
  ├── [M1] get_demand_elements(FG-001, 1010)
  │     └─► API_MRP_MATERIALS_SRV_01 → SupplyDemandItems + A_MRPMaterial
  │         returns: OrdRes -200 EA on 2026-07-01, PurOrd +300 EA on 2026-07-10
  │         logs: M1.achieved: stock_perception_complete (demand layer)
  │
  └── [M2] Agent synthesises root cause
        logs: M2.achieved: root_cause_identified | primary_cause=sales_order_reservation
        Response: "Stock dropped due to sales order reservation 1000001 (-200 EA) on Jul 1.
                   Inbound PO 4500001 (+300 EA) arrives Jul 10, restoring cover."
  ▼
User sees root-cause narrative in chatbox
```

---

### Scenario B — "Can we confirm order X?" (Check_Order_Feasibility)

```
User  "Can we confirm 300 EA of FG-001 for delivery by July 5?"
  ▼
inventory-atp-agent  ──► sub-intent: Check_Order_Feasibility
  │
  └── [M3] run_atp_check(FG-001, 1010, qty=300, date=2026-07-05)
        └─► CE_APIAVAILTOPROMISECHECK_0001 → CheckAvailabilityWithoutResvn
            returns: confirmed=300 EA, atp_date=2026-07-05, is_fully_confirmed=true
            logs: M3.achieved: atp_check_complete
  ▼
User sees: "300 EA confirmed for 5 Jul. Order is fully feasible."
```

---

### Scenario C — "What are our options?" (Simulate_Options)

```
User  "We have a shortfall of 150 EA by July 3. What can we do?"
  ▼
inventory-atp-agent  ──► sub-intent: Simulate_Options
  │
  ├── get_planned_orders(FG-001, 1010)  → open planned order 0000100001, 500 EA, ends Jul 10
  ├── get_demand_elements(FG-001, 1010)  → demand context
  │
  └── [M4] propose_corrective_actions(FG-001, 1010, shortfall=150, date=2026-07-03)
        Derives 4 options ranked by lead days:
          Rank 1 — Convert Planned Order 0000100001 (7 days lead) ✅ covers 500 EA
          Rank 2 — Stock Transport Order from plant 1020 (5 days) — needs approval
          Rank 3 — PIR reduction (free 150 EA demand) — needs approval
          Rank 4 — Partial fulfillment now + backorder rest
        logs: M4.achieved: options_simulated | top_option=planned_order_conversion
  ▼
User sees ranked options with trade-offs
```

---

### Scenario D — "Convert the planned order" (Execute_With_Approval)

```
User  "Convert planned order 0000100001"
  ▼
inventory-atp-agent — APPROVAL GATE triggered
  │
  Agent presents ACTION CARD:
  ┌─────────────────────────────────────────────────────┐
  │ ⚠️  Approval Required                               │
  │ Action:   Convert Planned Order → Production Order  │
  │ Order:    0000100001                                │
  │ Quantity: 500 EA  |  Plant: 1010                   │
  │ Impact:   +500 EA available by 2026-07-10          │
  │                                                     │
  │  Type "confirm" to proceed or "reject" to cancel   │
  └─────────────────────────────────────────────────────┘
  │
User types: "confirm"
  │
  └── [M5] convert_planned_order(0000100001, "production")
        └─► API_PLANNED_ORDERS → PlannedOrderSchedule (FunctionImport / PATCH)
            returns: converted_document_number=PRD0000100001, status=CONVERTED
            logs: M5.achieved: execution_complete | action=convert_planned_order
  ▼
User sees: "Planned order converted to production order PRD0000100001."
```

---

### Scenario E — Watchlist Alert (Protect_Service_Level)

```
Scheduled call / proactive check
  ▼
inventory-atp-agent  ──► sub-intent: Protect_Service_Level
  │
  └── watchlist_monitor([{material: FG-001, plant: 1010, threshold: 50, sla_date: 2026-07-01}])
        ├── get_material_stock(FG-001, 1010)  → unrestricted=45 EA
        └── 45 < 50 threshold → BREACH
            returns: { alert_type: SAFETY_STOCK_BREACH, material: FG-001,
                       plant: 1010, current_stock: 45, threshold: 50,
                       breach_severity: HIGH }
  ▼
Caller (BTP Notifications / dashboard push) delivers alert to user
```

---

## 5. Data Flow and Security

```
Browser
  │  HTTPS
  ▼
CAP App (XSUAA-authenticated)
  │  CF-internal HTTP (A2A token forwarding)
  ▼
Agents (JWT validation via XSUAA)
  │  SAP Destination Service (OAuth 2.0 client credentials)
  ▼
S/4HANA Cloud OData APIs
```

- All inter-service calls use **SAP Destination Service** — no credentials are hardcoded.
- Write tools enforce a **human-in-the-loop approval gate** before any OData PATCH/POST.
- Role-based tool policy prevents lower-privileged roles from accessing write tools.

---

## 6. Observability

| Milestone | Log Pattern | Tool |
|---|---|---|
| M1 — Signal Perception | `M1.achieved: stock_perception_complete` | `get_material_stock`, `get_demand_elements` |
| M2 — Root-Cause Analysis | `M2.achieved: root_cause_identified` | `agent._run_agent()` |
| M3 — ATP Feasibility | `M3.achieved: atp_check_complete` | `run_atp_check` |
| M4 — Options Simulated | `M4.achieved: options_simulated` | `propose_corrective_actions` |
| M5 — Approved Execution | `M5.achieved: execution_complete` | write tools |

All tools are instrumented with OpenTelemetry custom spans (`@tracer.start_as_current_span`). `auto_instrument()` is called at startup in `main.py` before any AI framework imports.

---

## 7. Deployment Checklist Summary

| Step | Command | Status |
|---|---|---|
| Build CAP | `npm run build:all` in `assets/material-stock-dashboard-cap/` | ✅ |
| CF push CAP | `/tmp/cf push` in `assets/material-stock-dashboard-cap/` | ✅ |
| CF push NLI agent | `/tmp/cf push` in `assets/nli-stockadv-agent/` | ✅ |
| CF push ATP agent | `/tmp/cf push` in `assets/inventory-atp-agent/` | ✅ |
| Health checks | `curl https://<route>/stock` and `/.well-known/agent.json` | ✅ |

See `docs/deploy-runbook.md` for full re-deployment instructions.
