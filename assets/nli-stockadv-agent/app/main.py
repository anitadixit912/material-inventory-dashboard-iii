"""
Stock Advisor Agent — A2A server entry point.
"""
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Core A2A imports ─────────────────────────────────────────────────────────
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent_executor import AgentExecutor

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))

skill = AgentSkill(
    id="nli-stockadv-agent",
    name="nli-stockadv-agent",
    description=(
        "An AI agent that analyzes material stock levels and provides "
        "replenishment recommendations based on real-time inventory data."
    ),
    tags=["stock", "inventory", "replenishment", "advisor"],
    examples=[
        "Which materials should I reorder today?",
        "What is the most critical stock item in plant 1000?",
        "Give me a summary of at-risk materials",
    ],
)

agent_card = AgentCard(
    name="nli-stockadv-agent",
    description=(
        "An AI agent that analyzes material stock levels and provides "
        "replenishment recommendations based on real-time inventory data."
    ),
    url=os.environ.get("AGENT_PUBLIC_URL", f"http://{HOST}:{PORT}/"),
    version="1.5.0",
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

# ── Optional OpenTelemetry instrumentation ───────────────────────────────────
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

    parser = argparse.ArgumentParser(description="Stock Advisor A2A server")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--host", type=str, default=HOST)
    args, _ = parser.parse_known_args()

    logger.info("Starting A2A server at http://%s:%s", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
