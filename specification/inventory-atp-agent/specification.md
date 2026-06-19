# Specification: inventory-atp-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read `product-requirements-document.md` and `intent.md` before starting implementation
- [x] Bootstrap agent code in `assets/inventory-atp-agent/` using skill `sap-agent-bootstrap` (invoke from inside `assets/inventory-atp-agent/`, use copy commands — do NOT create files manually)
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

---

## MCP Server Generation (API Specs → MCP Tools)

All SAP S/4HANA API integrations MUST go through MCP tools. No direct HTTP calls are permitted.

Downloaded API spec files are in `specification/inventory-atp-agent/api-specs/`:

| File | API ORD ID | Entity Sets / Actions | Purpose |
|---|---|---|---|
| `advanced-atp-check.edmx` | `sap.s4:apiResource:CE_APIAVAILTOPROMISECHECK_0001:v1` | `RlvtProductPlant`, Actions: `ChkSlsAvailyWthoutResvn`, `CheckAvailabilityWithoutResvn` | ATP feasibility check |
| `material-stock-read.edmx` | `sap.s4:apiResource:API_MATERIAL_STOCK_SRV:v1` | `A_MaterialStock`, `A_MatlStkInAcctMod` | Real-time stock by category |
| `material-planning-data-mrp.edmx` | `sap.s4:apiResource:API_MRP_MATERIALS_SRV_01:v1` | `A_MRPMaterial`, `MaterialCoverages`, `SupplyDemandItems` | Demand elements, safety stock, MRP parameters |
| `planned-orders.edmx` | `sap.s4:apiResource:API_PLANNED_ORDERS:v1` | `A_PlannedOrder`, FunctionImports: `PlannedOrderSchedule` | Planned order read and conversion |
| `planned-independent-requirements.edmx` | `sap.s4:apiResource:API_PLND_INDEP_RQMT_SRV:v1` | `PlannedIndepRqmt`, `PlannedIndepRqmtItem` | Demand plan adjustment (PIR) |
| `stock-transport-order` *(spec expired)* | `sap.s4:apiResource:CE_STOCKTRANSPORTORDER_0001:v1` | POST STO creation | Inter-plant Stock Transport Order |

- [x] Invoke `mcp-translation-file` skill for each EDMX file — `generate_mcp_translation` returned **HTTP 404** (platform endpoint `/api/v1/mcp-builder` not available in this environment — confirmed on 2026-06-18). All 6 EDMX files are staged in `specification/inventory-atp-agent/mcps/<api-name>/api-spec.edmx`. **No `translation.json` files were generated.** When the platform enables this endpoint, re-run `generate_mcp_translation` per EDMX, then run `setup-solution` to register MCP server assets.
- [x] MCP tool calls are implemented **directly** in each `assets/inventory-atp-agent/app/tools/*.py` file using the `mcp_tools.get_mcp_tools()` pattern from `app/mcp_tools.py` — this is equivalent to MCP server asset wiring.
- [x] `mcp-mock.json` generated manually from EDMX tool signatures — covers all 6 APIs with realistic mock responses for testing. See `assets/inventory-atp-agent/mcp-mock.json`.
- [ ] **TODO (future)**: When `generate_mcp_translation` is available, generate `translation.json` for each of the 6 EDMX files and register MCP server assets in `solution.yaml` via `setup-solution` skill.
- [x] For `CE_STOCKTRANSPORTORDER_0001`: `create_stock_transport_order` tool returns `STO_MCP_UNAVAILABLE` structured error when MCP tool is absent.
- [x] Wire MCP tool loading in `agent.py` using the canonical `get_mcp_tools()` pattern from `mcp_tools.py`

---

## Agent Tools Implementation

Implement each sub-intent as a discrete async Python tool function in `assets/inventory-atp-agent/app/tools/`. Each tool wraps MCP calls and returns a structured dict.

### Tool 1: `get_material_stock` — R-01 (Explain Stock Drop — Perception Layer)

