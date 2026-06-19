# Configure S/4HANA Destination for Live Stock Data

The CAP service automatically falls back to **mock data** when the `S4HANA_MATERIAL_STOCK`
destination is not configured. To connect live S/4HANA Cloud stock data, follow these steps.

---

## 1. Open BTP Cockpit

Go to: https://cockpit.btp.cloud.sap  
Navigate to: **your subaccount → Connectivity → Destinations**

---

## 2. Create the Destination

Click **"New Destination"** and fill in:

| Field | Value |
|---|---|
| **Name** | `S4HANA_MATERIAL_STOCK` ← must match exactly |
| **Type** | `HTTP` |
| **URL** | Your S/4HANA Cloud API URL, e.g. `https://<your-tenant>.s4hana.cloud.sap` |
| **Proxy Type** | `Internet` |
| **Authentication** | `BasicAuthentication` or `OAuth2ClientCredentials` |
| **User / Client ID** | Your S/4HANA API user or OAuth client ID |
| **Password / Secret** | Your S/4HANA API password or OAuth client secret |

### Additional Properties (click "New Property"):

| Property | Value |
|---|---|
| `sap-client` | `100` (or your S/4HANA client number) |
| `HTML5.DynamicDestination` | `true` |
| `WebIDEEnabled` | `true` |
| `WebIDESystem` | `S4HANA` |

---

## 3. API Used

The dashboard calls: **`API_MATERIAL_STOCK_SRV`** (OData v2)  
Entity set: `A_MatlStkInAcctModType`  
Fields: `Material`, `Plant`, `StorageLocation`, `MaterialBaseUnit`, `MatlWrhsStkQtyInMatlBaseUnit`

Make sure your S/4HANA user has authorization for this API (authorization object `M_MSEG_WMB`).

---

## 4. Bind the Destination Service to the CAP App

The Joule Studio runtime auto-injects service bindings at deploy time. Confirm that
`proj-vector-destination-service` is referenced in the CAP asset configuration:

```
assets/material-stock-dashboard-cap/asset.yaml
```

It should include:
```yaml
services:
  - name: proj-vector-destination-service
```

No manual binding in BTP Cockpit is needed — the Joule Studio runtime handles it automatically during deployment.

---

## 5. Verify (no redeploy needed)

Once the destination is created, the CAP service will automatically pick it up on the next
request — no redeploy required. The mock-data fallback log warning will disappear from the logs.

---

## Current Status

Until the destination is configured, the dashboard works with **15 mock materials** (Plant 1000, 
storage locations SL01/SL02/SL03) — fully functional for demonstration and testing.
