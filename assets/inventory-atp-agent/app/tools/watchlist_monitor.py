"""Watchlist Monitor — R-03 Protect Service Level.

Monitors a list of material/plant entries against safety stock thresholds
and returns structured breach alerts.
"""

import logging

from tools.get_material_stock import get_material_stock

logger = logging.getLogger(__name__)


async def watchlist_monitor(
    watchlist: list,
    mcp_tools: dict = None,
) -> list:
    """Monitor materials against safety stock thresholds.

    Args:
        watchlist: List of dicts with keys:
            - material (str)
            - plant (str)
            - safety_stock_threshold (float)
            - sla_date (str, YYYY-MM-DD)
        mcp_tools: Dict mapping tool name -> callable

    Returns:
        List of alert dicts for materials in breach.
    """
    alerts = []
    for entry in watchlist:
        material = entry.get("material", "")
        plant = entry.get("plant", "")
        threshold = float(entry.get("safety_stock_threshold", 0))
        sla_date = entry.get("sla_date", "")
        try:
            stock_data = await get_material_stock(material, plant, mcp_tools=mcp_tools)
            if stock_data.get("error"):
                continue
            current_stock = float(stock_data.get("unrestricted_stock", 0))
            if current_stock < threshold:
                deficit_pct = ((threshold - current_stock) / threshold * 100) if threshold > 0 else 100
                if deficit_pct >= 50:
                    severity = "HIGH"
                elif deficit_pct >= 20:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"
                alerts.append({
                    "alert_type": "SAFETY_STOCK_BREACH",
                    "material": material,
                    "plant": plant,
                    "current_stock": current_stock,
                    "threshold": threshold,
                    "sla_date": sla_date,
                    "breach_severity": severity,
                    "deficit_pct": round(deficit_pct, 1),
                })
                logger.warning(
                    "Safety stock breach | material=%s plant=%s current=%.1f threshold=%.1f severity=%s",
                    material, plant, current_stock, threshold, severity,
                )
        except Exception as exc:
            logger.warning("watchlist_monitor error | material=%s plant=%s error=%s", material, plant, str(exc))
    return alerts
