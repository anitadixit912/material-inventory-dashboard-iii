"""Tests for get_planned_orders tool."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.get_planned_orders import get_planned_orders


@pytest.mark.asyncio
async def test_planned_orders_returned():
    async def mock_tool(**kwargs):
        return {"value": [
            {"PlannedOrder": "0000100001", "PlannedOrderType": "ZP01",
             "PlannedOrderPlannedQuantity": 500.0, "PlannedOrderOpeningDate": "2026-07-01",
             "PlannedOrderEndDate": "2026-07-10", "MRPType": "X"},
        ]}
    tools = {"API_PLANNED_ORDERS__A_PlannedOrder_Read": mock_tool}
    result = await get_planned_orders("FG-001", "1010", mcp_tools=tools)
    assert result["count"] == 1
    assert result["planned_orders"][0]["planned_order"] == "0000100001"
    assert result["planned_orders"][0]["quantity"] == 500.0


@pytest.mark.asyncio
async def test_empty_planned_orders():
    async def mock_tool(**kwargs):
        return {"value": []}
    tools = {"API_PLANNED_ORDERS__A_PlannedOrder_Read": mock_tool}
    result = await get_planned_orders("FG-999", "9999", mcp_tools=tools)
    assert result["count"] == 0
    assert result["planned_orders"] == []


@pytest.mark.asyncio
async def test_planned_orders_fallback_no_mcp():
    result = await get_planned_orders("FG-001", "1010", mcp_tools=None)
    assert "planned_orders" in result
    assert result["count"] > 0


@pytest.mark.asyncio
async def test_date_filter_passed():
    called_with = {}
    async def mock_tool(**kwargs):
        called_with.update(kwargs)
        return {"value": []}
    tools = {"API_PLANNED_ORDERS__A_PlannedOrder_Read": mock_tool}
    await get_planned_orders("FG-001", "1010", date_from="2026-07-01", mcp_tools=tools)
    assert called_with.get("PlannedOrderOpeningDate") == "2026-07-01"


@pytest.mark.asyncio
async def test_error_handled_gracefully():
    async def mock_tool(**kwargs):
        raise RuntimeError("Network error")
    tools = {"API_PLANNED_ORDERS__A_PlannedOrder_Read": mock_tool}
    result = await get_planned_orders("FG-001", "1010", mcp_tools=tools)
    assert result.get("error") is True
