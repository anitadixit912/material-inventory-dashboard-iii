# Product Requirements Document (PRD)

**Title:** Material Stock Intelligence Platform  
**Date:** 2026-06-18  
**Owner:** Supply Chain / Inventory Management Team  
**Solution Category:** BTP Extension + AI Agents

---

## Product Purpose & Value Proposition

**Elevator Pitch:**  
Inventory managers, supply chain planners, and procurement officers waste time navigating multiple S/4HANA transactions to assess stock health and feasibility. This platform provides a unified, real-time stock monitoring dashboard coupled with two AI-powered agents: one for natural-language stock queries and another for deep ATP feasibility checks, root-cause analysis, and approval-gated execution of corrective supply chain actions.

**Business Need:**  
There is no consolidated view in SAP S/4HANA that surfaces stock risk at a glance, split by storage location. Users must run multiple reports (MB52, MB53, MD04), cross-reference safety stock and reorder point data manually, and repeat this exercise frequently. Beyond visibility, users cannot quickly check whether a sales order can be confirmed (Available-to-Promise), determine why stock dropped, or simulate corrective options — without expert SAP knowledge. This creates operational lag, stockout risk, and delayed order confirmations.

**Expected Value:**

- Reduced time to identify at-risk materials (target: from multiple transactions to a single screen)
- Proactive replenishment decisions before stockout occurs
- Natural-language stock queries for all roles (no SAP GUI expertise required)
- ATP feasibility checks in seconds rather than hours
- Approval-gated execution of corrective actions (STO, PIR, planned order conversion, PO expediting) directly from the assistant

**Product Objectives (Prioritized):**

1. Provide a real-time, categorised view of all materials by stock health status (sufficient vs. nearly out of stock)
2. Display storage location for all at-risk materials to enable targeted replenishment action
3. Support configurable risk thresholds (reorder point breach and safety stock percentage drop)
4. Allow natural-language queries against live stock data via a conversational AI agent
5. Provide deep ATP feasibility analysis: root-cause diagnosis, order confirmation check, corrective option simulation, and approval-gated write actions against S/4HANA

---

## User Profiles & Personas

### Primary Persona: Maria – Warehouse / Inventory Manager

Maria is a 38-year-old inventory manager responsible for daily stock oversight at a manufacturing plant. She starts each morning by manually checking several MM reports in S/4HANA to see which materials are running low. She is comfortable with SAP transactions but finds it time-consuming to cross-reference stock levels, reorder points, and safety stock values across multiple screens. Her success is measured by zero stockout events and accurate inventory records. She needs a fast overview that tells her what is fine and what needs attention — without digging into individual material records.

### Secondary Persona: Lars – Supply Chain Planner

Lars is a 44-year-old supply chain planner who sets safety stock and reorder point parameters for materials. He monitors stock trends and coordinates with procurement to trigger replenishment. His pain point is a lack of early visibility into materials trending toward risk before they formally breach thresholds. He also needs to quickly check whether planned orders can be converted to production orders to cover shortfalls.

### Persona: Sophie – Sales Operations Analyst

Sophie is a 31-year-old sales ops analyst who handles order confirmations and escalations. She needs to quickly check ATP feasibility for customer delivery requests — "Can we confirm 300 EA of FG-001 for July 5?" — without calling a planner or logging into SAP GUI.

### Persona: Carlos – Procurement Manager

Carlos is a 47-year-old procurement manager responsible for supplier relationships and PO management. He needs to flag urgent purchase orders for expediting when stock shortfalls are detected, and confirm replenishment actions are being taken.

### Other User Types

- **Plant Manager**: Needs a high-level status view to confirm operations are not at risk; reads the dashboard but does not act directly.
- **Customer Service Representative**: Needs to quickly verify stock availability to answer customer delivery queries.

---

## User Goals & Tasks

### For Maria (Inventory Manager):

