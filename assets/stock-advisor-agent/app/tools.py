"""
Stock data tools for the Stock Advisor Agent.
These tools query the CAP StockService to retrieve live material stock data.
"""
import logging
import os
import urllib.request
import urllib.parse
import json
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

CAP_BASE_URL = os.environ.get("CAP_SERVICE_URL", "http://localhost:4004")


def _fetch(path: str) -> dict:
    """Simple synchronous HTTP GET against the CAP service."""
    url = f"{CAP_BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


@tool
def get_atrisk_materials() -> str:
    """
    Retrieve the list of materials that are nearly out of stock.
    Returns each material's number, description, plant, storage location,
    current stock quantity, base unit, reorder point, safety stock, and risk reason.
    Risk reasons: REORDER_POINT_BREACH | SAFETY_STOCK_PCT_BREACH | BOTH
    """
    try:
        data = _fetch("/stock/MaterialStockView")
        items = [r for r in data.get("value", []) if r.get("StockStatus") == "NEARLY_OUT_OF_STOCK"]
        if not items:
            return "No at-risk materials found."
        lines = []
        for m in items:
            risk = {
                "REORDER_POINT_BREACH": "Below Reorder Point",
                "SAFETY_STOCK_PCT_BREACH": "Below Safety Stock %",
                "BOTH": "Critical – Below Reorder Point AND Safety Stock %",
            }.get(m.get("RiskReason", ""), m.get("RiskReason", "Unknown"))
            lines.append(
                f"- {m['Material']} ({m.get('MaterialDescription','')}) | "
                f"Plant: {m['Plant']} | Loc: {m['StorageLocation']} | "
                f"Stock: {m['StockQuantity']} {m['BaseUnit']} | "
                f"Reorder Point: {m.get('ReorderPoint',0)} | "
                f"Safety Stock: {m.get('SafetyStock',0)} | "
                f"Risk: {risk}"
            )
        return f"At-risk materials ({len(items)}):\n" + "\n".join(lines)
    except Exception as e:
        logger.exception("get_atrisk_materials failed")
        return f"Error fetching at-risk materials: {e}"


@tool
def get_sufficient_materials() -> str:
    """
    Retrieve the list of materials that have sufficient stock levels.
    Returns each material's number, description, plant, storage location,
    current stock quantity and base unit.
    """
    try:
        data = _fetch("/stock/MaterialStockView")
        items = [r for r in data.get("value", []) if r.get("StockStatus") == "SUFFICIENT"]
        if not items:
            return "No materials with sufficient stock found."
        lines = [
            f"- {m['Material']} ({m.get('MaterialDescription','')}) | "
            f"Plant: {m['Plant']} | Loc: {m['StorageLocation']} | "
            f"Stock: {m['StockQuantity']} {m['BaseUnit']}"
            for m in items
        ]
        return f"Sufficient stock materials ({len(items)}):\n" + "\n".join(lines)
    except Exception as e:
        logger.exception("get_sufficient_materials failed")
        return f"Error fetching sufficient materials: {e}"


@tool
def get_stock_summary() -> str:
    """
    Get a high-level summary of current stock health:
    total materials, how many are sufficient, how many are nearly out of stock,
    and a breakdown by risk reason.
    """
    try:
        data = _fetch("/stock/MaterialStockView")
        all_items   = data.get("value", [])
        sufficient  = [r for r in all_items if r.get("StockStatus") == "SUFFICIENT"]
        at_risk     = [r for r in all_items if r.get("StockStatus") == "NEARLY_OUT_OF_STOCK"]
        both_breach = [r for r in at_risk   if r.get("RiskReason") == "BOTH"]
        rop_only    = [r for r in at_risk   if r.get("RiskReason") == "REORDER_POINT_BREACH"]
        ss_only     = [r for r in at_risk   if r.get("RiskReason") == "SAFETY_STOCK_PCT_BREACH"]
        return (
            f"Stock Summary:\n"
            f"  Total materials: {len(all_items)}\n"
            f"  Sufficient: {len(sufficient)}\n"
            f"  Nearly out of stock: {len(at_risk)}\n"
            f"    - Critical (both breaches): {len(both_breach)}\n"
            f"    - Below reorder point only: {len(rop_only)}\n"
            f"    - Below safety stock % only: {len(ss_only)}"
        )
    except Exception as e:
        logger.exception("get_stock_summary failed")
        return f"Error fetching stock summary: {e}"


@tool
def get_critical_materials_by_plant(plant: str) -> str:
    """
    Retrieve at-risk materials for a specific plant.
    Args:
        plant: The plant code (e.g. '1000', '2000')
    """
    try:
        data = _fetch("/stock/MaterialStockView")
        items = [
            r for r in data.get("value", [])
            if r.get("StockStatus") == "NEARLY_OUT_OF_STOCK"
            and r.get("Plant") == plant
        ]
        if not items:
            return f"No at-risk materials found for plant {plant}."
        lines = [
            f"- {m['Material']} ({m.get('MaterialDescription','')}) | "
            f"Loc: {m['StorageLocation']} | Stock: {m['StockQuantity']} {m['BaseUnit']} | "
            f"Risk: {m.get('RiskReason','')}"
            for m in items
        ]
        return f"At-risk materials in plant {plant} ({len(items)}):\n" + "\n".join(lines)
    except Exception as e:
        logger.exception("get_critical_materials_by_plant failed")
        return f"Error fetching data for plant {plant}: {e}"


STOCK_TOOLS = [
    get_atrisk_materials,
    get_sufficient_materials,
    get_stock_summary,
    get_critical_materials_by_plant,
]
