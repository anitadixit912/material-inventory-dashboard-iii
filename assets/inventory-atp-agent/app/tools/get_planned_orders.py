"""Tool 4: Get Planned Orders — R-04 Supply Side.

Reads open planned orders from API_PLANNED_ORDERS MCP tool.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def get_planned_orders(
    material: str,
    plant: str,
    date_from: str = "",
    date_to: str = "",
    mcp_tools: dict = None,
) -> dict:
    """Fetch planned orders for a material/plant from S/4HANA via MCP.

    Args:
        material: SAP material number
        plant: SAP plant code
        date_from: Optional filter — basic start date (YYYY-MM-DD)
        date_to: Optional filter — basic end date (YYYY-MM-DD)
        mcp_tools: Dict mapping tool name -> callable

    Returns:
        Structured dict with list of planned orders or error reason.
    """
    tool_name = "API_PLANNED_ORDERS__A_PlannedOrder_Read"
    try:
        if mcp_tools and tool_name in mcp_tools:
            params = {
                "Material": material,
                "ProductionPlant": plant,
                "$top": "100",
            }
            if date_from:
                params["PlannedOrderOpeningDate"] = date_from
            raw = await mcp_tools[tool_name](**params)
            orders = _parse_orders(raw)
        else:
            orders = _mock_orders(material, plant)

        return {
            "material": material,
            "plant": plant,
            "planned_orders": orders,
            "count": len(orders),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.warning("get_planned_orders failed | material=%s plant=%s error=%s", material, plant, str(exc))
        return {
            "error": True,
            "error_code": "PLANNED_ORDERS_FETCH_FAILED",
            "error_reason": str(exc),
            "material": material,
            "plant": plant,
        }


def _parse_orders(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    items = raw.get("value", []) if isinstance(raw, dict) else []
    orders = []
    for item in items:
        orders.append({
            "planned_order": item.get("PlannedOrder", ""),
            "order_type": item.get("PlannedOrderType", ""),
            "quantity": float(item.get("PlannedOrderPlannedQuantity", 0) or 0),
            "basic_start_date": item.get("PlannedOrderOpeningDate", ""),
            "basic_end_date": item.get("PlannedOrderEndDate", ""),
            "procurement_type": item.get("MRPType", ""),
            "conversion_eligible": True,
        })
    return orders


def _mock_orders(material, plant):
    return [
        {
            "planned_order": "0000100001",
            "order_type": "ZP01",
            "quantity": 500.0,
            "basic_start_date": "2026-07-01",
            "basic_end_date": "2026-07-10",
            "procurement_type": "X",
            "conversion_eligible": True,
        },
        {
            "planned_order": "0000100002",
            "order_type": "ZP01",
            "quantity": 250.0,
            "basic_start_date": "2026-07-15",
            "basic_end_date": "2026-07-20",
            "procurement_type": "X",
            "conversion_eligible": True,
        },
    ]
