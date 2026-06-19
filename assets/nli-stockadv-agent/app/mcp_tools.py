"""MCP tool loader.

In test mode (IBD_TESTING=1): reads mcp-mock.json and returns LangChain
StructuredTool instances built from the mock data — no network calls.

In production (CF): returns empty list — MCP tools are not used on CF.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from pydantic import create_model
from langchain_core.tools import StructuredTool

from util import enhance_tool_description, enhance_tool_name, call_mcp_tool_with_retry

logger = logging.getLogger(__name__)

# mcp-mock.json lives at the asset root (one level above app/)
_MOCK_FILE = Path(__file__).parent.parent / "mcp-mock.json"

# Tool cache
_tool_cache: Optional[tuple[list, float]] = None
_CACHE_TTL = float(os.environ.get("MCP_TOOL_CACHE_TTL", "60.0"))


def _build_mock_tools() -> list:
    """Build LangChain StructuredTool instances from mcp-mock.json."""
    if not _MOCK_FILE.exists():
        return []

    try:
        mock_data = json.loads(_MOCK_FILE.read_text())
    except Exception:
        logger.warning("Failed to parse mcp-mock.json at %s — returning empty tool list", _MOCK_FILE, exc_info=True)
        return []

    tools = []

    from pydantic import Field, create_model

    for _server_slug, server in mock_data.get("servers", {}).items():
        for tool_name, tool_def in server.get("tools", {}).items():
            description = tool_def.get("description", "")
            mock_response = tool_def.get("mock_response", {})
            input_schema = tool_def.get("input_schema", {})

            props = input_schema.get("properties", {})
            required_fields = set(input_schema.get("required", []))
            field_definitions: dict = {}
            for field_name, field_info in props.items():
                json_type = field_info.get("type", "string")
                if json_type == "integer":
                    python_type = int
                elif json_type == "number":
                    python_type = float
                elif json_type == "boolean":
                    python_type = bool
                else:
                    python_type = str

                if field_name in required_fields:
                    field_definitions[field_name] = (python_type, Field(description=field_info.get("description", "")))
                else:
                    field_definitions[field_name] = (python_type, Field(default=None, description=field_info.get("description", "")))

            args_schema = create_model(f"{tool_name}_args", **field_definitions) if field_definitions else create_model(f"{tool_name}_args")
            _response = json.dumps(mock_response)

            async def _coroutine(_resp=_response, **kwargs) -> str:
                return _resp

            tools.append(
                StructuredTool(
                    name=tool_name,
                    description=description,
                    args_schema=args_schema,
                    coroutine=_coroutine,
                )
            )

    logger.info("Loaded %d mock MCP tool(s) from %s", len(tools), _MOCK_FILE)
    return tools


async def get_mcp_tools(use_cache: bool = True) -> list:
    """Return LangChain-compatible MCP tools.

    In test mode (IBD_TESTING=1): returns mock tools from mcp-mock.json.
    In production (CF): returns empty list.
    """
    if os.environ.get("IBD_TESTING") == "1":
        return _build_mock_tools()

    return []
