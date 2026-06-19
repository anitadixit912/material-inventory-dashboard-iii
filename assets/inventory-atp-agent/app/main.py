"""
Inventory ATP Agent — A2A server entry point.

All heavy/optional imports (sap_cloud_sdk, aicore, langchain) are deferred
to import-time-safe blocks so the server always starts and passes the
CF health probe at /.well-known/agent.json regardless of which optional
packages are installed.
"""
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# —— Optional Joule SDK init ——————————————————————————————————————————————————
# MUST run before importing AI frameworks on Joule/Kyma.
# Wrapped so a missing or broken sap_cloud_sdk never kills startup.
if os.environ.get("JOULE_RUNTIME"):
    try:
        from sap_cloud_sdk.aicore import set_aicore_config
        set_aicore_config()
        logger.info("set_aicore_config() completed")
    except Exception as _e:
        logger.warning("set_aicore_config skipped: %s", _e)

    try:
        from sap_cloud_sdk.core.telemetry import auto_instrument
        auto_instrument()
        logger.info("auto_instrument() completed")
    except Exception as _e:
        logger.warning("auto_instrument skipped: %s", _e)

# —— Core A2A imports (always available via a2a-sdk) —————————————————————————
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent_executor import AgentExecutor

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))

skill = AgentSkill(
    id="inventory-atp-agent",
    name="inventory-atp-agent",
    description=(
        "An AI agent that analyzes inventory availability, explains stock drops, "
        "checks order feasibility via ATP, simulates corrective options, and "
        "executes approved supply chain actions."
    ),
    tags=["inventory", "atp", "supply-chain", "s4hana", "agent"],
    examples=[
        "Why did stock drop for material FG-001 in plant 1010?",
        "Can we fulfill 500 units of FG-001 by next Friday?",
    ],
)

agent_card = AgentCard(
    name="inventory-atp-agent",
    description=(
        "An AI agent that analyzes inventory availability, explains stock drops, "
        "checks order feasibility via ATP, simulates corrective options, and "
        "executes approved supply chain actions."
    ),
    url=os.environ.get("AGENT_PUBLIC_URL", f"http://{HOST}:{PORT}/"),
    version="1.0.0",
    default_input_modes=["text", "text/plain"],
    default_output_modes=["text", "text/plain"],
    capabilities=AgentCapabilities(streaming=True, push_notifications=False),
    skills=[skill],
)

server = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=DefaultRequestHandler(
        agent_executor=AgentExecutor(),
        task_store=InMemoryTaskStore(),
    ),
)

# Build the ASGI application
app = server.build()
application = app  # gunicorn looks for `application`

# —— Optional OpenTelemetry instrumentation ———————————————————————————————————
try:
    from opentelemetry.instrumentation.starlette import StarletteInstrumentor
    StarletteInstrumentor().instrument_app(app)
    logger.info("StarletteInstrumentor attached")
except Exception as _e:
    logger.warning("OpenTelemetry instrumentation skipped: %s", _e)

logger.info("A2A application built successfully (host=%s, port=%s)", HOST, PORT)


def main() -> None:
    """Entry point for direct invocation (development only)."""
    import argparse

    parser = argparse.ArgumentParser(description="Inventory ATP Agent A2A server")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--host", type=str, default=HOST)
    args, _ = parser.parse_known_args()

    logger.info("Starting A2A server at http://%s:%s", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
