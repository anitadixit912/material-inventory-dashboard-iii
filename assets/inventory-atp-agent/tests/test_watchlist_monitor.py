"""Tests for watchlist_monitor tool."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.watchlist_monitor import watchlist_monitor


def _make_stock_mock(unrestricted_stock: float):
    async def mock_tool(**kwargs):
        return {
            "value": [{
                "Material": kwargs.get("Material", "FG-001"),
                "Plant": kwargs.get("Plant", "1010"),
                "StorageLocation": "0001",
                "MatlWrhsStkQtyInMatlBaseUnit": unrestricted_stock,
                "MaterialStockInTransferQty": 0.0,
                "MatlStkQtyInMatlBaseUnit": 0.0,
                "SafetyStock": 50.0,
                "MaterialBaseUnit": "EA",
            }]
        }
    return {"API_MATERIAL_STOCK_SRV__A_MaterialStock_Read": mock_tool}


@pytest.mark.asyncio
async def test_high_severity_breach():
    tools = _make_stock_mock(10.0)  # 10 vs threshold 100 → 90% deficit → HIGH
    watchlist = [{"material": "FG-001", "plant": "1010", "safety_stock_threshold": 100.0, "sla_date": "2026-07-15"}]
    alerts = await watchlist_monitor(watchlist, mcp_tools=tools)
    assert len(alerts) == 1
    assert alerts[0]["breach_severity"] == "HIGH"
    assert alerts[0]["alert_type"] == "SAFETY_STOCK_BREACH"


@pytest.mark.asyncio
async def test_medium_severity_breach():
    tools = _make_stock_mock(70.0)  # 70 vs threshold 100 → 30% deficit → MEDIUM
    watchlist = [{"material": "FG-001", "plant": "1010", "safety_stock_threshold": 100.0, "sla_date": "2026-07-15"}]
    alerts = await watchlist_monitor(watchlist, mcp_tools=tools)
    assert len(alerts) == 1
    assert alerts[0]["breach_severity"] == "MEDIUM"


@pytest.mark.asyncio
async def test_low_severity_breach():
    tools = _make_stock_mock(85.0)  # 85 vs threshold 100 → 15% deficit → LOW
    watchlist = [{"material": "FG-001", "plant": "1010", "safety_stock_threshold": 100.0, "sla_date": "2026-07-15"}]
    alerts = await watchlist_monitor(watchlist, mcp_tools=tools)
    assert len(alerts) == 1
    assert alerts[0]["breach_severity"] == "LOW"


@pytest.mark.asyncio
async def test_no_breach_returns_empty():
    tools = _make_stock_mock(200.0)  # 200 > threshold 100 → no breach
    watchlist = [{"material": "FG-001", "plant": "1010", "safety_stock_threshold": 100.0, "sla_date": "2026-07-15"}]
    alerts = await watchlist_monitor(watchlist, mcp_tools=tools)
    assert alerts == []


@pytest.mark.asyncio
async def test_multiple_entries_mixed():
    async def mock_tool(**kwargs):
        material = kwargs.get("Material", "FG-001")
        stock = 200.0 if material == "FG-001" else 10.0
        return {"value": [{"Material": material, "Plant": "1010", "StorageLocation": "0001",
                           "MatlWrhsStkQtyInMatlBaseUnit": stock, "MaterialStockInTransferQty": 0.0,
                           "MatlStkQtyInMatlBaseUnit": 0.0, "SafetyStock": 50.0, "MaterialBaseUnit": "EA"}]}
    tools = {"API_MATERIAL_STOCK_SRV__A_MaterialStock_Read": mock_tool}
    watchlist = [
        {"material": "FG-001", "plant": "1010", "safety_stock_threshold": 100.0, "sla_date": "2026-07-15"},
        {"material": "FG-002", "plant": "1010", "safety_stock_threshold": 100.0, "sla_date": "2026-07-15"},
    ]
    alerts = await watchlist_monitor(watchlist, mcp_tools=tools)
    assert len(alerts) == 1
    assert alerts[0]["material"] == "FG-002"


@pytest.mark.asyncio
async def test_empty_watchlist():
    alerts = await watchlist_monitor([], mcp_tools=None)
    assert alerts == []