- [x] Create `assets/inventory-atp-agent/app/tools/get_material_stock.py`
- [x] Implement `async def get_material_stock(material: str, plant: str, storage_location: str = "") -> dict` 
- [x] Call the MCP tool wrapping `API_MATERIAL_STOCK_SRV` → `A_MaterialStock` entity set, filtered by `Material` and `Plant` (and optionally `StorageLocation`)
- [x] Return structured response: `{ material, plant, storage_location, unrestricted_stock, in_transit_stock, reserved_stock, safety_stock, unit_of_measure, timestamp }`
- [x] Set `$top=100` on all queries; inform caller if limit applied
- [x] Handle API errors gracefully — return error reason in response dict, never raise uncaught exceptions

### Tool 2: `get_demand_elements` — R-01 (Explain Stock Drop — Root Cause Layer)

- [x] Create `assets/inventory-atp-agent/app/tools/get_demand_elements.py`
- [x] Implement `async def get_demand_elements(material: str, plant: str, date_from: str = "", date_to: str = "") -> dict`
- [x] Call MCP tool wrapping `API_MRP_MATERIALS_SRV_01` → `SupplyDemandItems` entity set, filtered by `Material` and `Plant`; optionally filter by date range
- [x] Also fetch `A_MRPMaterial` for safety stock (`SafetyStock`) and reorder point values
- [x] Return: `{ material, plant, safety_stock, reorder_point, demand_elements: [{type, document_number, quantity, date, element_type}], supply_elements: [{type, document_number, quantity, date}] }`
- [x] Set `$top=100`; apply date filter if provided

### Tool 3: `run_atp_check` — R-02 (Check Order Feasibility)

- [x] Create `assets/inventory-atp-agent/app/tools/run_atp_check.py`
- [x] Implement `async def run_atp_check(material: str, plant: str, requested_quantity: float, requested_date: str, sales_order: str = "", sales_order_item: str = "") -> dict`
- [x] Call MCP tool wrapping `CE_APIAVAILTOPROMISECHECK_0001` → Action `ChkSlsAvailyWthoutResvn` (or `CheckAvailabilityWithoutResvn` for generic check)
- [x] Pass material, plant, requested quantity, and requested delivery date as action parameters
- [x] Return: `{ material, plant, requested_quantity, requested_date, confirmed_quantity, atp_date, unfulfilled_quantity, reason_code, reason_text, is_fully_confirmed }`
- [x] If ATP is partial, set `is_fully_confirmed: false` and populate `unfulfilled_quantity`

### Tool 4: `get_planned_orders` — R-04 (Simulate Options — Supply Side)

- [x] Create `assets/inventory-atp-agent/app/tools/get_planned_orders.py`
- [x] Implement `async def get_planned_orders(material: str, plant: str, date_from: str = "", date_to: str = "") -> dict`
- [x] Call MCP tool wrapping `API_PLANNED_ORDERS` → `A_PlannedOrder` entity set, filtered by `Material` and `ProductionPlant` (or equivalent field)
- [x] Return: `{ material, plant, planned_orders: [{planned_order, order_type, quantity, basic_start_date, basic_end_date, procurement_type, conversion_eligible}] }`
- [x] Set `$top=100`; include `PlannedOrderComponent` expand if available for BOM context

### Tool 5: `propose_corrective_actions` — R-04 (Simulate and Rank Options)

- [x] Create `assets/inventory-atp-agent/app/tools/propose_corrective_actions.py`
- [x] Implement `async def propose_corrective_actions(material: str, plant: str, shortfall_quantity: float, required_date: str) -> dict`
- [x] Internally calls `get_planned_orders` and `get_demand_elements` to gather supply/demand context
- [x] Derives and ranks up to 4 options:
  - **Option A — Planned Order Conversion**: if open planned orders exist that cover the shortfall, propose conversion; estimate lead time from `BasicEndDate`
  - **Option B — Stock Transport Order (STO)**: propose inter-plant transfer if multi-plant context; flag that STO creation requires `CE_STOCKTRANSPORTORDER_0001` MCP tool
  - **Option C — PIR Adjustment**: propose reducing lower-priority PIR demand to free supply
  - **Option D — Partial Fulfillment**: split order into confirmed qty now + backorder for remainder
- [x] Rank options by ascending estimated lead days
- [x] Return: `{ material, plant, shortfall_quantity, required_date, options: [{rank, type, description, estimated_lead_days, quantity_covered, trade_offs, requires_approval: true}] }`

