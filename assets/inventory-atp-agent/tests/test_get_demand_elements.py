"""Tests for get_demand_elements tool."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.get_demand_elements import get_demand_elements


@pytest.mark.asyncio
async def test_demand_elements_parsed_correctly():
    async def mock_sd(**kwargs):
        return {"value": [
            {"MRPElementCategory": "OrdRes", "MRPElement": "1000001", "MRPElementSupplyDemandQuantity": -200.0, "MRPElementOpenQuantityDate": "2026-07-01"},
            {"MRPElementCategory": "PurOrd", "MRPElement": "4500001", "MRPElementSupplyDemandQuantity": 300.0, "MRPElementOpenQuantityDate": "2026-07-10"},
        ]}
    async def mock_mrp(**kwargs):
        return {"value": [{"SafetyStock": 50.0, "ReorderPoint": 100.0}]}
    tools = {
        "API_MRP_MATERIALS_SRV_01__SupplyDemandItems_Read": mock_sd,
        "API_MRP_MATERIALS_SRV_01__A_MRPMaterial_Read": mock_mrp,
    }
    result = await get_demand_elements("FG-001", "1010", mcp_tools=tools)
    assert result["safety_stock"] == 50.0
    assert result["reorder_point"] == 100.0
    assert len(result["demand_elements"]) == 1
    assert len(result["supply_elements"]) == 1


@pytest.mark.asyncio
async def test_demand_elements_fallback_no_mcp():
    result = await get_demand_elements("FG-001", "1010", mcp_tools=None)
    assert "demand_elements" in result
    assert "supply_elements" in result
    assert "error" not in result


@pytest.mark.asyncio
async def test_date_filter_passed_to_tool():
    called_with = {}
    async def mock_sd(**kwargs):
        called_with.update(kwargs)
        return {"value": []}
    async def mock_mrp(**kwargs):
        return {"value": [{}]}
    tools = {
        "API_MRP_MATERIALS_SRV_01__SupplyDemandItems_Read": mock_sd,
        "API_MRP_MATERIALS_SRV_01__A_MRPMaterial_Read": mock_mrp,
    }
    await get_demand_elements("FG-001", "1010", date_from="2026-07-01", date_to="2026-07-31", mcp_tools=tools)
    assert called_with.get("DateFrom") == "2026-07-01"


@pytest.mark.asyncio
async def test_demand_error_handled():
    async def mock_sd(**kwargs):
        raise RuntimeError("API error")
    tools = {"API_MRP_MATERIALS_SRV_01__SupplyDemandItems_Read": mock_sd}
    result = await get_demand_elements("FG-001", "1010", mcp_tools=tools)
    assert result.get("error") is True