**Goals:**
- Know immediately which materials are at risk of running out, by storage location
- Confirm which materials have healthy stock levels without manually checking each one
- Ask natural-language questions: "Which plant has the most critical shortage right now?"

**Key Tasks:**
- Open the dashboard each morning to review the two stock status panels
- Filter the at-risk list by plant or storage location
- Use the chatbox to ask follow-up questions about at-risk materials
- Adjust the safety stock threshold percentage

### For Lars (Supply Chain Planner):

**Goals:**
- Detect materials trending toward risk before a formal threshold breach
- Check ATP feasibility and simulate corrective options
- Execute approved corrective actions (convert planned orders, adjust PIR, create STO)

**Key Tasks:**
- Review the "nearly out of stock" list to identify patterns
- Ask the ATP agent: "What are my options if FG-001 is short by 150 EA on Jul 3?"
- Confirm and execute a planned order conversion after reviewing the proposal

### For Sophie (Sales Operations):

**Goals:**
- Confirm order feasibility in real time for customer delivery requests

**Key Tasks:**
- Ask the ATP agent: "Can we confirm 300 EA of FG-001 for July 5?"
- Read the ATP confirmation result and communicate it to the customer

### For Carlos (Procurement Manager):

**Goals:**
- Expedite POs when stock shortfalls require accelerated delivery

**Key Tasks:**
- Ask the ATP agent to flag a purchase order for expediting
- Review and approve the expedite action via the approval gate

---

## Product Principles

1. **Clarity over completeness**: Show only what is needed to act — two clearly labelled lists, not a data dump.
2. **Real-time accuracy**: Data must reflect the current S/4HANA stock position; no stale caches that mislead users.
3. **Configurable thresholds**: Threshold values are adjustable without code changes.
4. **Conversational access**: Any target user role can query stock data and ATP results in natural language.
5. **Approval-gated writes**: No corrective action is executed against S/4HANA without explicit user confirmation.
6. **Role-aware tool access**: The ATP agent enforces role-based tool policies — not all roles can trigger all actions.

---

## Business Context

**Current State:**  
Users rely on standard SAP MM reports (MB52, MB53, MD04) run on demand. These reports are not combined, require SAP GUI access, and do not provide a visual at-a-glance classification of stock health or any AI-assisted analysis.

**Strategic Alignment:**  
Supports the Plan to Fulfill end-to-end process by improving inventory visibility and enabling proactive replenishment decisions — a key capability under "Manage supply chain data and operations" (BPS-342).

**Success Criteria:**

- All target user roles can access the dashboard via a BTP-hosted URL without SAP GUI access
- Materials are correctly classified as sufficient or at-risk based on configured thresholds
- Storage location is visible for all at-risk materials
- Users can query stock data in natural language and receive accurate, sourced answers
- ATP feasibility checks complete in under 10 seconds
- Approved corrective actions are successfully submitted to S/4HANA

---

## Goals and Non-Goals

### Goals (In Scope)

- Display a list of materials with sufficient stock (stock above reorder point and safety stock threshold)
- Display a list of materials nearly out of stock, with storage location, plant, and current stock quantity
- Classify materials based on two configurable rules: (1) stock quantity below reorder point, (2) stock percentage below a user-defined percentage of safety stock
- Allow threshold configuration (safety stock percentage) from the UI
- Read stock data live from SAP S/4HANA Cloud Public Edition via the Material Stock Read OData API
- Support natural-language stock queries via the NLI Stock Advisor agent (6 tools)
- Support deep ATP analysis via the Inventory ATP Agent (10 tools): root-cause diagnosis, ATP check, option simulation, approval-gated execution (STO, planned order conversion, PIR adjustment, PO expediting)
- Enforce role-based tool access policy in the ATP agent (PLANNER / SALES_OPS / CUSTOMER_SERVICE / PROCUREMENT_MANAGER)
- Provide proactive safety stock breach alerts via watchlist monitoring

### Non-Goals (Out of Scope)

