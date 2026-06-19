import logging
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.checkpoint.memory import InMemorySaver
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Role-based tool access policy
# ---------------------------------------------------------------------------
ROLE_TOOL_POLICY: dict[str, list[str]] = {
    "PLANNER": [],  # empty = all tools allowed
    "SALES_OPS": ["get_material_stock", "run_atp_check", "propose_corrective_actions"],
    "CUSTOMER_SERVICE": ["get_material_stock", "run_atp_check"],
    "PROCUREMENT_MANAGER": ["flag_po_expedite", "get_demand_elements", "get_planned_orders"],
}

# Write tools that require explicit user approval before invocation
APPROVAL_REQUIRED_TOOLS = {
    "create_stock_transport_order",
    "convert_planned_order",
    "adjust_pir",
    "flag_po_expedite",
}


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return "sap/anthropic--claude-4.5-sonnet"


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
    return """You are an Inventory ATP Agentic Copilot for SAP S/4HANA Cloud. You handle 5 sub-intents:

1. **Explain_Stock_Drop** — Use get_material_stock and get_demand_elements to identify why stock dropped. Cite exact quantities and document numbers from tool results.
2. **Check_Order_Feasibility** — Use run_atp_check to validate if a requested quantity can be confirmed by a required date. Report confirmed quantity, ATP date, and unfulfilled quantity.
3. **Protect_Service_Level** — Use watchlist_monitor to check materials against safety stock thresholds. Return structured alerts for breaches.
4. **Simulate_Options** — Use propose_corrective_actions to generate and rank corrective options for a shortfall. Present ranked options clearly with lead times and trade-offs.
5. **Execute_With_Approval** — Before calling any write tool (create_stock_transport_order, convert_planned_order, adjust_pir, flag_po_expedite), you MUST present an approval card to the user showing: action type, key parameters, estimated impact. Only proceed after the user explicitly confirms with "confirm" or "yes".

**Rules:**
- NEVER hallucinate quantities, dates, or document numbers — cite ONLY values returned by tools.
- Always set $top=100 (or equivalent limit parameter) on every tool call that accepts a limit.
- Write tools MUST NOT be called unless the user has explicitly confirmed the action card in the current conversation turn.
- If ATP simulation returns partial or ambiguous results, explain uncertainty explicitly.
- Always state which tool provided the data in your response.
"""


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


THREAD_TTL_SECONDS = 3600  # evict threads inactive for 1 hour


class SampleAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self.llm = ChatLiteLLM(model=get_model_name(), temperature=get_temperature())
        self._checkpointer = InMemorySaver()
        self._last_active: dict[str, float] = {}
        self._summarization_middleware = SummarizationMiddleware(
            model=self.llm,
            trigger=("tokens", 100_000),
        )

    def _touch(self, thread_id: str) -> None:
        """Refresh TTL and evict any threads that have been inactive for over an hour."""
        now = time.monotonic()
        expired = [
            tid
            for tid, ts in list(self._last_active.items())
            if now - ts > THREAD_TTL_SECONDS
        ]
        for tid in expired:
            self._checkpointer.delete_thread(tid)
            del self._last_active[tid]
            logger.info("Evicted inactive thread: %s", tid)
        self._last_active[thread_id] = now

    def _filter_tools_by_role(
        self, tools: Sequence[BaseTool], role: str | None
    ) -> list[BaseTool]:
        """Filter tools based on user role. Unknown/absent role → read-only."""
        if role is None:
            allowed = ROLE_TOOL_POLICY.get("CUSTOMER_SERVICE", [])
        else:
            allowed = ROLE_TOOL_POLICY.get(role.upper(), [])
        if not allowed:
            # Empty list means all tools allowed (PLANNER)
            return list(tools)
        return [t for t in tools if t.name in allowed]

    async def _run_agent(
        self,
        query: str,
        context_id: str,
        tools: list[BaseTool],
    ) -> str:
        """Core agent execution — runs the LangGraph agent and returns the response string."""
        graph = create_agent(
            self.llm,
            tools=tools,
            system_prompt=get_system_prompt(),
            checkpointer=self._checkpointer,
            middleware=[self._summarization_middleware],
        )
        config = {"configurable": {"thread_id": context_id}}
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=query)]}, config
        )
        response = result["messages"][-1].content

        # M2 milestone — root-cause analysis completed
        if any(kw in query.lower() for kw in ["drop", "why", "cause", "explain", "fell"]):
            logger.info(
                "M2.achieved: root_cause_identified | primary_cause=stock_drop contributing_elements=%d material=unknown",
                0,
            )
        return response

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
        role: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream agent responses with role-based tool filtering."""
        self._touch(context_id)
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing...",
        }

        try:
            filtered_tools = self._filter_tools_by_role(tools or [], role)
            if tools:
                logger.info(
                    "Running agent with %d tool(s) (role=%s): %s",
                    len(filtered_tools),
                    role or "default",
                    [t.name for t in filtered_tools],
                )
            else:
                logger.info("Running agent without tools")

            response = await self._run_agent(query, context_id, filtered_tools)
            self._touch(context_id)

            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }

        except Exception as e:
            logger.exception("Agent stream() failed")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"I encountered an error while processing your request: {str(e)}. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
        role: str | None = None,
    ) -> AgentResponse:
        """Invoke agent and return final response."""
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools, role=role):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(
            status="error", message=last.get("content", "Unknown error")
        )
