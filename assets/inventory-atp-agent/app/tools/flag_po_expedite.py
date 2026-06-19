"""Tool 9: Flag PO Expedite — R-05 Execute With Approval.

Generates a structured expedite request payload for buyer action.
No direct OData PO expedite API exists; this tool creates an action card
that the buyer must action manually.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def flag_po_expedite(
    purchase_order: str,
    purchase_order_item: str,
    expedite_reason: str,
    buyer_note: str = "",
    approved_by: str = "user",
    mcp_tools: dict = None,
) -> dict:
    """Generate a structured PO expedite request for buyer action.

    Args:
        purchase_order: SAP purchase order number
        purchase_order_item: PO line item number
        expedite_reason: Reason for expediting (e.g. 'STOCK_SHORTFALL')
        buyer_note: Optional note to the buyer
        approved_by: User ID who confirmed the action
        mcp_tools: Not used (no direct expedite API available)

    Returns:
        Structured expedite payload with status PENDING_BUYER_ACTION.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        result = {
            "purchase_order": purchase_order,
            "purchase_order_item": purchase_order_item,
            "expedite_reason": expedite_reason,
            "buyer_note": buyer_note,
            "flagged_at": timestamp,
            "status": "PENDING_BUYER_ACTION",
        }
        logger.info(
            "M5.achieved: execution_complete | action=FLAG_PO_EXPEDITE document=%s approved_by=%s timestamp=%s",
            purchase_order, approved_by, timestamp,
        )
        return result
    except Exception as exc:
        logger.warning(
            "M5.missed: execution_not_completed | action=FLAG_PO_EXPEDITE reason=%s approved_by=%s",
            str(exc), approved_by,
        )
        return {
            "error": True,
            "error_code": "PO_EXPEDITE_FAILED",
            "error_reason": str(exc),
            "purchase_order": purchase_order,
        }