- Push notifications or email alerts (beyond in-UI alerts)
- Historical trend analysis or time-series stock charts
- Integration with SAP IBP or SAP Analytics Cloud
- Support for batch-managed or serial-number-managed stock classifications
- MCP translation.json generation (platform endpoint unavailable; tools wired directly)

---

## Requirements

### Must-Have Requirements

**R1: Sufficient Stock List**

- **Problem to Solve**: Users have no consolidated view of materials with healthy stock.
- **User Story**: As an inventory manager, I need a list of all materials with stock above both the reorder point and the safety stock threshold so that I can confirm which materials require no action.
- **Acceptance Criteria**:
  - Given stock data is loaded from S/4HANA, when the dashboard opens, then all materials with unrestricted stock above the reorder point AND above the configured safety stock percentage are displayed in the "Sufficient Stock" panel.
  - The list shows: Material Number, Material Description, Plant, Storage Location, Current Stock Quantity, Unit of Measure.
- **Maps to Objective**: Objective 1
- **Priority Rank**: 1

**R2: Nearly Out of Stock List with Storage Location**

- **Problem to Solve**: At-risk materials are not surfaced in a single view.
- **User Story**: As a supply chain planner, I need a list of materials below the reorder point or below the safety stock threshold, along with storage location, so that I can act immediately.
- **Acceptance Criteria**:
  - All materials meeting either at-risk condition are shown in the "Nearly Out of Stock" panel with a visual risk indicator.
  - The list shows: Material Number, Description, Plant, Storage Location, Stock Quantity, Reorder Point, Safety Stock, Risk Reason, Unit of Measure.
  - Materials breaching both conditions are shown once with both risk reasons flagged.
- **Maps to Objective**: Objectives 1 and 2
- **Priority Rank**: 2

**R3: Configurable Safety Stock Percentage Threshold**

- **User Story**: As an inventory manager, I need to configure the safety stock percentage threshold from the UI so that the classification reflects current policy without developer involvement.
- **Acceptance Criteria**:
  - When a user changes the safety stock percentage threshold and applies it, both panels update immediately.
  - The threshold value is persisted and retained on next page load.
- **Maps to Objective**: Objective 3
- **Priority Rank**: 3

**R4: Live Data from SAP S/4HANA Cloud Public Edition**

- **User Story**: As an inventory manager, I need the dashboard to reflect the current stock position from S/4HANA so that I am not acting on outdated information.
- **Acceptance Criteria**:
  - Stock data is fetched live from `API_MATERIAL_STOCK_SRV` on dashboard load.
  - A manual refresh button triggers a new data fetch on demand.
- **Maps to Objective**: Objective 1
- **Priority Rank**: 4

**R5: Natural-Language Stock Queries (NLI Stock Advisor Agent)**

- **Problem to Solve**: Non-SAP-expert users cannot efficiently query stock status without navigating transactions.
- **User Story**: As any target user role, I need to ask stock-related questions in natural language and receive accurate, data-sourced answers.
- **Acceptance Criteria**:
  - The agent answers questions using live stock data from the CAP `/stock/MaterialStockView` endpoint.
  - Supported tools: `get_material_stock`, `get_atrisk_materials`, `get_sufficient_materials`, `get_stock_summary`, `get_critical_materials_by_plant`, `send_email`.
  - Agent response includes source data and is returned within 15 seconds.
  - The agent is accessible via `/.well-known/agent.json` (HTTP 200).
- **Maps to Objective**: Objective 4
- **Priority Rank**: 5

**R6: ATP Feasibility Analysis (Inventory ATP Agent)**

