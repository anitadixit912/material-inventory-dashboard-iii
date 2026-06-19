# Specification: nli-stockadv-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

---

## Basic Setup

- [x] Read `product-requirements-document.md` and `intent.md` before starting implementation
- [x] Bootstrap agent code in `assets/nli-stockadv-agent/` using skill `sap-agent-bootstrap`
- [x] Install CF dependencies (`pip install -r requirements.txt`), validate agent starts and responds at `/.well-known/agent.json`
- [x] Validate `app/__init__.py` sets `__version__ = "1.5.0"`

---

## Agent Role & Purpose

The `nli-stockadv-agent` is the **Natural Language Interface (NLI) Stock Advisor** — the primary conversational entry point for all user stock queries from the React chatbox in the Material Stock Dashboard.

**Responsibilities:**
- Answer natural-language questions about material stock levels using live CAP OData data
- Identify at-risk materials and recommend replenishment actions
- Provide per-plant filtering and summary views
- Send email notifications on user request (SMTP via env vars)

**Live URL:** `https://nli-stockadv-agent.cfapps.us10.hana.ondemand.com`
**Agent card:** `https://nli-stockadv-agent.cfapps.us10.hana.ondemand.com/.well-known/agent.json`

---

## CF Runtime Configuration

- [x] `requirements.txt` — CF buildpack dependencies; includes `sap-ai-sdk-gen==6.6.0` for AI Core via BTP destination; excludes Joule/Kyma-specific packages (`litellm`, `langchain-litellm`, `sap-cloud-sdk`, `click==8.1.8`)
- [x] `requirements-test.txt` — test dependencies only: `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `pytest-cov>=4.0.0`, `pytest-json-report>=1.5.0`, `pytest-timeout>=2.4.0`, `ruff`
- [x] `Dockerfile` — **not used for CF deployment** (retained for local dev reference only); `python:3.12-slim`, installs `requirements.txt`, copies `app/`, exposes port 5000, CMD gunicorn with uvicorn worker
- [x] `Procfile` — CF start command: `gunicorn --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:${PORT} --chdir app main:application`
- [x] `runtime.txt` — pins Python version: `python-3.12.x` for CF buildpack
- [x] `.cfignore` — excludes test files, `__pycache__`, `.coverage`, `Dockerfile`, `migration-audit/`, `asset.yaml` from CF push

---

## `app/main.py` — A2A Server Entry Point

- [x] Guard `set_aicore_config()` and `auto_instrument()` under `if os.environ.get("JOULE_RUNTIME")` — these are Joule-only SDK calls; on CF the env var is absent so they are skipped; no Joule/Kyma SDK is installed
- [x] Import `uvicorn`, `A2AStarletteApplication`, `DefaultRequestHandler`, `InMemoryTaskStore` from `a2a.server.*`
- [x] Define `AgentSkill` with `id="nli-stockadv-agent"`, `tags=["stock", "inventory", "replenishment", "advisor"]`, 3 example utterances
- [x] Define `AgentCard` with `version="1.5.0"`, `capabilities=AgentCapabilities(streaming=True, push_notifications=False)`, `default_input_modes=["text", "text/plain"]`
- [x] `AGENT_PUBLIC_URL` sourced from env var; fallback to `http://{HOST}:{PORT}/`
- [x] `app = server.build()` + `application = app` (module-level ASGI object required by gunicorn)
- [x] Attach `StarletteInstrumentor` for OpenTelemetry; wrapped in try/except — skipped gracefully if unavailable
- [x] `main()` function for direct invocation in development (`argparse` for `--host` / `--port`); runs `uvicorn.run(app, ...)`

---

## `app/agent_executor.py` — A2A Request Handler

- [x] Subclass `A2AAgentExecutor` from `a2a.server.agent_execution`
- [x] `__init__`: instantiates `SampleAgent()`
- [x] `execute(context, event_queue)`:
  - Creates task via `new_task(context.message)` if no current task; enqueues it
  - Loads `STOCK_TOOLS` from `tools.py` (always available on CF)
  - MCP tools: calls `get_mcp_tools(use_cache=True)` from `mcp_tools.py`; in production returns `[]` (Agent Gateway not available on CF); in test mode (`IBD_TESTING=1`) returns mock tools from `mcp-mock.json`; appended to tools list; gracefully skips on exception
  - Streams via `self.agent.stream(query, task.context_id, tools=tools)`
  - Task state machine: `working` status updates → artifact + `complete` on finish → `input_required` on prompt
  - Raises `ServerError(InternalError())` on unhandled exception
