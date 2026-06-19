"""Tests for flag_po_expedite tool."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.flag_po_expedite import flag_po_expedite


@pytest.mark.asyncio
async def test_expedite_payload_returned():
    result = await flag_po_expedite("4500001234", "000010", "STOCK_SHORTFALL")
    assert result["purchase_order"] == "4500001234"
    assert result["purchase_order_item"] == "000010"
    assert result["expedite_reason"] == "STOCK_SHORTFALL"
    assert result["status"] == "PENDING_BUYER_ACTION"


@pytest.mark.asyncio
async def test_status_is_pending_buyer_action():
    result = await flag_po_expedite("4500001234", "000010", "URGENT_DEMAND")
    assert result["status"] == "PENDING_BUYER_ACTION"


@pytest.mark.asyncio
async def test_buyer_note_included():
    result = await flag_po_expedite("4500001234", "000010", "STOCK_SHORTFALL", buyer_note="Urgent — SLA at risk")
    assert result["buyer_note"] == "Urgent — SLA at risk"


@pytest.mark.asyncio
async def test_flagged_at_timestamp_present():
    result = await flag_po_expedite("4500001234", "000010", "STOCK_SHORTFALL")
    assert "flagged_at" in result
    assert result["flagged_at"] != ""


@pytest.mark.asyncio
async def test_no_mcp_tool_needed():
    # flag_po_expedite does not use MCP — should always succeed
    result = await flag_po_expedite("4500001234", "000010", "LOW_STOCK", mcp_tools={})
    assert result["status"] == "PENDING_BUYER_ACTION"
