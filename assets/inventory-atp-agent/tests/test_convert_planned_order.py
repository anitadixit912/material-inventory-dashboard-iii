"""Tests for convert_planned_order tool."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.convert_planned_order import convert_planned_order


@pytest.mark.asyncio
async def test_conversion_successful():
    async def mock_tool(**kwargs):
        return {"PlannedOrder": "0000100001", "ProductionOrder": "PRD0000100001", "Status": "CONVERTED"}
    tools = {"API_PLANNED_ORDERS__PlannedOrderSchedule": mock_tool}
    result = await convert_planned_order("0000100001", mcp_tools=tools)
    assert result["converted_document_number"] == "PRD0000100001"
    assert result["status"] == "CONVERTED"
    assert result["planned_order"] == "0000100001"


@pytest.mark.asyncio
async def test_conversion_fallback_no_mcp():
    result = await convert_planned_order("0000100002", mcp_tools=None)
    assert result["planned_order"] == "0000100002"
    assert "converted_document_number" in result
    assert result["status"] == "CONVERTED"


@pytest.mark.asyncio
async def test_conversion_order_type_passed():
    called_with = {}
    async def mock_tool(**kwargs):
        called_with.update(kwargs)
        return {"ProductionOrder": "PRD123"}
    tools = {"API_PLANNED_ORDERS__PlannedOrderSchedule": mock_tool}
    await convert_planned_order("0000100001", conversion_order_type="process", mcp_tools=tools)
    assert called_with.get("OrderType") == "process"


@pytest.mark.asyncio
async def test_conversion_error_handled():
    async def mock_tool(**kwargs):
        raise RuntimeError("Conversion not allowed")
    tools = {"API_PLANNED_ORDERS__PlannedOrderSchedule": mock_tool}
    result = await convert_planned_order("0000100001", mcp_tools=tools)
    assert result.get("error") is True
    assert "error_reason" in result