- [x] `cancel(context, event_queue)`: raises `ServerError(UnsupportedOperationError())`

---

## `app/agent.py` — LangGraph Agent

- [x] **Decorator import**: `from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section` wrapped in try/except; falls back to `_identity_decorator` (pass-through) — Joule SDK is not installed on CF; decorators become no-ops
- [x] **Lazy LLM import**: `from langchain.agents import create_agent` and `SummarizationMiddleware` wrapped in try/except; stored as module-level `_create_agent` / `_SummarizationMiddleware`; `ImportError` raised at call-time if absent (not at import-time)
- [x] **Lazy AI Core import**: `from aicore import init_llm_from_destination` wrapped in try/except; stored as `_init_llm_from_destination`
- [x] `@agent_model` → `get_model_name()` reads `AGENT_LLM_MODEL` env var; active value on CF: `gpt-4o` (overridden — `sap/anthropic--claude-4.5-sonnet` not available in the AI Core resource group)
- [x] `@agent_config` → `get_temperature()` returns `0.0`
- [x] `@prompt_section` → `get_system_prompt()` full system prompt (see System Prompt section below)
- [x] `AgentResponse` dataclass: `status: Literal["input_required", "completed", "error"]`, `message: str`
- [x] `THREAD_TTL_SECONDS = 3600` — threads inactive for >1 hour are evicted; documented with data retention policy comment block
- [x] `SampleAgent.__init__`: sets `self._llm = None`, `self._summarization_middleware = None`, `self._checkpointer = InMemorySaver()`, `self._last_active: dict[str, float] = {}`
- [x] `SampleAgent._get_llm()`: builds and caches LLM via `init_llm_from_destination(get_model_name(), temperature=...)` on first call; attaches `SummarizationMiddleware` (trigger at 100k tokens) if available; logs model name; raises `ImportError` if `aicore` module absent
- [x] `SampleAgent._touch(thread_id)`: refreshes TTL; evicts expired threads from checkpointer and `_last_active`
- [x] `SampleAgent.stream(query, context_id, tools)`: async generator; calls `_touch`; yields `{is_task_complete: False, require_user_input: False, content: "Processing..."}` immediately; calls `_create_agent(llm, tools, system_prompt, checkpointer, middleware)`; invokes graph; yields complete/input_required/error result; calls `_touch` after completion; catches all exceptions → yields error response
- [x] `SampleAgent.invoke(query, context_id, tools)`: collects stream generator; returns `AgentResponse(completed|input_required|error, message)`

---

## `app/tools.py` — Stock Data Tools

### Tool Infrastructure

- [x] `CAP_BASE_URL` sourced from `CAP_SERVICE_URL` env var; default `http://localhost:4004`
- [x] `_fetch(path)` helper: synchronous `urllib.request.urlopen` with 10s timeout; returns parsed JSON dict
- [x] `STOCK_TOOLS` list exported: `[get_material_stock, get_atrisk_materials, get_sufficient_materials, get_stock_summary, get_critical_materials_by_plant, send_email]`

### Tool 1: `get_material_stock`

- [x] Decorated with `@tool`; trigger: any specific material number(s) mentioned in query (pattern `MAT-XXXX`)
- [x] Accepts comma-separated material numbers: splits on `,`, loops per material
- [x] OData filter: `$filter=Material eq '<mat>'` against `/stock/MaterialStockView`
- [x] Returns per material: Material, Description, Plant, Storage Location, Stock Qty, Unit, Reorder Point, Safety Stock, Status (`SUFFICIENT` / `NEARLY OUT OF STOCK`), Risk Reason (human-readable)
- [x] Returns `"No stock record found for material '<mat>'"` for unknown materials
- [x] All exceptions caught; returns error string — never raises

### Tool 2: `get_atrisk_materials`

