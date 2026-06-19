"""Integration tests for the full agent flow — all MCP tools and LLM mocked."""
import pytest
import sys, os
from unittest.mock import AsyncMock, patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from agent import SampleAgent, ROLE_TOOL_POLICY


def _make_mock_tool(name: str, return_value: str = '{"ok": true}'):
    tool = MagicMock()
    tool.name = name
    tool.description = f"Mock tool: {name}"
    return tool


# ---------------------------------------------------------------------------
# Role-based access tests (no LLM needed)
# ---------------------------------------------------------------------------

def test_planner_gets_all_tools():
    agent = SampleAgent.__new__(SampleAgent)
    agent._last_active = {}
    tools = [_make_mock_tool(n) for n in ["get_material_stock", "create_stock_transport_order", "run_atp_check"]]
    filtered = agent._filter_tools_by_role(tools, "PLANNER")
    assert len(filtered) == 3  # PLANNER gets all


def test_customer_service_read_only():
    agent = SampleAgent.__new__(SampleAgent)
    agent._last_active = {}
    tools = [_make_mock_tool(n) for n in ["get_material_stock", "run_atp_check", "create_stock_transport_order"]]
    filtered = agent._filter_tools_by_role(tools, "CUSTOMER_SERVICE")
    names = [t.name for t in filtered]
    assert "create_stock_transport_order" not in names
    assert "get_material_stock" in names
    assert "run_atp_check" in names


def test_sales_ops_cannot_create_sto():
    agent = SampleAgent.__new__(SampleAgent)
    agent._last_active = {}
    tools = [_make_mock_tool(n) for n in ["get_material_stock", "create_stock_transport_order", "propose_corrective_actions"]]
    filtered = agent._filter_tools_by_role(tools, "SALES_OPS")
    names = [t.name for t in filtered]
    assert "create_stock_transport_order" not in names


def test_unknown_role_defaults_to_read_only():
    agent = SampleAgent.__new__(SampleAgent)
    agent._last_active = {}
    tools = [_make_mock_tool(n) for n in ["get_material_stock", "create_stock_transport_order"]]
    filtered = agent._filter_tools_by_role(tools, None)
    names = [t.name for t in filtered]
    assert "create_stock_transport_order" not in names


# ---------------------------------------------------------------------------
# Agent stream tests (LLM mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_explain_stock_drop_m2_milestone(caplog):
    import logging
    agent = SampleAgent.__new__(SampleAgent)
    agent._last_active = {}

    mock_response = MagicMock()
    mock_response.content = "Stock dropped due to reservation order 1000001 consuming 200 units."

    with patch("agent.create_agent") as mock_create, \
         patch("agent.InMemorySaver"), \
         patch("agent.ChatLiteLLM"), \
         patch("agent.SummarizationMiddleware"):
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_response]}
        mock_create.return_value = mock_graph
        agent.llm = MagicMock()
        agent._checkpointer = MagicMock()
        agent._checkpointer.delete_thread = MagicMock()
        agent._summarization_middleware = MagicMock()

        with caplog.at_level(logging.INFO, logger="agent"):
            response = await agent._run_agent(
                "Why did stock drop for FG-001 in plant 1010?", "ctx-001", []
            )

    assert "Stock dropped" in response
    assert any("M2.achieved" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_atp_check_stream_completed():
    agent = SampleAgent.__new__(SampleAgent)
    agent._last_active = {}

    mock_response = MagicMock()
    mock_response.content = "ATP confirms 300 units by 2026-07-15."

    with patch("agent.create_agent") as mock_create, \
         patch("agent.InMemorySaver"), \
         patch("agent.ChatLiteLLM"), \
         patch("agent.SummarizationMiddleware"):
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_response]}
        mock_create.return_value = mock_graph
        agent.llm = MagicMock()
        agent._checkpointer = MagicMock()
        agent._checkpointer.delete_thread = MagicMock()
        agent._summarization_middleware = MagicMock()

        chunks = []
        async for chunk in agent.stream("Can we fulfill 300 units by 2026-07-15?", "ctx-002"):
            chunks.append(chunk)

    final = chunks[-1]
    assert final["is_task_complete"] is True
    assert "ATP confirms" in final["content"]


@pytest.mark.asyncio
async def test_agent_error_returns_gracefully():
    agent = SampleAgent.__new__(SampleAgent)
    agent._last_active = {}

    with patch("agent.create_agent") as mock_create, \
         patch("agent.InMemorySaver"), \
         patch("agent.ChatLiteLLM"), \
         patch("agent.SummarizationMiddleware"):
        mock_graph = AsyncMock()
        mock_graph.ainvoke.side_effect = RuntimeError("LLM timeout")
        mock_create.return_value = mock_graph
        agent.llm = MagicMock()
        agent._checkpointer = MagicMock()
        agent._checkpointer.delete_thread = MagicMock()
        agent._summarization_middleware = MagicMock()

        chunks = []
        async for chunk in agent.stream("Test query", "ctx-003"):
            chunks.append(chunk)

    final = chunks[-1]
    assert final["is_task_complete"] is True
    assert "error" in final["content"].lower()


@pytest.mark.asyncio
async def test_simulate_options_flow():
    agent = SampleAgent.__new__(SampleAgent)
    agent._last_active = {}

    mock_response = MagicMock()
    mock_response.content = "Ranked 3 corrective options: 1. Planned Order Conversion (0 days)..."

    with patch("agent.create_agent") as mock_create, \
         patch("agent.InMemorySaver"), \
         patch("agent.ChatLiteLLM"), \
         patch("agent.SummarizationMiddleware"):
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_response]}
        mock_create.return_value = mock_graph
        agent.llm = MagicMock()
        agent._checkpointer = MagicMock()
        agent._checkpointer.delete_thread = MagicMock()
        agent._summarization_middleware = MagicMock()

        result = await agent.invoke("What options do I have for FG-001 shortfall of 200 units?", "ctx-004")

    assert result.status == "completed"
    assert "Planned Order" in result.message


@pytest.mark.asyncio
async def test_execute_with_approval_write_tool_blocked_for_customer_service():
    agent = SampleAgent.__new__(SampleAgent)
    agent._last_active = {}
    write_tool = _make_mock_tool("create_stock_transport_order")
    read_tool = _make_mock_tool("get_material_stock")
    filtered = agent._filter_tools_by_role([write_tool, read_tool], "CUSTOMER_SERVICE")
    names = [t.name for t in filtered]
    assert "create_stock_transport_order" not in names
    assert "get_material_stock" in names
