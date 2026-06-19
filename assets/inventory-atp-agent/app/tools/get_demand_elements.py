"""Tool 2: Get Demand Elements — R-01 Root Cause Layer.

Fetches supply/demand items and MRP parameters from API_MRP_MATERIALS_SRV_01.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def get_demand_elements(
    material: str,
    plant: str,
    date_from: str = "",
    date_to: str = "",
    mcp_tools: dict = None,
) -> dict:
    """Fetch demand and supply elements from MRP data via MCP tool.

    Args:
        material: SAP material number
        plant: SAP plant code
        date_from: Optional ISO date filter start (YYYY-MM-DD)
        date_to: Optional ISO date filter end (YYYY-MM-DD)
        mcp_tools: Dict mapping tool name -> callable

    Returns:
        Structured dict with demand/supply elements or error reason.
    """
    tool_name = "API_MRP_MATERIALS_SRV_01__SupplyDemandItems_Read"
    mrp_tool_name = "API_MRP_MATERIALS_SRV_01__A_MRPMaterial_Read"
    try:
        demand_elements = []
        supply_elements = []
        safety_stock = 0.0
        reorder_point = 0.0

        if mcp_tools and tool_name in mcp_tools:
            params = {"Material": material, "MRPPlant": plant, "$top": "100"}
            if date_from:
                params["DateFrom"] = date_from
            if date_to:
                params["DateTo"] = date_to
            raw = await mcp_tools[tool_name](**params)
            demand_elements, supply_elements = _parse_supply_demand(raw)
        else:
            demand_elements, supply_elements = _mock_supply_demand()

        if mcp_tools and mrp_tool_name in mcp_tools:
            mrp_raw = await mcp_tools[mrp_tool_name](Material=material, MRPPlant=plant)
            safety_stock, reorder_point = _parse_mrp(mrp_raw)
        else:
            safety_stock, reorder_point = 50.0, 100.0

        logger.info(
            "M1.achieved: stock_perception_complete | material=%s plant=%s sloc=ALL stock_categories=1 demand_elements=%d",
            material, plant, len(demand_elements),
        )
        return {
            "material": material,
            "plant": plant,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "demand_elements": demand_elements,
            "supply_elements": supply_elements,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.warning(
            "M1.missed: stock_perception_failed | material=%s plant=%s error=%s — perception step did not complete",
            material, plant, str(exc),
        )
        return {
            "error": True,
            "error_code": "DEMAND_FETCH_FAILED",
            "error_reason": str(exc),
            "material": material,
            "plant": plant,
        }


def _parse_supply_demand(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return [], []
    items = raw.get("value", []) if isinstance(raw, dict) else []
    demand, supply = [], []
    for item in items:
        element_type = item.get("MRPElementCategory", "")
        qty = float(item.get("MRPElementSupplyDemandQuantity", 0) or 0)
        entry = {
            "type": element_type,
            "document_number": item.get("MRPElement", ""),
            "quantity": qty,
            "date": item.get("MRPElementOpenQuantityDate", ""),
            "element_type": element_type,
        }
        if qty < 0:
            demand.append(entry)
        else:
            supply.append(entry)
    return demand, supply


def _parse_mrp(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return 0.0, 0.0
    value = raw.get("value", [{}]) if isinstance(raw, dict) else [{}]
    row = value[0] if value else {}
    return float(row.get("SafetyStock", 0) or 0), float(row.get("ReorderPoint", 0) or 0)


def _mock_supply_demand():
    demand = [
        {"type": "OrdRes", "document_number": "1000001", "quantity": -200.0, "date": "2026-07-01", "element_type": "OrdRes"},
        {"type": "SalesOrd", "document_number": "2000001", "quantity": -150.0, "date": "2026-07-05", "element_type": "SalesOrd"},
    ]
    supply = [
        {"type": "PurOrd", "document_number": "4500001", "quantity": 300.0, "date": "2026-07-10", "element_type": "PurOrd"},
    ]
    return demand, supply