- [x] Decorated with `@tool`; trigger: general "show at-risk" / "what needs attention" without a specific material number
- [x] Fetches all `/stock/MaterialStockView`; filters `StockStatus == "NEARLY_OUT_OF_STOCK"` client-side
- [x] Returns count + list: Material, Description, Plant, Location, Stock, Unit, Reorder Point, Safety Stock, Risk (human-readable label)
- [x] Returns `"No at-risk materials found."` for empty result
- [x] All exceptions caught; returns error string

### Tool 3: `get_sufficient_materials`

- [x] Decorated with `@tool`; trigger: general "show sufficient" / "what's healthy" without a specific material number
- [x] Fetches all `/stock/MaterialStockView`; filters `StockStatus == "SUFFICIENT"` client-side
- [x] Returns count + list: Material, Description, Plant, Location, Stock, Unit
- [x] Returns `"No materials with sufficient stock found."` for empty result
- [x] All exceptions caught; returns error string

### Tool 4: `get_stock_summary`

- [x] Decorated with `@tool`; trigger: "summary", "overview", "how is stock health"
- [x] Computes: total count, sufficient count, at-risk count, BOTH-breach count, reorder-point-only count, safety-stock-only count
- [x] Returns formatted multi-line summary string
- [x] All exceptions caught; returns error string

### Tool 5: `get_critical_materials_by_plant`

- [x] Decorated with `@tool`; accepts `plant: str` argument; trigger: "at-risk in plant 1000"
- [x] Fetches all `/stock/MaterialStockView`; filters `StockStatus == "NEARLY_OUT_OF_STOCK"` AND `Plant == plant` client-side
- [x] Returns count + list per plant: Material, Description, Location, Stock, Unit, RiskReason
- [x] Returns `"No at-risk materials found for plant {plant}."` for empty result
- [x] All exceptions caught; returns error string

### Tool 6: `send_email`

- [x] Decorated with `@tool`; accepts `to: str`, `subject: str`, `body: str`; trigger: "send email to X about MAT-Y"
- [x] Normalises recipient: appends `@sap.com` if no `@` domain present
- [x] Reads `SMTP_USER` + `SMTP_PASSWORD` from env vars; returns warning string (does not crash) if either absent
- [x] Gmail SMTP, port 587, STARTTLS via `ssl.create_default_context()`
- [x] Sends `MIMEMultipart("alternative")` message with plain-text body
- [x] Returns success string with To / Subject / Body on send; logs `EMAIL SENT | From | To | Subject`
- [x] All exceptions caught; returns `"❌ Failed to send email to '{to}': {e}"`

---

## `app/aicore.py` — AI Core LLM Resolver

- [x] `set_proxy_version("gen-ai-hub")` called at module import
- [x] `AICORE_DESTINATION_ENV = "AICORE_DESTINATION_NAME"`, default `"aicore"`; `TOKEN_TTL` from `DESTINATION_TOKEN_TTL` env var (default 600s)
- [x] `_vcap()` — parses `VCAP_SERVICES` JSON; returns `{}` on missing/invalid
- [x] `_first_binding(label)` — returns first service binding credentials dict for given label; returns `None` if absent
- [x] `_CachedToken` dataclass: `value: str`, `expires_at: float`, `expired()` method
- [x] `_client_credentials_token(token_url, client_id, client_secret, timeout=20.0)` — async POST to `{token_url}/oauth/token` with `grant_type=client_credentials`; returns `access_token`
- [x] `_xsuaa_access_token()` — checks `_xsuaa_token_cache`; fetches new token from destination service binding if expired; raises `RuntimeError` if no destination binding in VCAP
- [x] `_fetch_destination_raw(name)` — GET `{uri}/destination-configuration/v1/destinations/{name}` with bearer token; raises `RuntimeError` on HTTP 4xx+
- [x] `init_llm_from_destination(model_name, *, temperature, max_tokens, destination_name)` — idempotent: skips destination GET if `AICORE_BASE_URL` already set; extracts `URL`, `clientId`, `clientSecret`, `tokenServiceURL`, `AI-Resource-Group` from destination config; sets all `AICORE_*` env vars; returns `init_llm(model_name, **kwargs)`

