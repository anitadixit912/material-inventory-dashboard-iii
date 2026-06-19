"""Tool 5: Propose Corrective Actions — R-04 Simulate and Rank Options.

Derives and ranks up to 4 corrective options based on supply/demand context.
"""

import logging
from datetime import datetime, timezone

from tools.get_planned_orders import get_planned_orders
from tools.get_demand_elements import get_demand_elements

logger = logging.getLogger(__name__)


async def propose_corrective_actions(
    material: str,
    plant: str,
    shortfall_quantity: float,
    required_date: str,
    mcp_tools: dict = None,
) -> dict:
    """Simulate and rank corrective action options for a supply shortfall.

    Args:
        material: SAP material number
        plant: SAP plant code
        shortfall_quantity: Unfulfilled quantity to cover
        required_date: Required fulfillment date (YYYY-MM-DD)
        mcp_tools: Dict mapping tool name -> callable

    Returns:
        Structured dict with ranked options list.
    """
    try:
        planned = await get_planned_orders(material, plant, mcp_tools=mcp_tools)
        demand = await get_demand_elements(material, plant, mcp_tools=mcp_tools)

        orders = planned.get("planned_orders", [])
        options = []

        # Option A — Planned Order Conversion
        eligible = [o for o in orders if o.get("conversion_eligible") and o.get("quantity", 0) > 0]
        if eligible:
            best = eligible[0]
            end_date = best.get("basic_end_date", required_date)
            lead_days = _days_between(required_date, end_date)
            options.append({
                "rank": 1,
                "type": "PLANNED_ORDER_CONVERSION",
                "description": f"Convert planned order {best['planned_order']} ({best['quantity']} {material}) to a production/process order.",
                "estimated_lead_days": max(0, lead_days),
                "quantity_covered": min(best["quantity"], shortfall_quantity),
                "trade_offs": "Requires production capacity; lead time depends on basic end date.",
                "requires_approval": True,
            })

        # Option B — Stock Transport Order
        options.append({
            "rank": 2,
            "type": "STOCK_TRANSPORT_ORDER",
            "description": f"Create a Stock Transport Order to transfer {shortfall_quantity} {material} from a supplying plant.",
            "estimated_lead_days": 3,
            "quantity_covered": shortfall_quantity,
            "trade_offs": "Requires available stock at supplying plant and transport lane setup.",
            "requires_approval": True,
        })

        # Option C — PIR Adjustment
        demand_items = demand.get("demand_elements", [])
        pir_items = [d for d in demand_items if "PIR" in d.get("type", "") or "IndReq" in d.get("type", "")]
        if pir_items:
            options.append({
                "rank": 3,
                "type": "PIR_ADJUSTMENT",
                "description": f"Reduce lower-priority planned independent requirements to free {shortfall_quantity} units of supply.",
                "estimated_lead_days": 0,
                "quantity_covered": shortfall_quantity,
                "trade_offs": "Reduces planned demand; may affect future forecast accuracy.",
                "requires_approval": True,
            })

        # Option D — Partial Fulfillment
        options.append({
            "rank": len(options) + 1,
            "type": "PARTIAL_FULFILLMENT",
            "description": f"Fulfill available confirmed quantity now; backorder remaining {shortfall_quantity} units.",
            "estimated_lead_days": 7,
            "quantity_covered": shortfall_quantity,
            "trade_offs": "Customer receives partial delivery; remaining qty fulfilled on next available date.",
            "requires_approval": True,
        })

        # Sort by lead days
        options.sort(key=lambda x: x["estimated_lead_days"])
        for i, opt in enumerate(options, 1):
            opt["rank"] = i

        top = options[0] if options else {}
        logger.info(
            "M4.achieved: options_simulated | material=%s options_count=%d top_option=%s estimated_lead_days=%d",
            material, len(options), top.get("type", "N/A"), top.get("estimated_lead_days", 0),
        )
        return {
            "material": material,
            "plant": plant,
            "shortfall_quantity": shortfall_quantity,
            "required_date": required_date,
            "options": options,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.warning(
            "M4.missed: options_not_simulated | material=%s reason=%s — ranked options not generated",
            material, str(exc),
        )
        return {
            "error": True,
            "error_code": "OPTIONS_SIMULATION_FAILED",
            "error_reason": str(exc),
            "material": material,
            "plant": plant,
        }


def _days_between(date_a: str, date_b: str) -> int:
    """Return days from date_a to date_b. Negative if date_b is earlier."""
    try:
        from datetime import datetime
        fmt = "%Y-%m-%d"
        return (datetime.strptime(date_b, fmt) - datetime.strptime(date_a, fmt)).days
    except Exception:
        return 5
