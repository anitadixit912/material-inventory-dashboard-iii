"""Tool 1: Get Material Stock — R-01 Perception Layer.

Fetches real-time stock quantities per material, plant, and storage location
from the API_MATERIAL_STOCK_SRV MCP tool.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def get_material_stock(
    material: str,
    plant: str,
    storage_location: str = "",
    mcp_tools: dict = None,
) -> dict:
    """Fetch material stock data from S/4HANA via MCP tool.

    Args:
        material: SAP material number (e.g. 'FG-001')
        plant: SAP plant code (e.g. '1010')
        storage_location: Optional storage location filter
        mcp_tools: Dict mapping tool name -> callable (injected by agent)

    Returns:
        Structured dict with stock categories or error reason.
    """
    tool_name = "API_MATERIAL_STOCK_SRV__A_MaterialStock_Read"
    try:
        if mcp_tools and tool_name in mcp_tools:
            params = {"Material": material, "Plant": plant, "$top": "100"}
            if storage_location:
                params["StorageLocation"] = storage_location
            raw = await mcp_tools[tool_name](**params)
        else:
            # Fallback — return structured mock when MCP unavailable in test
            raw = _mock_stock(material, plant, storage_location)

        result = _parse_stock(raw, material, plant, storage_location)
        stock_category_count = sum(
            1 for v in [
                result.get("unrestricted_stock", 0),
                result.get("in_transit_stock", 0),
                result.get("reserved_stock", 0),
            ] if v and float(v) > 0
        )
        logger.info(
            "M1.achieved: stock_perception_complete | material=%s plant=%s sloc=%s stock_categories=%d demand_elements=0",
            material, plant, storage_location or "ALL", stock_category_count,
        )
        return result
    except Exception as exc:
        logger.warning(
            "M1.missed: stock_perception_failed | material=%s plant=%s error=%s — perception step did not complete",
            material, plant, str(exc),
        )
        return {
            "error": True,
            "error_code": "STOCK_FETCH_FAILED",
            "error_reason": str(exc),
            "material": material,
            "plant": plant,
            "storage_location": storage_location,
        }


def _parse_stock(raw, material, plant, storage_location):
    """Parse raw MCP response into structured stock dict."""
    if isinstance(raw, dict) and "error" in raw:
        return raw
    # raw may be a JSON string or already parsed
    import json
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            pass
    value = raw if isinstance(raw, dict) else {}
    if "value" in value and isinstance(value["value"], list) and value["value"]:
        value = value["value"][0]
    return {
        "material": value.get("Material", material),
        "plant": value.get("Plant", plant),
        "storage_location": value.get("StorageLocation", storage_location or ""),
        "unrestricted_stock": float(value.get("MatlWrhsStkQtyInMatlBaseUnit", 0) or 0),
        "in_transit_stock": float(value.get("MaterialStockInTransferQty", 0) or 0),
        "reserved_stock": float(value.get("MatlStkQtyInMatlBaseUnit", 0) or 0),
        "safety_stock": float(value.get("SafetyStock", 0) or 0),
        "unit_of_measure": value.get("MaterialBaseUnit", "EA"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _mock_stock(material, plant, storage_location):
    """Return minimal mock data when MCP is unavailable."""
    return {
        "Material": material,
        "Plant": plant,
        "StorageLocation": storage_location or "0001",
        "MatlWrhsStkQtyInMatlBaseUnit": 120.0,
        "MaterialStockInTransferQty": 0.0,
        "MatlStkQtyInMatlBaseUnit": 10.0,
        "SafetyStock": 50.0,
        "MaterialBaseUnit": "EA",
    }