---

## `app/mcp_tools.py` — MCP Tool Loader

- [x] **CF-only runtime**: `IBD_TESTING=1` → returns mock tools from `mcp-mock.json`; production CF → returns `[]` (Agent Gateway / mTLS not available on CF; `sap_cloud_sdk` not installed)
- [x] `_MOCK_FILE` = `Path(__file__).parent.parent / "mcp-mock.json"` (asset root)
- [x] `_build_mock_tools()` — parses `mcp-mock.json`; builds `StructuredTool` per tool with Pydantic `create_model` args schema; async coroutine returns `json.dumps(mock_response)`; returns `[]` silently if file absent or unparseable
- [x] `get_mcp_tools(use_cache=True)` — in test mode returns `_build_mock_tools()`; in production returns `[]`; no Agent Gateway client instantiated on CF

---

## `app/util.py` — MCP Utility Functions

- [x] `MCP_MAX_RESPONSE_CHARS` from `MCP_MAX_RESPONSE_CHARS` env var (default 100,000) — prevents OOM on large responses
- [x] `_MCP_RETRY_ATTEMPTS = 4`, `_MCP_RETRY_DELAY = 4.0s`
- [x] `_is_retryable_error(exc)` — returns `False` for HTTP 4xx client errors; `True` for HTTP 5xx, `ExceptionGroup`, `BaseExceptionGroup`, network/timeout errors
- [x] `enhance_tool_description(mcp_tool)` — prefixes description with `[{server_label}]`; uses `fragment_name` if available else `server_name`; returns `""` if tool is None with warning log
- [x] `enhance_tool_name(mcp_tool)` — parses `server_name` by `:` separator; drops first 2 segments if >2 (org + type); builds `{remaining}__{tool_name}`; sanitises to `^[a-zA-Z0-9-_]+$`; truncates to 55 chars + 8-char sha256 suffix if >64 chars
- [x] `call_mcp_tool_with_retry(agw_client, mcp_tool, **kwargs)` — logs tool name + arg keys only (never values — business/personal data risk); retries up to `_MCP_RETRY_ATTEMPTS` with `_MCP_RETRY_DELAY` sleep; handles `ExceptionGroup` teardown race (result already captured → suppress); validates result is not None; truncates response if >MCP_MAX_RESPONSE_CHARS; returns stale cache on refresh failure; raises last exception after all retries exhausted

---

## System Prompt Rules (`app/agent.py` → `get_system_prompt()`)

- [x] Base recommendations on tool-returned data only — no hallucination
- [x] **CRITICAL — specific material lookup**: any token matching `MAT-XXXX` pattern → always call `get_material_stock`; includes follow-ups ("What about MAT-1007?", "And MAT-1007?", "Is MAT-1007 ok?"); never call `get_atrisk_materials` / `get_sufficient_materials` when a material number is present
- [x] **CRITICAL — multiple materials**: >1 material number → single `get_material_stock` call with ALL as comma-separated string; never partial/first-only calls
- [x] General list queries (no material number) → `get_atrisk_materials` or `get_sufficient_materials`
- [x] Prioritise `BOTH` breach materials as most critical
- [x] Include plant + storage location when listing materials
- [x] **CRITICAL — email flow**: `get_material_stock` FIRST → compose professional email with stock data (material, plant, location, stock qty, reorder point, safety stock, status, recommended action) → `send_email` → confirm to user with `✅ Email sent to <recipient> regarding <material>`

---

## CF Deployment Configuration

### `manifest.yml`

- [x] App name: `nli-stockadv-agent`
- [x] Memory: `512M`, disk: `1G`, instances: `1`
- [x] Buildpack: `python_buildpack`
- [x] Start command: `gunicorn --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:${PORT} --chdir app main:application`
- [x] Timeout: `180`
- [x] Health-check type: `http`, endpoint: `/.well-known/agent.json`
- [x] Services: `proj-vector-destination-service`
- [x] Env: `AICORE_DESTINATION_NAME=aicore`, `CAP_SERVICE_URL=https://material-stock-dashboard-cap.cfapps.us10.hana.ondemand.com`, `LOG_LEVEL=INFO`

### `asset.yaml`

