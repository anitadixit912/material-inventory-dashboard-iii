# Material Stock Intelligence Platform

A BTP-hosted three-asset solution that gives warehouse managers, supply chain planners, and procurement officers a real-time stock monitoring dashboard, a natural-language stock advisor agent, and an AI-powered ATP feasibility copilot with approval-gated corrective action execution against SAP S/4HANA Cloud Public Edition.

## Business challenge

Inventory managers and supply chain teams lack a consolidated, real-time view of material stock health across storage locations. They cannot quickly identify at-risk materials, determine why stock dropped, check whether a customer order can be confirmed (Available-to-Promise), or simulate and execute corrective supply chain actions — without navigating multiple S/4HANA transactions or relying on expert SAP knowledge.

The platform resolves this with three integrated components deployed on SAP BTP Cloud Foundry (us10):

1. **Material Stock Dashboard (CAP)** — Visual two-panel dashboard with sufficient-stock and at-risk-materials lists, configurable thresholds, and an embedded chatbox.
2. **NLI Stock Advisor Agent** — Conversational AI agent for natural-language stock queries using 6 tools that read live data from the CAP service.
3. **Inventory ATP Agent** — Agentic copilot for deep ATP analysis: 5 sub-intents, 10 tools, role-based tool policy, business milestone logging, and approval-gated execution of corrective actions (STO, planned order conversion, PIR adjustment, PO expediting).

## Key Milestones

- **M1 — Signal Perception**: Stock and demand data successfully retrieved from S/4HANA (`get_material_stock`, `get_demand_elements`).
- **M2 — Root-Cause Analysis**: Agent synthesises root cause from stock and demand data (`agent._run_agent()`).
- **M3 — ATP Feasibility**: ATP check completed with confirmed quantity and date (`run_atp_check`).
- **M4 — Options Simulated**: Ranked corrective action options returned for a shortfall scenario (`propose_corrective_actions`).
- **M5 — Approved Execution**: Write action confirmed by user and submitted to S/4HANA (write tools).
- **M6 — Dashboard Rendered**: Both stock panels visible and populated in the browser (CAP + React frontend).

## Business Architecture (RBA)

### End-to-End Process

Plan to Fulfill (E2E)

### Process Hierarchy

```
Plan to Fulfill (E2E)
└── Manage Fulfillment (generic)
    └── Manage supply chain data and operations (BPS-342)
        └── Manage inventory and warehouse operations
        └── Balance inventory
        └── Confirm customer order delivery (ATP check)
        └── Execute corrective replenishment actions
```

### Summary

The platform directly supports "Manage supply chain data and operations" within the Plan to Fulfill E2E by providing real-time inventory visibility, AI-assisted diagnosis, ATP feasibility checking, and supervised execution of corrective supply chain actions.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | Gap? | Notes / assumptions |
| ---------------------- | ----------------------- | ---------- | ----------------- | ---- | ------------------- |
| Read material stock levels by storage location | SAP S/4HANA Cloud Public Edition – Inventory Analytics and Control (SC765) | `sap.s4:apiResource:API_MATERIAL_STOCK_SRV:v1` | — | No | OData Read API available; no MCP server found — direct API integration |
| Classify materials as sufficient vs. at-risk | SAP S/4HANA Cloud Public Edition – Inventory Analytics and Control (SC765) | `sap.s4:apiResource:API_MATERIAL_STOCK_SRV:v1` | — | Partial | Reorder point available in API; safety stock % threshold logic is custom |
| Display storage location for at-risk materials | SAP S/4HANA Cloud Public Edition – Internal Warehouse Management (SC841) | `sap.s4:apiResource:API_MATERIAL_STOCK_SRV:v1` | — | No | Standard field in Material Stock API |
| Configurable threshold (safety stock %) | Not covered by standard SAP reporting | — | — | Yes | Custom threshold UI required |
| Natural-language stock queries | Not covered by standard SAP products | — | — | Yes | Custom NLI agent required; LLM via SAP Generative AI Hub (gpt-4o) |
| ATP feasibility check (Available-to-Promise) | SAP S/4HANA Cloud – Advanced ATP (CE_APIAVAILTOPROMISECHECK_0001) | `sap.s4:apiResource:CE_APIAVAILTOPROMISECHECK_0001:v1` | — | No | OData API available; no MCP server — direct integration |
| Read demand elements / MRP situation | SAP S/4HANA Cloud – Materials Planning (SC540) | `sap.s4:apiResource:API_MRP_MATERIALS_SRV_01:v1` | — | No | Supply/Demand API available |
| Read and convert planned orders | SAP S/4HANA Cloud – Production Planning (SC500) | `sap.s4:apiResource:API_PLANNED_ORDERS:v1` | — | No | Planned Orders API available |
| Adjust planned independent requirements (PIR) | SAP S/4HANA Cloud – Demand Management (SC530) | `sap.s4:apiResource:API_PLND_INDEP_RQMT_SRV:v1` | — | No | PIR API available |
| Create stock transport order (inter-plant transfer) | SAP S/4HANA Cloud – Inventory Management (SC765) | `sap.s4:apiResource:CE_STOCKTRANSPORTORDER_0001:v1` | — | No | STO API available |
| Approval-gated write execution with role policy | Not covered by standard SAP products | — | — | Yes | Custom approval card pattern in agent required |
| Proactive safety stock watchlist alerts | Not covered by standard SAP products | — | — | Yes | Custom watchlist_monitor tool required |
| Business milestone logging for auditability | Not covered by standard SAP products | — | — | Yes | Custom M1–M5 logging implemented in agent tools |
| Consolidated dashboard for multiple user roles | SAP Analytics Cloud (optional) | — | — | Yes | Custom BTP dashboard is leaner and more targeted |

