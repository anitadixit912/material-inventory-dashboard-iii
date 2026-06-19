# Deploy Runbook — Material Stock Dashboard

**Solution:** `material-stock-dashboard-890c0`  
**Platform:** SAP BTP — Cloud Foundry  
**BTP Subaccount:** `GDH-PRJ-Vector-Hackathon-APAC-Dev1`  
**CF API:** `https://api.cf.us10.hana.ondemand.com`  
**CF Org:** `GDH-PRJ-Vector-Hackathon_gdh-prj-vector-hackathon-apac-dev1-5ms3qdnd`  
**CF Space:** `Dev`  
**Last successful deploy:** 2026-06-18 11:27 UTC — all 3 assets running  
**Last runbook execution:** 2026-06-18 11:27 UTC ✅ complete

---

## Assets

| Asset | Type | CF Route |
|---|---|---|
| `material-stock-dashboard-cap` | CAP App | https://material-stock-dashboard-cap.cfapps.us10.hana.ondemand.com |
| `nli-stockadv-agent` | Agent | https://nli-stockadv-agent.cfapps.us10.hana.ondemand.com |
| `inventory-atp-agent` | Agent | https://inventory-atp-agent.cfapps.us10.hana.ondemand.com |

---

## Prerequisites

### 1. BTP Service Instances

| Service Instance | Used By |
|---|---|
| `proj-vector-destination-service` | All 3 assets (destination lookups) |
| `material-stock-dashboard-xsuaa` | `material-stock-dashboard-cap` (authentication) |

### 2. Destinations (BTP Cockpit → GDH-PRJ-Vector-Hackathon-APAC-Dev1 → Connectivity → Destinations)

| Destination Name | Used By | Purpose |
|---|---|---|
| `S4HANA_MATERIAL_STOCK` | `material-stock-dashboard-cap` | S/4HANA OData stock API |
| `aicore` | `nli-stockadv-agent`, `inventory-atp-agent` | SAP AI Core LLM access |

> - S/4HANA destination setup → [`docs/s4hana-destination-setup.md`](./s4hana-destination-setup.md)
> - AI Core destination setup → [`docs/aicore-destination-setup.md`](./aicore-destination-setup.md)

### 3. CF CLI Login

```bash
cf login -a https://api.cf.us10.hana.ondemand.com
cf target -o GDH-PRJ-Vector-Hackathon_gdh-prj-vector-hackathon-apac-dev1-5ms3qdnd -s Dev
```

---

## Deploy Steps

### Step 1 — Push nli-stockadv-agent

```bash
cd assets/nli-stockadv-agent
cf push
```

### Step 2 — Push inventory-atp-agent

```bash
cd assets/inventory-atp-agent
cf push
```

### Step 3 — Build and Push material-stock-dashboard-cap

```bash
cd assets/material-stock-dashboard-cap
npm run build:all
cf push
```

### Step 4 — Cleanup (if old app still present)

```bash
cf delete stock-advisor-agent -f
```

---

## Post-Deploy Verification

### 1. nli-stockadv-agent

```bash
curl -s -o /dev/null -w "%{http_code}" \
  https://nli-stockadv-agent.cfapps.us10.hana.ondemand.com/.well-known/agent.json
```
**Expected:** `200`

### 2. inventory-atp-agent

```bash
curl -s -o /dev/null -w "%{http_code}" \
  https://inventory-atp-agent.cfapps.us10.hana.ondemand.com/.well-known/agent.json
```
**Expected:** `200`

### 3. CAP Dashboard

```bash
curl -s -o /dev/null -w "%{http_code}" \
  https://material-stock-dashboard-cap.cfapps.us10.hana.ondemand.com/stock
```
**Expected:** `200`

### 4. Agent Card Validation

```bash
curl -s https://nli-stockadv-agent.cfapps.us10.hana.ondemand.com/.well-known/agent.json | jq .
curl -s https://inventory-atp-agent.cfapps.us10.hana.ondemand.com/.well-known/agent.json | jq .
```
**Expected:** Valid JSON with correct agent names.

---

## Smoke Tests

### CAP Dashboard (Jest)

```bash
cd assets/material-stock-dashboard-cap
npm test
```
**Expected:** 6/6 tests pass

### nli-stockadv-agent (pytest)

```bash
cd assets/nli-stockadv-agent
python -m pytest prebuilt_tests/ -v
```
**Expected:** 5/5 tests pass

### inventory-atp-agent (pytest)

```bash
cd assets/inventory-atp-agent
python -m pytest tests/ -v
```
**Expected:** 56/56 tests pass, coverage ≥ 85%

---

## Health Checks

| Asset | Health Endpoint | Expected |
|---|---|---|
| `nli-stockadv-agent` | `/.well-known/agent.json` | HTTP 200 |
| `inventory-atp-agent` | `/.well-known/agent.json` | HTTP 200 |
| `material-stock-dashboard-cap` | `/stock` | HTTP 200 |

---

## Rollback

1. If any asset fails → `cf logs <app-name> --recent` to check logs.
2. Code regression → revert the offending file and `cf push` that asset only.
3. Infrastructure failure → report to admin; do NOT delete service bindings.

> ⚠️ Never delete `solution.yaml`, `asset.yaml`, `manifest.yml`, or service binding configs during rollback.

---

## Known Behaviours

| Behaviour | Cause | Impact |
|---|---|---|
| CAP logs `SECURITY WARNING: Falling back to mock stock data` | `S4HANA_MATERIAL_STOCK` destination not configured | Dashboard shows 15 mock materials — functional for demo/test |
| Agent returns error on every chat message | `aicore` destination missing or misconfigured | No LLM access — configure per `aicore-destination-setup.md` |

---

## Deployment Checklist

### Pre-Deploy
- [ ] CF CLI logged in and targeted to correct Org/Space
- [ ] `proj-vector-destination-service` exists in BTP subaccount
- [ ] `material-stock-dashboard-xsuaa` exists in BTP subaccount
- [ ] `S4HANA_MATERIAL_STOCK` destination configured
- [ ] `aicore` destination configured
- [ ] `npm run build:all` run for `material-stock-dashboard-cap` before `cf push`

### Post-Deploy
- [x] `nli-stockadv-agent` `/.well-known/agent.json` → HTTP 200 ✅
- [x] `inventory-atp-agent` `/.well-known/agent.json` → HTTP 200 ✅
- [x] `material-stock-dashboard-cap` `/stock` → HTTP 200 ✅
- [x] Agent card JSON valid for both agents ✅
- [x] Jest smoke tests pass (6/6) ✅
- [x] pytest tests pass — nli-stockadv-agent (5/5), inventory-atp-agent (56/56, 85% coverage) ✅
- [x] `stock-advisor-agent` deleted from CF ✅