- **Problem to Solve**: Users cannot check order feasibility, diagnose stock drops, simulate options, or execute corrections without expert SAP knowledge.
- **User Story**: As a supply chain planner, I need an AI agent that can diagnose why stock dropped, check if an order can be confirmed, simulate corrective options, and execute approved actions against S/4HANA.
- **Acceptance Criteria**:
  - Agent supports 5 sub-intents: Explain_Stock_Drop, Check_Order_Feasibility, Simulate_Options, Execute_With_Approval, Protect_Service_Level.
  - 10 tools implemented: `get_material_stock`, `get_demand_elements`, `run_atp_check`, `get_planned_orders`, `propose_corrective_actions`, `create_stock_transport_order`, `convert_planned_order`, `adjust_pir`, `flag_po_expedite`, `watchlist_monitor`.
  - Write tools (`create_stock_transport_order`, `convert_planned_order`, `adjust_pir`, `flag_po_expedite`) require explicit user confirmation via approval card before execution.
  - Role-based tool policy enforced: PLANNER (all tools), SALES_OPS (read + ATP), CUSTOMER_SERVICE (read + ATP), PROCUREMENT_MANAGER (PO tools + read).
  - Agent is accessible via `/.well-known/agent.json` (HTTP 200).
  - 85%+ test coverage.
- **Maps to Objective**: Objective 5
- **Priority Rank**: 6

**R7: Proactive Safety Stock Watchlist**

- **User Story**: As a planner, I need to monitor a watchlist of materials and receive alerts when any fall below their safety stock threshold.
- **Acceptance Criteria**:
  - `watchlist_monitor` tool accepts a list of `{material, plant, threshold}` items.
  - Returns alert objects for any item breaching the threshold, with `alert_type`, `breach_severity`, `current_stock`, and `threshold`.
- **Maps to Objective**: Objective 5
- **Priority Rank**: 7

**R8: Business Milestone Logging**

- **User Story**: As an operations manager, I need each agent interaction to log structured milestone events so that I can track AI decision quality and audit corrective actions.
- **Acceptance Criteria**:
  - M1 (`stock_perception_complete`) logged in `get_material_stock`, `get_demand_elements`.
  - M2 (`root_cause_identified`) logged in `agent._run_agent()`.
  - M3 (`atp_check_complete`) logged in `run_atp_check`.
  - M4 (`options_simulated`) logged in `propose_corrective_actions`.
  - M5 (`execution_complete`) logged in all write tools.
- **Maps to Objective**: Objectives 4 and 5
- **Priority Rank**: 8

### High-Want Requirements

**R9: Filter by Plant and Storage Location**

- **User Story**: As a warehouse manager, I need to filter both stock lists by plant and storage location so that I can focus on my area of responsibility.
- **Priority Rank**: 1

**R10: Export at-risk list to CSV**

- **User Story**: As a procurement officer, I need to export the nearly-out-of-stock list to CSV so that I can share it with my team.
- **Priority Rank**: 2

---

## Non-Functional Requirements

### Performance

- **Dashboard**: Renders both panels within 5 seconds under normal load (up to 500 material records).
- **NLI Agent**: Responds within 15 seconds for stock queries.
- **ATP Agent**: ATP feasibility check completes within 10 seconds.
- **Throughput**: Supports up to 50 concurrent users across all three components.

### Reliability

- **Availability**: Inherits BTP Cloud Foundry SLA (99.9% uptime target).
- **Fallback**: If the S/4HANA API call fails, an error banner is displayed; last successfully loaded data is shown with a timestamp.

### Explainability

- **Traceability**: Each at-risk material shows the specific rule(s) that triggered its classification.
- **Decision Logging**: Classification logic, threshold values, and all milestone log entries are persisted server-side for auditability.
- **Approval transparency**: Write actions always present a human-readable action card before execution.

### Test Coverage

- All Python assets maintain ≥70% test coverage; `inventory-atp-agent` currently at 85%.
- CAP backend Jest tests: 6/6 passing.

---

## Solution Architecture

**Architecture Overview:**  
A three-component BTP Extension hosted on SAP BTP Cloud Foundry (us10), consisting of:

1. **`material-stock-dashboard-cap`** — CAP Node.js backend + React frontend (SAP UI5 Web Components). Serves the stock dashboard UI and exposes `/stock/MaterialStockView` (OData v4) and `/stock/chat` (AI chatbox).
2. **`nli-stockadv-agent`** — Python LangGraph agent. Handles natural-language stock queries using 6 tools that read live data from the CAP service.
3. **`inventory-atp-agent`** — Python LangGraph agent. Handles deep ATP analysis with 10 tools covering read, simulation, and approval-gated write operations against S/4HANA OData APIs.

All three components are deployed to Cloud Foundry (us10) and bound to `proj-vector-destination-service`. CAP is additionally bound to `material-stock-dashboard-xsuaa`.

**S/4HANA APIs consumed:**

| API | ORD ID | Usage |
|---|---|---|
| Material Stock Read | `sap.s4:apiResource:API_MATERIAL_STOCK_SRV:v1` | Stock levels (all 3 components) |
| Material Planning / MRP | `sap.s4:apiResource:API_MRP_MATERIALS_SRV_01:v1` | Demand elements (ATP agent) |
| Advanced ATP Check | `sap.s4:apiResource:CE_APIAVAILTOPROMISECHECK_0001:v1` | Feasibility checks (ATP agent) |
| Planned Orders | `sap.s4:apiResource:API_PLANNED_ORDERS:v1` | Planned order management (ATP agent) |
| Planned Indep. Requirements | `sap.s4:apiResource:API_PLND_INDEP_RQMT_SRV:v1` | PIR management (ATP agent) |
| Stock Transport Order | `sap.s4:apiResource:CE_STOCKTRANSPORTORDER_0001:v1` | Inter-plant transfers (ATP agent) |

**Deployment:**

- **Region**: SAP BTP CF us10
- **CF Org**: `GDH-PRJ-Vector-Hackathon_gdh-prj-vector-hackathon-apac-dev1-5ms3qdnd`
- **CF Space**: `Dev`
- **Live routes**:
  - `https://material-stock-dashboard-cap.cfapps.us10.hana.ondemand.com`
  - `https://nli-stockadv-agent.cfapps.us10.hana.ondemand.com`
  - `https://inventory-atp-agent.cfapps.us10.hana.ondemand.com`

### Automation & Agent Behaviour

**NLI Stock Advisor Agent (nli-stockadv-agent):**

- Automation Level: Read-only AI agent
- Actions without approval: Querying stock data, summarising results, sending email (optional tool)
- Knowledge sources: CAP `/stock/MaterialStockView` (live S/4HANA stock data)
- No write operations against S/4HANA

**Inventory ATP Agent (inventory-atp-agent):**

- Automation Level: Supervised (read actions automatic; write actions require human confirmation)
- Actions without approval: `get_material_stock`, `get_demand_elements`, `run_atp_check`, `get_planned_orders`, `propose_corrective_actions`, `watchlist_monitor`
- Actions requiring approval: `create_stock_transport_order`, `convert_planned_order`, `adjust_pir`, `flag_po_expedite`
- Role-based access: PLANNER (all), SALES_OPS (read + ATP), CUSTOMER_SERVICE (read + ATP), PROCUREMENT_MANAGER (PO tools + read)
- Knowledge sources: 6 S/4HANA OData APIs via BTP Destination Service

---

## Milestones

### M1: Signal Perception Complete

- **Description**: Stock and demand data successfully retrieved from S/4HANA.
- **Achieved when**: `get_material_stock` or `get_demand_elements` returns a valid non-empty response.
- **Log on achievement**: `M1.achieved: stock_perception_complete — {count} records loaded`
- **Log on miss**: `M1.missed: stock_perception_failed — API call returned error or empty dataset`

### M2: Root-Cause Identified

- **Description**: Agent has synthesised a root-cause narrative from stock and demand data.
- **Achieved when**: `agent._run_agent()` produces a structured root-cause response.
- **Log on achievement**: `M2.achieved: root_cause_identified`
- **Log on miss**: `M2.missed: root_cause_analysis_failed`

### M3: ATP Feasibility Check Complete