### Key findings

- The **Material Stock – Read** OData API (`API_MATERIAL_STOCK_SRV`) provides unrestricted stock, storage location, reorder point, and safety stock — sufficient for the dashboard's core requirements.
- The **Advanced ATP** API (`CE_APIAVAILTOPROMISECHECK_0001`) provides ATP confirmation quantities and dates — sufficient for the ATP feasibility check.
- No MCP servers exist for any of the 6 APIs used; all integrations are via direct OData calls from the agent tools. EDMX files are staged for future MCP server registration.
- Safety stock percentage threshold classification is custom logic in the CAP backend.
- Role-based tool access policy (PLANNER / SALES_OPS / CUSTOMER_SERVICE / PROCUREMENT_MANAGER) is custom logic in the ATP agent.
- SAP Analytics Cloud could partially cover the dashboard use case but adds licensing overhead; a focused BTP Extension is a leaner fit.
- All six target user roles are served by a shared dashboard; the NLI and ATP agents enforce role-based tool access.

## Recommendations

### Material Stock Intelligence Platform on SAP BTP (CF us10)

#### Executive Summary

Three-component BTP Extension: CAP dashboard + NLI stock advisor agent + ATP agentic copilot, all deployed to Cloud Foundry us10.

#### Recommended Solution

Build a BTP Extension consisting of:

1. **`material-stock-dashboard-cap`** — CAP Node.js backend that fetches stock data from `API_MATERIAL_STOCK_SRV`, applies classification logic, and exposes `/stock/MaterialStockView` (OData v4) and `/stock/chat`. React frontend (SAP UI5 Web Components) renders two panels: sufficient-stock list and at-risk materials list with storage location, threshold configuration, and chatbox.

2. **`nli-stockadv-agent`** — Python LangGraph agent for natural-language stock queries. 6 tools reading live data from the CAP service: `get_material_stock`, `get_atrisk_materials`, `get_sufficient_materials`, `get_stock_summary`, `get_critical_materials_by_plant`, `send_email`.

3. **`inventory-atp-agent`** — Python LangGraph agent for deep ATP analysis. 10 tools: 6 read/simulation tools + 4 approval-gated write tools. 5 sub-intents: Explain_Stock_Drop, Check_Order_Feasibility, Simulate_Options, Execute_With_Approval, Protect_Service_Level. Role-based tool policy. Business milestone logging (M1–M5).

#### Problem Statement

Inventory managers and planners have no single consolidated view to distinguish healthy stock from at-risk stock, no conversational interface to query stock status, and no guided workflow to check ATP feasibility or execute corrective actions without expert SAP knowledge.

#### Affected User Roles

- Warehouse / Inventory Manager
- Supply Chain Planner
- Sales Operations Analyst
- Procurement Manager
- Plant Manager
- Customer Service Representative

#### Important factors

##### Real-time data from S/4HANA Cloud Public Edition

All three components ultimately read from live S/4HANA OData APIs via BTP Destination Service (OAuth 2.0), ensuring data accuracy.

##### Approval-gated write execution

Write tools in the ATP agent always present a human-readable action card requiring explicit confirmation before any S/4HANA write operation is submitted.

##### Role-based tool access

The ATP agent enforces a role policy: PLANNER has full access; SALES_OPS and CUSTOMER_SERVICE have read + ATP access; PROCUREMENT_MANAGER has PO-related tools + read access.

##### Business milestone logging

Each agent interaction logs structured milestone events (M1–M5) for AI decision auditability and operational monitoring.

#### Potential risks

##### API connectivity and authorisation

All 6 S/4HANA OData API destinations must be correctly configured on BTP. Misconfiguration will prevent data from loading.

##### Safety stock and reorder point data availability

These fields must be maintained in the S/4HANA material master; if missing, classification defaults to "sufficient" incorrectly.

##### MCP translation.json unavailability

The `generate_mcp_translation` platform endpoint returns HTTP 404 in this environment. Tools are wired directly; EDMX files are staged for future MCP server registration.

##### LLM model availability

`gpt-4o` is used for both agents; `sap/anthropic--claude-4.5-sonnet` was not available in the AI Core resource group at deployment time.

#### Recommended solution category

BTP Extension, AI Agent

#### Intent fit
98%
