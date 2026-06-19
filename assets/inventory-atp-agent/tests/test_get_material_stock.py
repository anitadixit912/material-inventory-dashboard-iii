"""Tests for get_material_stock tool."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.get_material_stock import get_material_stock


@pytest.mark.asyncio
async def test_stock_returned_with_mock_tools():
    async def mock_tool(**kwargs):
        return {
            "value": [{
                "Material": "FG-001", "Plant": "1010", "StorageLocation": "0001",
                "MatlWrhsStkQtyInMatlBaseUnit": 120.0,
                "MaterialStockInTransferQty": 5.0,
                "MatlStkQtyInMatlBaseUnit": 10.0,
                "SafetyStock": 50.0,
                "MaterialBaseUnit": "EA",
            }]
        }
    tools = {"API_MATERIAL_STOCK_SRV__A_MaterialStock_Read": mock_tool}
    result = await get_material_stock("FG-001", "1010", mcp_tools=tools)
    assert result["material"] == "FG-001"
    assert result["plant"] == "1010"
    assert result["unrestricted_stock"] == 120.0
    assert result["unit_of_measure"] == "EA"
    assert "error" not in result


@pytest.mark.asyncio
async def test_stock_fallback_when_no_mcp():
    result = await get_material_stock("FG-002", "2020", mcp_tools=None)
    assert result["material"] == "FG-002"
    assert result["plant"] == "2020"
    assert "unrestricted_stock" in result
    assert "error" not in result


@pytest.mark.asyncio
async def test_stock_with_storage_location_filter():
    async def mock_tool(**kwargs):
        assert kwargs.get("StorageLocation") == "0002"
        return {"value": []}
    tools = {"API_MATERIAL_STOCK_SRV__A_MaterialStock_Read": mock_tool}
    result = await get_material_stock("FG-001", "1010", storage_location="0002", mcp_tools=tools)
    assert "error" not in result


@pytest.mark.asyncio
async def test_stock_error_handled_gracefully():
    async def mock_tool(**kwargs):
        raise RuntimeError("Connection refused")
    tools = {"API_MATERIAL_STOCK_SRV__A_MaterialStock_Read": mock_tool}
    result = await get_material_stock("FG-001", "1010", mcp_tools=tools)
    assert result.get("error") is True
    assert "error_reason" in result