- **Description**: An ATP check has been run and a feasibility result returned.
- **Achieved when**: `run_atp_check` returns `confirmed_quantity`, `atp_date`, and `is_fully_confirmed`.
- **Log on achievement**: `M3.achieved: atp_check_complete — confirmed={qty}, date={date}`
- **Log on miss**: `M3.missed: atp_check_failed`

### M4: Corrective Options Simulated

- **Description**: Agent has produced a ranked list of corrective actions for a stock shortfall.
- **Achieved when**: `propose_corrective_actions` returns at least one ranked option.
- **Log on achievement**: `M4.achieved: options_simulated — {count} options generated`
- **Log on miss**: `M4.missed: options_simulation_failed`

### M5: Approved Execution Complete

- **Description**: A write action has been confirmed by the user and successfully submitted to S/4HANA.
- **Achieved when**: A write tool returns success after user confirmation.
- **Log on achievement**: `M5.achieved: execution_complete — action={tool}, document={id}`
- **Log on miss**: `M5.missed: execution_failed — action={tool}, error={msg}`

### M6: Dashboard Rendered for User

- **Description**: Both stock panels are visible and populated in the browser.
- **Achieved when**: The React frontend renders both list panels without error.
- **Log on achievement**: `M6.achieved: dashboard rendered — {sufficient_count} sufficient, {atrisk_count} at-risk`
- **Log on miss**: `M6.missed: dashboard rendering failed`

---

## Risks, Assumptions, and Dependencies

### Risks

- **API connectivity**: If the BTP destination to S/4HANA is misconfigured or credentials expire, agents cannot load data. Mitigation: validate destination configuration during deployment.
- **Missing master data**: If reorder point or safety stock values are not maintained in the S/4HANA material master, materials may be misclassified. Mitigation: document assumption; flag unmaintained records in UI.
- **MCP translation.json unavailable**: `generate_mcp_translation` platform endpoint returns HTTP 404 in this environment. Mitigation: tools are wired directly via `mcp_tools.py`; EDMX files are staged for future MCP server registration.
- **LLM model availability**: `gpt-4o` is used for both agents; `sap/anthropic--claude-4.5-sonnet` was not available in the AI Core resource group at time of deployment.

### Assumptions (Validated)

- All 6 S/4HANA OData APIs are accessible and authorised for the BTP technical user.
- Reorder point and safety stock fields are populated in the S/4HANA material master for the relevant materials and plants.
- All four target user roles have access to the BTP-hosted URLs.
- CF apps are deployed to us10 region; Kyma/Joule Runtime deployment is explicitly out of scope.

### Dependencies

- SAP BTP Cloud Foundry subaccount (us10) with Destination Service (`proj-vector-destination-service`) and XSUAA (`material-stock-dashboard-xsuaa`) configured
- SAP S/4HANA Cloud Public Edition tenant with all 6 OData APIs enabled and authorised
- SAP Generative AI Hub with `gpt-4o` model accessible in the AI Core resource group
- SAP UI5 Web Components and CAP Node.js runtime on BTP
- Python 3.11 buildpack on CF for agent apps

---

## References

- [SAP Material Stock Read API – Business Accelerator Hub](https://api.sap.com/api/API_MATERIAL_STOCK_SRV/overview)
- [SAP Advanced ATP API – Business Accelerator Hub](https://api.sap.com/api/CE_APIAVAILTOPROMISECHECK_0001/overview)
- [SAP Planned Orders API – Business Accelerator Hub](https://api.sap.com/api/API_PLANNED_ORDERS/overview)
- [SAP BTP Destination Service Documentation](https://help.sap.com/docs/connectivity/sap-btp-connectivity-cf/destinations)
- [SAP CAP Node.js Documentation](https://cap.cloud.sap/docs/)
- [SAP UI5 Web Components](https://sap.github.io/ui5-webcomponents/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Architecture Documentation](../docs/architecture.md)
- [Deploy Runbook](../docs/deploy-runbook.md)
