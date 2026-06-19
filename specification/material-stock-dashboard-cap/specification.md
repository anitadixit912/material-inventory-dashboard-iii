# Specification: material-stock-dashboard-cap

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-cap.md](../guidelines-cap.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read the project input (`product-requirements-document.md`, `intent.md`)
- [x] Invoke the `cap-development` skill from `assets/material-stock-dashboard-cap/` to set up the CAP project structure
- [x] Install dependencies (`npm install`), validate the project starts (`cds watch`) and responds

## API Spec Reference

The Material Stock Read OData API spec (EDMX) is located at:
`specification/material-stock-dashboard-cap/api-specs/material-stock.edmx`

Key entity used for stock data: `A_MatlStkInAcctModType`
- `Material` (String) — material number
- `Plant` (String) — plant
- `StorageLocation` (String) — storage location
- `MatlWrhsStkQtyInMatlBaseUnit` (Decimal) — unrestricted stock quantity
- `MaterialBaseUnit` (String) — base unit of measure

**Note**: The Material Stock API does not expose reorder point or safety stock. These values must be mocked in the CAP backend using an in-memory configuration store until a Material Master API integration is available.

## Data Model

- [x] Define CDS entity `MaterialStockView` in `srv/stock-service.cds`:
  - `Material` : String (key)
  - `Plant` : String (key)
  - `StorageLocation` : String (key)
  - `MaterialDescription` : String
  - `StockQuantity` : Decimal
  - `BaseUnit` : String
  - `ReorderPoint` : Decimal
  - `SafetyStock` : Decimal
  - `StockStatus` : String (enum: `SUFFICIENT`, `NEARLY_OUT_OF_STOCK`)
  - `RiskReason` : String (e.g. `REORDER_POINT_BREACH`, `SAFETY_STOCK_PCT_BREACH`, `BOTH`, or null)

- [x] Define CDS entity `StockThresholdConfig`:
  - `id` : Integer (key, value = 1 — singleton config)
  - `safetyStockPct` : Decimal (default 20 — meaning stock must be >= 20% of safety stock)

- [x] Expose both entities via a CDS service `StockService` at path `/stock`

## Backend: S/4HANA Integration via Destination

- [x] Define an external service in `package.json` under `cds.requires` pointing to the S/4HANA Material Stock OData API
- [x] Import the EDMX spec into the CAP project: `srv/external/API_MATERIAL_STOCK_SRV.edmx` present
- [x] Run `cds import srv/external/API_MATERIAL_STOCK_SRV.edmx` — CDS model generated at `srv/external/API_MATERIAL_STOCK_SRV.cds`
- [x] Create mock data in `test/data/material-stock-mock.js` with 15 realistic rows covering sufficient, reorder point breach, safety stock % breach, and both conditions

## Backend: Classification Logic (Custom Handler)

- [x] Implement a custom `READ` handler for `MaterialStockView` in `srv/stock-service.js`:
  1. Fetches mock/S4 data with S4HANA destination fallback
  2. Loads `safetyStockPct` from in-memory cache (DB-seeded on startup)
  3. Classifies each record: `REORDER_POINT_BREACH`, `SAFETY_STOCK_PCT_BREACH`, `BOTH`, or `SUFFICIENT`
  4. Returns enriched `MaterialStockView` records including `RiskDescription`

- [x] Implement `updateThreshold` action — controlled write path for threshold config (in-memory + DB persist)
- [x] `ReorderPoint` and `SafetyStock` seeded from mock data; documented for future Material Master API integration

## Backend: Tests

- [x] Unit tests written in `test/stock-service.test.js` with `cds.User` auth context:
  - Test: stock above thresholds → `SUFFICIENT`
  - Test: stock below reorder point → `NEARLY_OUT_OF_STOCK` / `REORDER_POINT_BREACH`
  - Test: stock below safety stock % → `NEARLY_OUT_OF_STOCK` / `SAFETY_STOCK_PCT_BREACH`
  - Test: both conditions breached → `NEARLY_OUT_OF_STOCK` / `BOTH`
  - Test: `StockThresholdConfig` read returns default 20%

- [x] `cds compile srv/` — no errors (confirmed)
- [x] `cds watch` — service starts and `/stock/MaterialStockView` returns 15 classified records (6 sufficient, 9 at-risk)

## Frontend: Dashboard UI

The frontend is a React app using SAP UI5 Web Components deployed at `app/react-ui/`.

- [x] React frontend scaffolded in `assets/material-stock-dashboard-cap/app/react-ui/`
- [x] `@ui5/webcomponents-react` installed

### Dashboard Layout

- [x] Main `App.jsx` as the root component rendered at `/react-ui/`
- [x] Top `ShellBar` with title "Material Stock Dashboard" and Refresh button (icon="refresh")
- [x] Threshold configuration bar: Label + `Input` (type Number, pre-filled) + "Apply" button that calls `updateThreshold` action and re-fetches data
- [x] Two panels side-by-side via CSS flexbox: Sufficient Stock (left) / Nearly Out of Stock (right)
- [x] Each panel has a `Title` heading and `AnalyticalTable`

### Sufficient Stock Panel

- [x] `AnalyticalTable` columns: Material, Description, Plant, Storage Location, Stock Qty
- [x] Data filtered client-side from `allStock` where `StockStatus === 'SUFFICIENT'`
- [x] Record count in panel heading: "✔ Sufficient Stock (N)"
- [x] Green top border accent on panel

### Nearly Out of Stock Panel

- [x] `AnalyticalTable` columns: Material, Description, Plant, Storage Location, Stock Qty, Reorder Point, Safety Stock, Safety Threshold, Risk
- [x] Data filtered client-side where `StockStatus === 'NEARLY_OUT_OF_STOCK'`
- [x] Record count in panel heading: "⚠ Nearly Out of Stock (N)"
- [x] `Tag` component with `colorScheme`: `'1'` (red) for `BOTH`, `'2'` (orange) for others
- [x] Red/amber top border accent on panel
- [x] Human-readable risk labels: "Below Reorder Point", "Below Safety Stock %", "Below Reorder Point & Safety Stock %"

### Filtering

- [x] Shared `Select` for Plant — populated dynamically from distinct plants in response
- [x] Cascading `Select` for Storage Location — filtered by selected plant
- [x] Filters applied client-side to `allStock` via `useMemo`

### Loading & Error States

- [x] `BusyIndicator` wraps both panels during data load
- [x] `MessageStrip` (design="Negative") shows error with Retry button on API failure
- [x] `noDataText` prop on tables for empty state: "No materials found" / "No at-risk materials"

### Export to CSV

- [x] "Export CSV" button in Nearly Out of Stock panel toolbar (icon="download")
- [x] Client-side CSV generation from `atRiskData` array — no backend call
- [x] CSV columns: Material, Description, Plant, StorageLocation, StockQuantity, Unit, SafetyThreshold(%), RiskReason

## Frontend: Connect to CAP Backend

- [x] Vite proxy configured: `/stock` and `/odata` → `http://localhost:4004`
- [x] `MaterialStockView` fetched from `/stock/MaterialStockView` (no OData filter; client-side split)
- [x] `StockThresholdConfig` fetched from `/stock/StockThresholdConfig(1)` on app load
- [x] Refresh triggered by ShellBar Refresh button and after threshold Apply

## Security Compliance

### 🔴 High — Authentication & Authorization

- [x] `StockThresholdConfig` entity is `@readonly` — direct PATCH/DELETE blocked
- [x] `@requires: 'authenticated-user'` at service level — all endpoints protected
- [x] Tests use `srv.tx({ user: new cds.User('test-user') }, ...)` to run as authenticated user

### 🟠 Medium — Input Validation & Data Exposure

- [x] Chat `message` capped at `String(1000)` in CDS; server guard returns HTTP 400 for empty/oversized input
- [x] `AGENT_SERVICE_URL` sourced from env var; protected by platform JWT proxy
- [x] `SECURITY WARNING` log emitted whenever mock fallback activates in place of real S4HANA destination

### 🟡 Low — Schema & Data Hygiene

- [x] `RiskDescription : String(500)` declared in CDS and computed by `classify()` function

---

## Validation

- [x] `cds compile srv/` — no errors
- [x] `cds watch` — service starts; `/stock/MaterialStockView` returns 15 classified records (6 sufficient, 9 at-risk)
- [x] React frontend builds (`npm run build`) — production bundle generated in `dist/`
- [x] React dev server starts on port 5173; proxy confirms 15 records served through Vite at port 5173
- [x] Threshold change verified: at 1% → 7 at-risk / 8 sufficient; at 99% → 9 at-risk / 6 sufficient
- [x] OData Plant filter verified: Plant 1000 → 6 records, Plant 2000 → 5 records
- [x] OData StockStatus filter verified: SUFFICIENT → 6, NEARLY_OUT_OF_STOCK → 9
- [x] Input validation: empty chat → 400, oversized chat → 400, invalid threshold → 400
- [x] All 6 unit tests pass (classification logic + config read)
- [x] CSV export: client-side logic generates correct columns including safety threshold value
- [x] Row colour coding: `BOTH` → Tag colorScheme `'1'` (red/critical), others → `'2'` (orange)
