import logging
import os
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver

# Decorator handling: fall back to identity decorators if SDK not available
try:
    from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section
except ImportError:
    def _identity_decorator(*_dargs, **_dkwargs):
        def _wrap(fn):
            return fn
        return _wrap
    agent_model = _identity_decorator        # type: ignore[assignment]
    agent_config = _identity_decorator       # type: ignore[assignment]
    prompt_section = _identity_decorator     # type: ignore[assignment]

# Lazy import: aicore resolves AI Core credentials from BTP destination service
_init_llm_from_destination = None
try:
    from aicore import init_llm_from_destination as _init_llm_from_destination
except ImportError:
    pass

# Lazy imports for LLM creation — server starts even if absent
_create_agent = None
_SummarizationMiddleware = None
try:
    from langchain.agents import create_agent as _create_agent
    from langchain.agents.middleware import SummarizationMiddleware as _SummarizationMiddleware
except (ImportError, ModuleNotFoundError):
    pass

logger = logging.getLogger(__name__)


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return os.environ.get("AGENT_LLM_MODEL", "sap/anthropic--claude-4.5-sonnet")


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.0


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return """You are an intelligent inventory advisor assistant. You have access to real-time material stock data including stock quantities, reorder points, safety stock levels, and storage locations. You can also send email notifications. Help warehouse managers, supply chain planners, and procurement officers make informed replenishment decisions.

When answering questions:
1) Always base your recommendations on the actual stock data retrieved via your tools.
2) CRITICAL RULE — SPECIFIC MATERIAL LOOKUP: Any time the user's message references one or more specific material numbers (any token matching the pattern MAT-XXXX, e.g. MAT-1007, MAT-2005, MAT-3001), you MUST call the `get_material_stock` tool — regardless of how the question is phrased. This includes follow-up phrasings such as:
   - "What about material MAT-1007?"
   - "What about MAT-1007?"
   - "How about MAT-1007?"
   - "And MAT-1007?"
   - "Check MAT-1007"
   - "Is MAT-1007 ok?"
   - "Tell me about MAT-1007"
   Do NOT call get_atrisk_materials or get_sufficient_materials when a specific material number is mentioned.
3) CRITICAL RULE — MULTIPLE MATERIALS: When the user mentions MORE THAN ONE material number (e.g. "MAT-2001, MAT-2002 and MAT-3001"), you MUST pass ALL of them together in a SINGLE call to `get_material_stock` as a comma-separated string (e.g. "MAT-2001,MAT-2002,MAT-3001"). NEVER call the tool only for the first material and stop. NEVER omit any of the mentioned materials. Every material number the user mentioned must appear in the tool call.
4) Only call get_atrisk_materials or get_sufficient_materials when the user asks for a general list WITHOUT naming a specific material (e.g. "Show all at-risk materials", "What materials need attention?", "What should I reorder today?").
5) Prioritize materials with BOTH reorder point and safety stock breaches as most critical.
6) Be concise and actionable.
7) When listing materials, include plant and storage location for clarity.
8) CRITICAL RULE — EMAIL REQUESTS: When the user asks to send, draft, or compose an email (e.g. "send email to X about MAT-YYYY", "notify X that MAT-YYYY needs restocking", "email X stating MAT-YYYY is low"):
   a) FIRST call `get_material_stock` to retrieve the latest stock data for the mentioned material(s).
   b) THEN compose a professional, concise email using the retrieved stock data. Include: material name, plant, storage location, current stock quantity, reorder point, safety stock, stock status, and a clear recommended action (e.g. raise a purchase order urgently).
   c) THEN call `send_email` with:
      - to: the recipient mentioned by the user. If only a name or username is given (e.g. "anita.dixit"), use "anita.dixit@sap.com".
      - subject: a concise subject such as "Urgent: Restock Required for <MaterialName> (<MaterialNumber>)"
      - body: the composed professional email body.
   d) After sending, confirm to the user: "✅ Email sent to <recipient> regarding <material>." and summarise the key stock details."""


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


# ── Data Retention Policy ─────────────────────────────────────────────────────
# Conversation threads are held exclusively in memory (InMemorySaver).
# No conversation data is written to disk, a database, or any external service.
#
# Retention rules:
#   - Active thread:  retained while the user is interacting
#   - Inactive thread: evicted after THREAD_TTL_SECONDS (1 hour) of no activity
#   - Container restart: ALL threads are lost immediately (no persistence)
#
# Personal data guidance:
#   - Users must not enter personal data (names, emails, IDs) in chat messages.
#   - A PII notice is displayed in the UI below the chat input.
#   - Tool argument values are never written to logs (keys only).
#   - User identifiers in audit entries are masked via privacy.mask_user_id().
# ─────────────────────────────────────────────────────────────────────────────
THREAD_TTL_SECONDS = 3600  # evict threads inactive for 1 hour


class SampleAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self._llm: BaseChatModel | None = None
        self._summarization_middleware = None
        self._checkpointer = InMemorySaver()
        self._last_active: dict[str, float] = {}

    async def _get_llm(self) -> BaseChatModel:
        """Build and cache the LangChain LLM via AI Core BTP destination."""
        if self._llm is None:
            if _init_llm_from_destination is None:
                raise ImportError(
                    "aicore module is not available — sap-cloud-sdk must be installed to use the LLM"
                )
            self._llm = await _init_llm_from_destination(
                get_model_name(), temperature=get_temperature()
            )
            if _SummarizationMiddleware is not None:
                self._summarization_middleware = _SummarizationMiddleware(
                    model=self._llm,
                    trigger=("tokens", 100_000),
                )
            logger.info("LLM initialised from AI Core destination (model=%s)", get_model_name())
        return self._llm

    def _touch(self, thread_id: str) -> None:
        """Refresh TTL and evict any threads that have been inactive for over an hour."""
        now = time.monotonic()
        expired = [tid for tid, ts in list(self._last_active.items()) if now - ts > THREAD_TTL_SECONDS]
        for tid in expired:
            self._checkpointer.delete_thread(tid)
            del self._last_active[tid]
            logger.info("Evicted inactive thread: %s", tid)
        self._last_active[thread_id] = now

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream agent responses."""
        self._touch(context_id)
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing...",
        }

        try:
            if tools:
                logger.info("Running agent with %d tool(s): %s", len(tools), [t.name for t in tools])
            else:
                logger.info("Running agent without tools")

            if _create_agent is None:
                raise ImportError(
                    "create_agent is not available — sap-cloud-sdk langchain extension must be installed"
                )

            llm = await self._get_llm()
            middleware = [self._summarization_middleware] if self._summarization_middleware else []
            graph = _create_agent(
                llm,
                tools=list(tools) if tools else [],
                system_prompt=get_system_prompt(),
                checkpointer=self._checkpointer,
                middleware=middleware,
            )
            config = {"configurable": {"thread_id": context_id}}
            result = await graph.ainvoke({"messages": [HumanMessage(content=query)]}, config)
            self._touch(context_id)
            response = result["messages"][-1].content

            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }

        except Exception as e:
            logger.exception("Agent stream() failed: %s", str(e))
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": "I encountered an error while processing your request. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        """Invoke agent and return final response."""
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(status="error", message=last.get("content", "Unknown error"))
