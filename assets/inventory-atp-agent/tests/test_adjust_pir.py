"""Tests for adjust_pir tool."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.adjust_pir import adjust_pir


@pytest.mark.asyncio
async def test_pir_adjusted_successfully():
    async def mock_tool(**kwargs):
        return {"PlannedIndepRqmt": "PIR1000001", "OldQuantity": 200.0, "NewQuantity": 150.0}
    tools = {"API_PLND_INDEP_RQMT_SRV__PlannedIndepRqmtItem_Update": mock_tool}
    result = await adjust_pir("FG-001", "1010", "00", "2026-07-01", 150.0, mcp_tools=tools)
    assert result["document_number"] == "PIR1000001"
    assert result["old_quantity"] == 200.0
    assert result["new_quantity"] == 150.0


@pytest.mark.asyncio
async def test_pir_old_new_quantities_present():
    result = await adjust_pir("FG-001", "1010", "00", "2026-07-01", 100.0, mcp_tools=None)
    assert "old_quantity" in result
    assert "new_quantity" in result
    assert result["new_quantity"] == 100.0


@pytest.mark.asyncio
async def test_pir_fallback_no_mcp():
    result = await adjust_pir("FG-002", "2020", "01", "2026-08-01", 50.0, mcp_tools=None)
    assert result["material"] == "FG-002"
    assert result["plant"] == "2020"
    assert "document_number" in result
    assert "error" not in result


@pytest.mark.asyncio
async def test_pir_error_handled():
    async def mock_tool(**kwargs):
        raise RuntimeError("Update locked")
    tools = {"API_PLND_INDEP_RQMT_SRV__PlannedIndepRqmtItem_Update": mock_tool}
    result = await adjust_pir("FG-001", "1010", "00", "2026-07-01", 100.0, mcp_tools=tools)
    assert result.get("error") is True
    assert "error_reason" in result
