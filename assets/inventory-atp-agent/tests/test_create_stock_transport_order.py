"""Tests for create_stock_transport_order tool."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.create_stock_transport_order import create_stock_transport_order


@pytest.mark.asyncio
async def test_sto_created_successfully():
    async def mock_tool(**kwargs):
        return {"StockTransportOrder": "STO4500001", "Status": "CREATED"}
    tools = {"CE_STOCKTRANSPORTORDER_0001__Create": mock_tool}
    result = await create_stock_transport_order(
        "FG-001", "1010", "2020", 100.0, "EA", "2026-07-20", mcp_tools=tools
    )
    assert result["sto_document_number"] == "STO4500001"
    assert result["status"] == "CREATED"
    assert result["quantity"] == 100.0


@pytest.mark.asyncio
async def test_sto_mcp_unavailable_returns_structured_error():
    result = await create_stock_transport_order(
        "FG-001", "1010", "2020", 100.0, "EA", "2026-07-20", mcp_tools=None
    )
    assert result.get("error") == "STO_MCP_UNAVAILABLE"
    assert "message" in result


@pytest.mark.asyncio
async def test_sto_mcp_unavailable_with_empty_tools():
    result = await create_stock_transport_order(
        "FG-001", "1010", "2020", 100.0, "EA", "2026-07-20", mcp_tools={}
    )
    assert result.get("error") == "STO_MCP_UNAVAILABLE"


@pytest.mark.asyncio
async def test_sto_api_error_handled():
    async def mock_tool(**kwargs):
        raise RuntimeError("S/4HANA write failed")
    tools = {"CE_STOCKTRANSPORTORDER_0001__Create": mock_tool}
    result = await create_stock_transport_order(
        "FG-001", "1010", "2020", 100.0, "EA", "2026-07-20", mcp_tools=tools
    )
    assert result.get("error") is True
    assert "error_reason" in result
