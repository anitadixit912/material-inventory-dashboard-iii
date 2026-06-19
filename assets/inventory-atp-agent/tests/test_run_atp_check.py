"""Tests for run_atp_check tool."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.run_atp_check import run_atp_check


@pytest.mark.asyncio
async def test_full_atp_confirmed():
    async def mock_tool(**kwargs):
        return {"ConfirmedQuantity": 500.0, "AvailabilityDate": "2026-07-15", "ReasonCode": "", "ReasonText": "Fully confirmed"}
    tools = {"CE_APIAVAILTOPROMISECHECK_0001__CheckAvailabilityWithoutResvn": mock_tool}
    result = await run_atp_check("FG-001", "1010", 500.0, "2026-07-15", mcp_tools=tools)
    assert result["is_fully_confirmed"] is True
    assert result["confirmed_quantity"] == 500.0
    assert result["unfulfilled_quantity"] == 0.0


@pytest.mark.asyncio
async def test_partial_atp():
    async def mock_tool(**kwargs):
        return {"ConfirmedQuantity": 200.0, "AvailabilityDate": "2026-07-20", "ReasonCode": "01", "ReasonText": "Partial stock"}
    tools = {"CE_APIAVAILTOPROMISECHECK_0001__CheckAvailabilityWithoutResvn": mock_tool}
    result = await run_atp_check("FG-001", "1010", 500.0, "2026-07-15", mcp_tools=tools)
    assert result["is_fully_confirmed"] is False
    assert result["confirmed_quantity"] == 200.0
    assert result["unfulfilled_quantity"] == 300.0


@pytest.mark.asyncio
async def test_zero_confirmed():
    async def mock_tool(**kwargs):
        return {"ConfirmedQuantity": 0.0, "AvailabilityDate": "", "ReasonCode": "02", "ReasonText": "No stock available"}
    tools = {"CE_APIAVAILTOPROMISECHECK_0001__CheckAvailabilityWithoutResvn": mock_tool}
    result = await run_atp_check("FG-001", "1010", 300.0, "2026-07-15", mcp_tools=tools)
    assert result["is_fully_confirmed"] is False
    assert result["confirmed_quantity"] == 0.0
    assert result["unfulfilled_quantity"] == 300.0


@pytest.mark.asyncio
async def test_atp_fallback_no_mcp():
    result = await run_atp_check("FG-001", "1010", 200.0, "2026-07-15", mcp_tools=None)
    assert "confirmed_quantity" in result
    assert "is_fully_confirmed" in result
    assert "error" not in result


@pytest.mark.asyncio
async def test_atp_error_handled():
    async def mock_tool(**kwargs):
        raise RuntimeError("ATP service unavailable")
    tools = {"CE_APIAVAILTOPROMISECHECK_0001__CheckAvailabilityWithoutResvn": mock_tool}
    result = await run_atp_check("FG-001", "1010", 500.0, "2026-07-15", mcp_tools=tools)
    assert result.get("error") is True
    assert "error_reason" in result