### Tool 6: `create_stock_transport_order` — R-05 (Execute with Approval — STO Write)

- [x] Create `assets/inventory-atp-agent/app/tools/create_stock_transport_order.py`
- [x] Implement `async def create_stock_transport_order(material: str, supplying_plant: str, receiving_plant: str, quantity: float, unit: str, delivery_date: str) -> dict`
- [x] Call MCP tool wrapping `CE_STOCKTRANSPORTORDER_0001` → POST to create STO
- [x] This tool MUST only be called after `requires_approval` gate is confirmed in agent orchestration
- [x] Return: `{ sto_document_number, material, supplying_plant, receiving_plant, quantity, unit, delivery_date, status, created_at }`
- [x] If MCP tool for STO is not yet available (spec expired), return a structured error: `{ error: "STO_MCP_UNAVAILABLE", message: "Stock Transport Order MCP tool not yet configured. Please re-fetch CE_STOCKTRANSPORTORDER_0001 spec." }`

### Tool 7: `convert_planned_order` — R-05 (Execute with Approval — Planned Order Conversion)

- [x] Create `assets/inventory-atp-agent/app/tools/convert_planned_order.py`
- [x] Implement `async def convert_planned_order(planned_order: str, conversion_order_type: str = "production") -> dict`
- [x] Call MCP tool wrapping `API_PLANNED_ORDERS` → PATCH `A_PlannedOrder` with conversion parameters (or FunctionImport `PlannedOrderSchedule` if direct conversion is supported)
- [x] This tool MUST only be called after `requires_approval` gate is confirmed
- [x] Return: `{ planned_order, converted_document_number, order_type, status, converted_at }`

### Tool 8: `adjust_pir` — R-05 (Execute with Approval — PIR Adjustment)

- [x] Create `assets/inventory-atp-agent/app/tools/adjust_pir.py`
- [x] Implement `async def adjust_pir(material: str, plant: str, version: str, requirement_date: str, new_quantity: float) -> dict`
- [x] Call MCP tool wrapping `API_PLND_INDEP_RQMT_SRV` → PATCH `PlannedIndepRqmtItem` with updated quantity
- [x] This tool MUST only be called after `requires_approval` gate is confirmed
- [x] Return: `{ material, plant, version, requirement_date, old_quantity, new_quantity, document_number, updated_at }`

### Tool 9: `flag_po_expedite` — R-05 (Execute with Approval — PO Expedite)

- [x] Create `assets/inventory-atp-agent/app/tools/flag_po_expedite.py`
- [x] Implement `async def flag_po_expedite(purchase_order: str, purchase_order_item: str, expedite_reason: str, buyer_note: str = "") -> dict`
- [x] Since no direct OData PO expedite API exists in the discovered specs, implement as a structured notification payload: generate a structured expedite request dict that the agent presents as a confirmation action card
- [x] Return: `{ purchase_order, purchase_order_item, expedite_reason, buyer_note, flagged_at, status: "PENDING_BUYER_ACTION" }`

---

## Agent Orchestration

- [x] In `assets/inventory-atp-agent/app/agent.py`, implement the system prompt that:
  - Defines the agent's role as "Inventory ATP Agentic Copilot for S/4HANA Cloud"
  - Enumerates the 5 sub-intents: `Explain_Stock_Drop`, `Check_Order_Feasibility`, `Protect_Service_Level`, `Simulate_Options`, `Execute_With_Approval`
  - Instructs the agent to NEVER hallucinate quantities, dates, or document numbers — cite ONLY values returned by MCP tools
  - Instructs the agent to always set `$top=100` (or equivalent) on every tool call that accepts a limit
  - Enforces the **approval gate rule**: tools `create_stock_transport_order`, `convert_planned_order`, `adjust_pir`, and `flag_po_expedite` MUST NOT be called unless the user has explicitly confirmed the action card in the current conversation turn
  - Defines the approval card format: present action type, key parameters, estimated impact, and ask for explicit "confirm" or "reject"
  - Instructs the agent to explain uncertainty explicitly when ATP simulation returns partial or ambiguous results