- [x] `apiVersion: asset.sap/v1`, `kind: Asset`
- [x] `metadata.name: nli-stockadv-agent`, `version: 2.0.0`
- [x] `type: agent`
- [x] `deployTarget.type: cf`, `deployTarget.url: https://nli-stockadv-agent.cfapps.us10.hana.ondemand.com`
- [x] `agentCard.version: 1.1.0`

---

## Migration Audit

- [x] `migration-audit/summary.md` records: runtime mode `cf-only` (Joule/Kyma runtime removed); systems `cap_direct` + `aicore`; LLM model `gpt-4o` (overridden — `sap/anthropic--claude-4.5-sonnet` not available in AI Core resource group); CF route confirmed; smoke verdict `healthy`
- [x] `migration-audit/state.json` records full migration state for traceability
- [x] `migration-audit/history` records timestamped run log

---

## Testing

- [x] `pytest.ini` — `testpaths = prebuilt_tests tests` (silently skips `tests/` if absent); `addopts`: `-v --no-header --timeout=600 -s --cov=app --cov-config=.coveragerc --cov-report=term-missing --cov-report=json:coverage.json`; `asyncio_mode = auto`; markers: `structure`, `server`, `integration`
- [x] `.coveragerc` — `[run] omit`: `app/agent_executor.py`, `app/extension_capabilities.py`, `app/main.py`, `app/mcp_client.py`, `app/ord.py`
- [x] `conftest.py` — sets `IBD_TESTING=1` before all imports; fixtures: `agent_path`, `agent_app_path`, `add_agent_to_path`, `start_agent` (subprocess server on free port, polls until ready, shuts down after); result collector writes `test_report.json` after full run; `_is_full_run()` guard prevents partial-run report overwrite

### `prebuilt_tests/test_structure.py` — Structure Tests (`@pytest.mark.structure`)

- [x] `TestRequiredFiles::test_agent_directory_exists` — verifies `AGENT_ROOT` exists and is a directory
- [x] `TestRequiredFiles::test_app_directory_exists` — verifies `AGENT_ROOT/app/` exists and is a directory
- [x] `TestRequiredFiles::test_requirements_txt_exists` — verifies `requirements.txt` exists and is non-empty

### `prebuilt_tests/test_server.py` — Server Integration Tests (`@pytest.mark.server`)

- [x] `TestServerStartup::test_server_starts` — verifies server subprocess is still running (poll() is None) and port > 0 after `start_agent` fixture
- [x] `TestA2AEndpoints::test_agent_card_endpoint` — GET `/.well-known/agent-card.json` → HTTP 200; valid JSON; contains `name` or `agentName` field; prints card name, description, and skill list

### Test Execution

```bash
cd assets/nli-stockadv-agent
pip install -r requirements-test.txt
pytest prebuilt_tests/ -v
```

- [x] All prebuilt tests pass: 5 tests (3 structure + 2 server) ✅
- [x] `coverage.json` written to asset root
- [x] `test_report.json` written to asset root after full run

---

## Integration with CAP Dashboard

- [x] CAP `srv/stock-service.js` exposes `/stock/chat` POST action
- [x] Chat action forwards user message to `AGENT_SERVICE_URL` env var (`https://nli-stockadv-agent.cfapps.us10.hana.ondemand.com`) via A2A protocol
- [x] Agent queries live stock data from CAP via `CAP_SERVICE_URL` env var → `/stock/MaterialStockView`
- [x] Circular dependency handled safely: CAP calls agent (A2A) → agent calls CAP (OData read) — different endpoints, no recursion

---

## Validation

- [x] `cf push` completed — app `nli-stockadv-agent` running on CF us10 ✅
- [x] `GET https://nli-stockadv-agent.cfapps.us10.hana.ondemand.com/.well-known/agent.json` → HTTP 200 ✅
- [x] Agent card JSON returned with correct name, description, version, skills ✅
- [x] All 5 prebuilt tests passing ✅
- [x] `migration-audit/summary.md` smoke verdict: `healthy` ✅
- [x] `assets/nli-stockadv-agent/coverage.json` exists ✅
- [x] `assets/nli-stockadv-agent/test_report.json` exists ✅
