"""Tool 6: Create Stock Transport Order — R-05 Execute With Approval (STO Write).

MUST only be called after user has explicitly confirmed the approval card.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def create_stock_transport_order(
    material: str,
    supplying_plant: str,
    receiving_plant: str,
    quantity: float,
    unit: str,
    delivery_date: str,
    approved_by: str = "user",
    mcp_tools: dict = None,
) -> dict:
    """Create a Stock Transport Order in S/4HANA via MCP.

    This tool MUST only be called after explicit user confirmation of the action card.

    Args:
        material: SAP material number
        supplying_plant: Supplying plant code
        receiving_plant: Receiving plant code
        quantity: Transfer quantity
        unit: Unit of measure
        delivery_date: Required delivery date (YYYY-MM-DD)
        approved_by: User ID who confirmed the action
        mcp_tools: Dict mapping tool name -> callable

    Returns:
        Structured dict with STO document number or error.
    """
    tool_name = "CE_STOCKTRANSPORTORDER_0001__Create"
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        if mcp_tools and tool_name in mcp_tools:
            raw = await mcp_tools[tool_name](
                Material=material,
                SupplyingPlant=supplying_plant,
                ReceivingPlant=receiving_plant,
                Quantity=str(quantity),
                BaseUnit=unit,
                DeliveryDate=delivery_date,
            )
            doc_number = _parse_doc_number(raw)
            result = {
                "sto_document_number": doc_number,
                "material": material,
                "supplying_plant": supplying_plant,
                "receiving_plant": receiving_plant,
                "quantity": quantity,
                "unit": unit,
                "delivery_date": delivery_date,
                "status": "CREATED",
                "created_at": timestamp,
            }
            logger.info(
                "M5.achieved: execution_complete | action=CREATE_STO document=%s approved_by=%s timestamp=%s",
                doc_number, approved_by, timestamp,
            )
            return result
        else:
            # MCP tool not yet available
            logger.warning(
                "M5.missed: execution_not_completed | action=CREATE_STO reason=STO_MCP_UNAVAILABLE approved_by=%s",
                approved_by,
            )
            return {
                "error": "STO_MCP_UNAVAILABLE",
                "message": "Stock Transport Order MCP tool not yet configured. Please re-fetch CE_STOCKTRANSPORTORDER_0001 spec.",
            }
    except Exception as exc:
        logger.warning(
            "M5.missed: execution_not_completed | action=CREATE_STO reason=%s approved_by=%s",
            str(exc), approved_by,
        )
        return {
            "error": True,
            "error_code": "STO_CREATE_FAILED",
            "error_reason": str(exc),
        }


def _parse_doc_number(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return "UNKNOWN"
    if isinstance(raw, dict):
        return raw.get("StockTransportOrder", raw.get("DocumentNumber", "UNKNOWN"))
    return "UNKNOWN"
