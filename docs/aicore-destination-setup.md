# Configure AI Core Destination for the Stock Advisor Agent

The Stock Advisor Agent resolves its LLM credentials at runtime by reading a BTP
destination named **`aicore`**. Without it the agent starts normally (health probe passes)
but returns an error on every chat message.

---

## 1. Obtain the AI Core Service Key

You need an **SAP AI Core** service instance with a service key (or a binding).

### Option A — you already have a service key (JSON)

Skip to Step 2. The service key looks like this:

```json
{
  "clientid": "sb-...",
  "clientsecret": "...",
  "url": "https://<subaccount>.authentication.<region>.hana.ondemand.com",
  "serviceurls": {
    "AI_API_URL": "https://api.ai.<region>.hana.ondemand.com"
  },
  "appname": "..."
}
```

### Option B — create a service key in BTP Cockpit

1. Go to **BTP Cockpit → your subaccount → Services → Instances**.
2. Find your **SAP AI Core** instance (or create one with plan `extended`).
3. Click **⋮ → Create Service Key**, give it a name (e.g. `aicore-key`).
4. Click **View** and copy the JSON.

---

## 2. Create the `aicore` Destination

Go to **BTP Cockpit → your subaccount → Connectivity → Destinations** → **New Destination**.

### Main Fields

| Field | Value |
|---|---|
| **Name** | `aicore` ← must match exactly |
| **Type** | `HTTP` |
| **URL** | `AI_API_URL` from the service key, e.g. `https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com` |
| **Proxy Type** | `Internet` |
| **Authentication** | `OAuth2ClientCredentials` |
| **Client ID** | `clientid` from the service key |
| **Client Secret** | `clientsecret` from the service key |
| **Token Service URL** | `url` from the service key + `/oauth/token`, e.g. `https://<subaccount>.authentication.us10.hana.ondemand.com/oauth/token` |

### Additional Properties (click **New Property** for each)

| Property | Value | Notes |
|---|---|---|
| `URL.headers.AI-Resource-Group` | `default` | Change if you use a non-default resource group |
| `HTML5.DynamicDestination` | `true` | Required for BTP connectivity |
| `WebIDEEnabled` | `true` | Optional — useful for tooling |

### Example (filled in)

| Field | Example Value |
|---|---|
| Name | `aicore` |
| URL | `https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com` |
| Authentication | `OAuth2ClientCredentials` |
| Client ID | `sb-a1b2c3d4-...@brokertenants` |
| Client Secret | `AbCdEfGhIjKl...` |
| Token Service URL | `https://mysubaccount.authentication.us10.hana.ondemand.com/oauth/token` |
| `URL.headers.AI-Resource-Group` | `default` |

Click **Save**, then **Check Connection** — expect HTTP 200.

---

## 3. Verify the AI Model is Deployed

The agent uses model **`sap/anthropic--claude-4.5-sonnet`** by default
(overridable via the `AGENT_LLM_MODEL` env var).

Confirm it is deployed in your AI Core resource group:

1. Go to **SAP AI Launchpad** (or use the AI Core API).
2. Navigate to **ML Operations → Deployments**.
3. Confirm a deployment for `anthropic--claude-4.5-sonnet` (or your chosen model) is in **Running** state.
4. Verify it belongs to resource group `default` (or the one set in `URL.headers.AI-Resource-Group`).

If not deployed, create a deployment via AI Launchpad:
- **Scenario:** `foundation-models`
- **Executable:** `claude-4.5-sonnet` (or your model)
- **Resource Group:** `default`

---

## 4. Verify the Destination Service Binding

The agent reads the destination via the **destination service** binding injected at runtime.
Confirm `proj-vector-destination-service` is bound to the `nli-stockadv-agent` asset.

In the Joule Studio solution (`solution.yaml`), the binding is declared in:
```
assets/nli-stockadv-agent/asset.yaml
```

Check that it includes:
```yaml
services:
  - name: proj-vector-destination-service
```

No redeploy is needed after adding a destination — the agent fetches credentials at
request time. However, if you change the binding itself, redeploy is required.

---

## 5. Test the Destination (no redeploy needed)

After saving the destination, send a test message to the agent:

```
curl -s https://801ab0c7-a7f0093b.joule-stg-us10.c.run.ai.cloud.sap/.well-known/agent.json
```

Expected: HTTP 200 with agent metadata JSON.

Then try a chat message via the Joule Studio UI or A2A client:
> *"Which materials should I reorder today?"*

If the destination is correctly configured, the agent returns stock-based recommendations.
If not, it returns: `"I encountered an error while processing your request."`

Check agent logs in BTP cockpit for:
```
aicore destination 'aicore' resolved (base=..., group=default)
LLM initialised from AI Core destination (model=sap/anthropic--claude-4.5-sonnet)
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Agent returns error on every message | `aicore` destination missing or misconfigured | Re-check Step 2 fields |
| `Destination service returned 404 for 'aicore'` in logs | Destination name typo | Name must be exactly `aicore` (lowercase) |
| `No 'destination' service binding found in VCAP_SERVICES` | Destination service not bound | Check `asset.yaml` service binding |
| `tokenServiceURL missing` in logs | Token Service URL not set in destination | Add `Token Service URL` field in destination |
| `401 Unauthorized` from AI Core | Wrong client ID / secret | Re-copy from service key |
| Model not found / `404` from AI Core | Model not deployed in resource group | Deploy model in AI Launchpad (Step 3) |
| Wrong resource group | `URL.headers.AI-Resource-Group` mismatch | Update additional property to match your group |

---

## Summary Checklist

- [ ] AI Core service instance exists with plan `extended`
- [ ] Service key obtained (clientid, clientsecret, url, AI_API_URL)
- [ ] BTP destination `aicore` created with correct URL, OAuth2 credentials, Token Service URL
- [ ] Additional property `URL.headers.AI-Resource-Group` = `default` (or your group)
- [ ] Model `anthropic--claude-4.5-sonnet` deployed and running in AI Core
- [ ] `proj-vector-destination-service` bound to `nli-stockadv-agent` asset
- [ ] Connection check in BTP Cockpit returns HTTP 200