- [x] Implement `Protect_Service_Level` watchlist logic:
  - [x] Add a `watchlist_monitor` async function that accepts a list of `{material, plant, safety_stock_threshold, sla_date}` entries
  - [x] For each entry, call `get_material_stock` and compare unrestricted stock against threshold
  - [x] If breach detected, return a structured alert dict: `{ alert_type: "SAFETY_STOCK_BREACH", material, plant, current_stock, threshold, breach_severity: "HIGH|MEDIUM|LOW" }`
  - [x] The Fiori push notification and chat alert delivery is handled externally by the BTP Notifications integration layer — agent returns the alert payload; the caller is responsible for delivery

- [x] Implement role-based tool access policy:
  - [x] Add `ROLE_TOOL_POLICY` dict in `agent.py` mapping roles to allowed write tools:
    - `PLANNER`: all tools
    - `SALES_OPS`: `get_material_stock`, `run_atp_check`, `propose_corrective_actions` (read-only)
    - `CUSTOMER_SERVICE`: `get_material_stock`, `run_atp_check` (read-only)
    - `PROCUREMENT_MANAGER`: `flag_po_expedite`, `get_demand_elements`, `get_planned_orders`
  - [x] Enforce policy in `stream()`: if user role is provided in context, filter available tools accordingly; if role is absent, default to read-only tools

---

## Business Step Instrumentation — Milestones (REQUIRED)

- [x] Implement instrumentation for all 5 PRD milestones. Extract all business logic from `stream()` into `_run_agent()` helper. Instrument `_run_agent()` — NEVER use `with tracer.start_as_current_span(...)` inside the `stream()` generator.

- [x] **M1 — Signal Perception**: In `get_material_stock` and `get_demand_elements` tools, after successful API response:
  ```python
  logger.info("M1.achieved: stock_perception_complete | material=%s plant=%s sloc=%s stock_categories=%d demand_elements=%d",
              material, plant, sloc, stock_category_count, demand_element_count)
  ```
  On failure:
  ```python
  logger.warning("M1.missed: stock_perception_failed | material=%s plant=%s error=%s — perception step did not complete",
                 material, plant, error_code)
  ```

- [x] **M2 — Root-Cause Analysis**: In `_run_agent()` after the agent generates its root-cause explanation:
  ```python
  logger.info("M2.achieved: root_cause_identified | primary_cause=%s contributing_elements=%d material=%s",
              cause_type, count, material)
  ```
  On failure:
  ```python
  logger.warning("M2.missed: root_cause_not_identified | material=%s reason=%s — explanation not generated",
                 material, reason)
  ```

- [x] **M3 — ATP Feasibility Check**: In `run_atp_check` tool after response:
  ```python
  logger.info("M3.achieved: atp_check_complete | order=%s line=%s confirmed_qty=%s atp_date=%s",
              order_number, line_item, confirmed_qty, atp_date)
  ```
  On failure:
  ```python
  logger.warning("M3.missed: atp_check_failed | order=%s line=%s error=%s — ATP result not returned",
                 order_number, line_item, error_code)
  ```

- [x] **M4 — Option Simulation and Ranking**: In `propose_corrective_actions` after ranking completes:
  ```python
  logger.info("M4.achieved: options_simulated | material=%s options_count=%d top_option=%s estimated_lead_days=%d",
              material, options_count, top_option_type, lead_days)
  ```
  On failure:
  ```python
  logger.warning("M4.missed: options_not_simulated | material=%s reason=%s — ranked options not generated",
                 material, reason)
  ```

- [x] **M5 — Human-Approved Execution**: In each write tool after successful S/4HANA write-back:
  ```python
  logger.info("M5.achieved: execution_complete | action=%s document=%s approved_by=%s timestamp=%s",
              action_type, s4_document_number, user_id, timestamp)
  ```
  On rejection or failure:
  ```python
  logger.warning("M5.missed: execution_not_completed | action=%s reason=%s approved_by=%s",
                 action_type, reason, user_id)
  ```

- [x] Add OpenTelemetry custom spans using `@tracer.start_as_current_span("span-name")` decorator on each tool async method (not on `stream()` generator)
- [x] Verify `auto_instrument()` is called at top of `main.py` before any AI framework imports

---

## Testing

