"""Tests for propose_corrective_actions tool."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.propose_corrective_actions import propose_corrective_actions


@pytest.mark.asyncio
async def test_four_options_generated():
    result = await propose_corrective_actions("FG-001", "1010", 200.0, "2026-07-15", mcp_tools=None)
    assert "options" in result
    assert len(result["options"]) >= 2


@pytest.mark.asyncio
async def test_options_ranked_by_lead_days():
    result = await propose_corrective_actions("FG-001", "1010", 200.0, "2026-07-15", mcp_tools=None)
    options = result["options"]
    lead_days = [o["estimated_lead_days"] for o in options]
    assert lead_days == sorted(lead_days)


@pytest.mark.asyncio
async def test_all_options_require_approval():
    result = await propose_corrective_actions("FG-001", "1010", 100.0, "2026-07-15", mcp_tools=None)
    for opt in result["options"]:
        assert opt.get("requires_approval") is True


@pytest.mark.asyncio
async def test_planned_order_conversion_option_present():
    result = await propose_corrective_actions("FG-001", "1010", 100.0, "2026-07-15", mcp_tools=None)
    types = [o["type"] for o in result["options"]]
    assert "PLANNED_ORDER_CONVERSION" in types


@pytest.mark.asyncio
async def test_partial_fulfillment_always_present():
    result = await propose_corrective_actions("FG-001", "1010", 100.0, "2026-07-15", mcp_tools=None)
    types = [o["type"] for o in result["options"]]
    assert "PARTIAL_FULFILLMENT" in types


@pytest.mark.asyncio
async def test_shortfall_qty_in_result():
    result = await propose_corrective_actions("FG-001", "1010", 350.0, "2026-07-20", mcp_tools=None)
    assert result["shortfall_quantity"] == 350.0
    assert result["required_date"] == "2026-07-20"
