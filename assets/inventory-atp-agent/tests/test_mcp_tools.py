"""Unit tests for mcp_tools.py — mock tool loading and conversion."""
import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure IBD_TESTING is set for all tests in this module
os.environ["IBD_TESTING"] = "1"

# Add app/ to path so mcp_tools can resolve peer imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from app.mcp_tools import _build_mock_tools, get_mcp_tools, _MOCK_FILE


# ---------------------------------------------------------------------------
# _build_mock_tools
# ---------------------------------------------------------------------------

def test_build_mock_tools_returns_list():
    tools = _build_mock_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0


def test_build_mock_tools_all_have_names():
    tools = _build_mock_tools()
    for t in tools:
        assert t.name
        assert isinstance(t.name, str)


def test_build_mock_tools_all_have_descriptions():
    tools = _build_mock_tools()
    for t in tools:
        assert t.description


def test_build_mock_tools_count_matches_mock_file():
    mock_data = json.loads(_MOCK_FILE.read_text())
    expected = sum(
        len(server.get("tools", {}))
        for server in mock_data.get("servers", {}).values()
    )
    tools = _build_mock_tools()
    assert len(tools) == expected


def test_build_mock_tools_missing_file_returns_empty(tmp_path, monkeypatch):
    """When mcp-mock.json does not exist, return empty list without raising."""
    import app.mcp_tools as mcp_tools_module
    monkeypatch.setattr(mcp_tools_module, "_MOCK_FILE", tmp_path / "nonexistent.json")
    result = mcp_tools_module._build_mock_tools()
    assert result == []


def test_build_mock_tools_invalid_json_returns_empty(tmp_path, monkeypatch):
    bad_file = tmp_path / "mcp-mock.json"
    bad_file.write_text("NOT VALID JSON {{{")
    import app.mcp_tools as mcp_tools_module
    monkeypatch.setattr(mcp_tools_module, "_MOCK_FILE", bad_file)
    result = mcp_tools_module._build_mock_tools()
    assert result == []


# ---------------------------------------------------------------------------
# get_mcp_tools (IBD_TESTING mode)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_mcp_tools_returns_mock_tools_in_test_mode():
    tools = await get_mcp_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0


@pytest.mark.asyncio
async def test_get_mcp_tools_tool_names_are_strings():
    tools = await get_mcp_tools()
    for t in tools:
        assert isinstance(t.name, str)


@pytest.mark.asyncio
async def test_get_mcp_tools_includes_key_tools():
    tools = await get_mcp_tools()
    tool_names = {t.name for t in tools}
    assert "get_material_stock" in tool_names
    assert "run_atp_check" in tool_names
    assert "propose_corrective_actions" in tool_names


@pytest.mark.asyncio
async def test_mock_tool_is_callable():
    """Mock tools must be invokable and return JSON string."""
    tools = await get_mcp_tools()
    stock_tool = next((t for t in tools if t.name == "get_material_stock"), None)
    assert stock_tool is not None
    result = await stock_tool.ainvoke({"material": "FG-001", "plant": "1010"})
    # Should return a JSON string (the mock_response)
    parsed = json.loads(result)
    assert "material" in parsed