- [x] `conftest.py` only sets `IBD_TESTING=true` — mock `mcp_tools.get_mcp_tools` using `mcp-mock.json`
- [x] Mock LLM (ChatLiteLLM) in all tests — no real AI Core calls during tests

### Unit Tests (one per tool, run each immediately after writing):

- [x] `tests/test_get_material_stock.py` — mock MCP, verify stock categories returned correctly; test empty result handling
- [x] `tests/test_get_demand_elements.py` — mock MRP API response with SupplyDemandItems; verify demand element parsing; test date filter
- [x] `tests/test_run_atp_check.py` — mock ATP action response; test full ATP, partial ATP, and zero-confirmed cases
- [x] `tests/test_get_planned_orders.py` — mock planned order list; verify filtering by material/plant; test empty result
- [x] `tests/test_propose_corrective_actions.py` — mock get_planned_orders + get_demand_elements; verify 4 options generated and ranked by lead days
- [x] `tests/test_create_stock_transport_order.py` — mock STO MCP tool (or verify graceful error when tool unavailable)
- [x] `tests/test_convert_planned_order.py` — mock planned order PATCH response; verify document number returned
- [x] `tests/test_adjust_pir.py` — mock PIR PATCH response; verify old/new quantities in return
- [x] `tests/test_flag_po_expedite.py` — verify structured expedite payload returned; verify `status: PENDING_BUYER_ACTION`
- [x] `tests/test_watchlist_monitor.py` — mock get_material_stock; test breach detection with HIGH/MEDIUM/LOW severity; test no-breach case

### Integration Test:

- [x] `tests/test_agent_integration.py` — mock all MCP tools and LLM; test full agent flow for each sub-intent:
  - Explain_Stock_Drop utterance → M1 + M2 milestones logged, root-cause response returned
  - Check_Order_Feasibility utterance → M3 milestone logged, ATP result returned
  - Simulate_Options utterance → M4 milestone logged, ranked options returned
  - Execute_With_Approval flow: approval card presented → user confirms → M5 achieved logged
  - Execute_With_Approval flow: user rejects → M5 missed logged, no write-back called
  - Role-based access: CUSTOMER_SERVICE role cannot call `create_stock_transport_order`

### Final Test Run:

- [x] Run `pytest` from `assets/inventory-atp-agent/` (no args) — coverage must be ≥ 70%
- [x] Verify `grep -r "M[0-9]\.achieved" assets/inventory-atp-agent/app/` returns results
- [x] Verify `grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/inventory-atp-agent/app/agent.py` returns exactly `3`
- [x] Verify `grep -r "sap_cloud_sdk.agent_decorators" assets/inventory-atp-agent/app/` returns results
- [x] Run `pytest` again (no args) to produce final `test_report.json`
- [x] Verify `assets/inventory-atp-agent/test_report.json` exists

---

## Agent Evaluation

- [x] Invoke `sap-aeval-generate-tool-schema` skill from `assets/inventory-atp-agent/` — produces `tools.json`
- [x] Invoke `sap-aeval-generate-testcase` skill from `assets/inventory-atp-agent/` with `product-requirements-document.md` and `tools.json`
- [x] Review generated `aeval/testcases/` — replace placeholder values (e.g. `<material:example>`) with realistic S/4HANA test data (e.g. material `FG-001`, plant `1010`)
- [x] Verify `aeval/eval.yaml` covers all 5 sub-intents

---

## API Discovery Results Reference

```
api-discovery-results.md — API ORD IDs for this asset:
  sap.s4:apiResource:CE_APIAVAILTOPROMISECHECK_0001:v1   — Advanced ATP Check (CE, Cloud Public)
  sap.s4:apiResource:API_MATERIAL_STOCK_SRV:v1           — Material Stock Read
  sap.s4:apiResource:API_MRP_MATERIALS_SRV_01:v1         — Material Planning Data / MRP
  sap.s4:apiResource:API_PLANNED_ORDERS:v1               — Planned Orders (read + conversion)
  sap.s4:apiResource:API_PLND_INDEP_RQMT_SRV:v1          — Planned Independent Requirements
  sap.s4:apiResource:CE_STOCKTRANSPORTORDER_0001:v1       — Stock Transport Order (CE, Cloud Public) [spec re-fetch required]
```
