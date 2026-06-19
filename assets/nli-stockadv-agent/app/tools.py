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
def get_material_stock(material: str) -> str:
    """
    Retrieve stock information for one or more specific materials by their material numbers.
    Use this tool whenever the user asks about specific materials (e.g. 'Check MAT-2001, MAT-2002 and MAT-3001',
    'What is the stock level of MAT-1001?', 'Is MAT-2005 sufficient?').
    IMPORTANT: When multiple material numbers are mentioned, pass them ALL as a comma-separated string
    (e.g. 'MAT-2001,MAT-2002,MAT-3001'). Never call this tool only for the first material and stop —
    always include every material number the user mentioned.
    Args:
        material: One or more material numbers, comma-separated (e.g. 'MAT-2001' or 'MAT-2001,MAT-2002,MAT-3001')
    """
    try:
        # Support comma-separated list of material numbers
        material_list = [m.strip() for m in material.split(",") if m.strip()]
        all_lines = []

        for mat in material_list:
            encoded = urllib.parse.quote(f"Material eq '{mat}'")
            data = _fetch(f"/stock/MaterialStockView?$filter={encoded}")
            items = data.get("value", [])
            if not items:
                all_lines.append(f"No stock record found for material '{mat}'.")
                continue
            for m in items:
                status = m.get("StockStatus", "")
                risk_description = m.get("RiskDescription") or {
                    "REORDER_POINT_BREACH": "Below Reorder Point",
                    "SAFETY_STOCK_PCT_BREACH": "Below Safety Stock threshold",
                    "BOTH": "Below Reorder Point AND Below Safety Stock threshold",
                }.get(m.get("RiskReason", ""), m.get("RiskReason", ""))

                if status == "SUFFICIENT":
                    status_label = "SUFFICIENT"
                elif status == "NEARLY_OUT_OF_STOCK":
                    status_label = "NEARLY OUT OF STOCK"
                else:
                    status_label = status

                risk_line = (
                    f"\n  Risk Reason: {risk_description}"
                    if risk_description and status == "NEARLY_OUT_OF_STOCK"
                    else ""
                )
                all_lines.append(
                    f"Material: {m['Material']} ({m.get('MaterialDescription', '')})\n"
                    f"  Plant: {m['Plant']} | Location: {m['StorageLocation']}\n"
                    f"  Stock: {m['StockQuantity']} {m['BaseUnit']}\n"
                    f"  Reorder Point: {m.get('ReorderPoint', 0)} | Safety Stock: {m.get('SafetyStock', 0)}\n"
                    f"  Status: {status_label}{risk_line}"
                )

        return "\n\n".join(all_lines)
    except Exception as e:
        logger.exception("get_material_stock failed")
        return f"Error fetching stock for material(s) '{material}': {e}"


@tool
def get_atrisk_materials() -> str:
    """
    Retrieve the list of ALL materials that are nearly out of stock.
    Use this only when the user asks for a general overview/list (e.g. 'Show all at-risk materials',
    'What materials need attention?'). Do NOT use this for a specific material lookup.
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
                "BOTH": "Critical - Below Reorder Point AND Safety Stock %",
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
    Retrieve the list of ALL materials that have sufficient stock levels.
    Use this only when the user asks for a general overview/list. Do NOT use this for a specific material lookup.
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


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email notification to the specified recipient.
    Use this tool whenever the user asks to send, draft, or compose an email to someone
    about stock levels, restocking urgency, or material replenishment.
    The agent should first look up the material stock data, then compose a professional
    email using that data before calling this tool.
    Args:
        to: Recipient email address (e.g. 'anita.dixit@sap.com'). If only a name or
            username is given (e.g. 'anita.dixit'), append '@sap.com' automatically.
        subject: A concise subject line for the email.
        body: The full email body text, including stock details and recommended action.
    """
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        # Normalise recipient — append @sap.com if no domain is present
        if "@" not in to:
            to = f"{to.strip()}@sap.com"

        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_password = os.environ.get("SMTP_PASSWORD", "")

        if not smtp_user or not smtp_password:
            logger.warning("SMTP credentials not configured — email not sent.")
            return (
                "⚠️ Email could not be sent: SMTP credentials are not configured.\n"
                f"Would have sent to: {to}\nSubject: {subject}"
            )

        # Build MIME message
        msg = MIMEMultipart("alternative")
        msg["From"] = smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Send via Gmail SMTP with STARTTLS
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to, msg.as_string())

        logger.info("EMAIL SENT | From: %s | To: %s | Subject: %s", smtp_user, to, subject)

        return (
            f"✅ Email successfully sent!\n\n"
            f"**To:** {to}\n"
            f"**Subject:** {subject}\n\n"
            f"**Message:**\n{body}"
        )
    except Exception as e:
        logger.exception("send_email failed")
        return f"❌ Failed to send email to '{to}': {e}"


STOCK_TOOLS = [
    get_material_stock,
    get_atrisk_materials,
    get_sufficient_materials,
    get_stock_summary,
    get_critical_materials_by_plant,
    send_email,
]
