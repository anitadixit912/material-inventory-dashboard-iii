# API Discovery Results — Inventory ATP Agentic Copilot

## Asset: inventory-atp-agent

| API Name | ORD ID | Type | Spec File | Purpose |
|---|---|---|---|---|
| Advanced ATP Check (CE) | `sap.s4:apiResource:CE_APIAVAILTOPROMISECHECK_0001:v1` | OData v4 | `specification/inventory-atp-agent/api-specs/advanced-atp-check.edmx` | ATP feasibility simulation — Actions: `ChkSlsAvailyWthoutResvn`, `CheckAvailabilityWithoutResvn` |
| Material Stock - Read | `sap.s4:apiResource:API_MATERIAL_STOCK_SRV:v1` | OData v2 | `specification/inventory-atp-agent/api-specs/material-stock-read.edmx` | Real-time stock by category — EntitySets: `A_MaterialStock`, `A_MatlStkInAcctMod` |
| Material Planning Data - Read | `sap.s4:apiResource:API_MRP_MATERIALS_SRV_01:v1` | OData v2 | `specification/inventory-atp-agent/api-specs/material-planning-data-mrp.edmx` | Demand elements, safety stock, MRP parameters — EntitySets: `A_MRPMaterial`, `SupplyDemandItems`, `MaterialCoverages` |
| Planned Order | `sap.s4:apiResource:API_PLANNED_ORDERS:v1` | OData v2 | `specification/inventory-atp-agent/api-specs/planned-orders.edmx` | Planned order read and conversion — EntitySets: `A_PlannedOrder`, FunctionImports: `PlannedOrderSchedule` |
| Planned Independent Requirements | `sap.s4:apiResource:API_PLND_INDEP_RQMT_SRV:v1` | OData v2 | `specification/inventory-atp-agent/api-specs/planned-independent-requirements.edmx` | Demand plan adjustment — EntitySets: `PlannedIndepRqmt`, `PlannedIndepRqmtItem` |
| Stock Transport Order (CE) | `sap.s4:apiResource:CE_STOCKTRANSPORTORDER_0001:v1` | OData v4 | *(spec download expired — re-fetch required)* | Inter-plant STO creation (write) |
