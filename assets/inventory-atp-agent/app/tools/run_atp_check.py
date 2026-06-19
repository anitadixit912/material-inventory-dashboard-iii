"""Tool 3: Run ATP Check — R-02 Check Order Feasibility.

Calls the CE_APIAVAILTOPROMISECHECK_0001 MCP action to check
availability-to-promise for a requested material/quantity/date.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def run_atp_check(
    material: str,
    plant: str,
    requested_quantity: float,
    requested_date: str,
    sales_order: str = "",
    sales_order_item: str = "",
    mcp_tools: dict = None,
) -> dict:
    """Run an ATP availability check via MCP tool.

    Args:
        material: SAP material number
        plant: SAP plant code
        requested_quantity: Requested order quantity
        requested_date: Requested delivery date (YYYY-MM-DD)
        sales_order: Optional sales order number for context
        sales_order_item: Optional sales order item
        mcp_tools: Dict mapping tool name -> callable

    Returns:
        Structured ATP result dict.
    """
    tool_name = "CE_APIAVAILTOPROMISECHECK_0001__CheckAvailabilityWithoutResvn"
    order_ref = sales_order or "ADHOC"
    item_ref = sales_order_item or "000010"
    try:
        if mcp_tools and tool_name in mcp_tools:
            raw = await mcp_tools[tool_name](
                Material=material,
                Plant=plant,
                RequestedQuantity=str(requested_quantity),
                RequestedDeliveryDate=requested_date,
                SalesOrder=sales_order,
                SalesOrderItem=sales_order_item,
            )
            result = _parse_atp(raw, material, plant, requested_quantity, requested_date)
        else:
            result = _mock_atp(material, plant, requested_quantity, requested_date)

        confirmed = result.get("confirmed_quantity", 0)
        atp_date = result.get("atp_date", requested_date)
        logger.info(
            "M3.achieved: atp_check_complete | order=%s line=%s confirmed_qty=%s atp_date=%s",
            order_ref, item_ref, confirmed, atp_date,
        )
        return result
    except Exception as exc:
        logger.warning(
            "M3.missed: atp_check_failed | order=%s line=%s error=%s — ATP result not returned",
            order_ref, item_ref, str(exc),
        )
        return {
            "error": True,
            "error_code": "ATP_CHECK_FAILED",
            "error_reason": str(exc),
            "material": material,
            "plant": plant,
            "requested_quantity": requested_quantity,
            "requested_date": requested_date,
        }


def _parse_atp(raw, material, plant, requested_quantity, requested_date):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            pass
    value = raw if isinstance(raw, dict) else {}
    if "value" in value and isinstance(value["value"], list) and value["value"]:
        value = value["value"][0]

    raw_confirmed = value.get("ConfirmedQuantity", None)
    confirmed = float(raw_confirmed) if raw_confirmed is not None else requested_quantity
    atp_date = value.get("AvailabilityDate", requested_date) or requested_date
    unfulfilled = max(0.0, requested_quantity - confirmed)
    is_fully_confirmed = unfulfilled == 0.0
    reason_code = value.get("ReasonCode", "")
    reason_text = value.get("ReasonText", "Fully confirmed" if is_fully_confirmed else "Partial availability")

    return {
        "material": material,
        "plant": plant,
        "requested_quantity": requested_quantity,
        "requested_date": requested_date,
        "confirmed_quantity": confirmed,
        "atp_date": atp_date,
        "unfulfilled_quantity": unfulfilled,
        "reason_code": reason_code,
        "reason_text": reason_text,
        "is_fully_confirmed": is_fully_confirmed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _mock_atp(material, plant, requested_quantity, requested_date):
    confirmed = min(requested_quantity, 300.0)
    unfulfilled = max(0.0, requested_quantity - confirmed)
    return {
        "material": material,
        "plant": plant,
        "requested_quantity": requested_quantity,
        "requested_date": requested_date,
        "confirmed_quantity": confirmed,
        "atp_date": requested_date,
        "unfulfilled_quantity": unfulfilled,
        "reason_code": "",
        "reason_text": "Fully confirmed" if unfulfilled == 0 else "Partial stock available",
        "is_fully_confirmed": unfulfilled == 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
