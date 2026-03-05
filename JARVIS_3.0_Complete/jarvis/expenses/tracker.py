"""
J.A.R.V.I.S. 3.0 — Module 5: Expense Manager
Log expenses and query history using Google Sheets as the database.
"""

from datetime import datetime, date
from typing import Optional

from googleapiclient.discovery import build

from config.settings import settings
from utils.helpers import get_google_credentials, get_logger, retry
from llm.claude import extract_json, chat

logger = get_logger("expenses")

# Column order in the Expenses sheet
COLUMNS = ["Date", "Vendor", "Amount", "Category", "Notes", "LoggedAt"]
CATEGORIES = ["food", "transport", "office", "entertainment", "health", "travel", "other"]


# ─────────────────── Sheets Service ───────────────────────────

def _sheets():
    return build("sheets", "v4", credentials=get_google_credentials())


def _range(tab: str = None, cells: str = "A:F") -> str:
    tab = tab or settings.SHEETS_EXPENSE_TAB
    return f"'{tab}'!{cells}"


# ─────────────────── Expense CRUD ─────────────────────────────

@retry(max_attempts=2)
def log_expense(
    vendor: str,
    amount: float,
    category: str,
    notes: str = "",
    expense_date: Optional[str] = None,
) -> dict:
    """Append one expense row to the Google Sheet."""
    service = _sheets()
    row = [
        expense_date or date.today().isoformat(),
        vendor,
        round(amount, 2),
        category.lower(),
        notes,
        datetime.utcnow().isoformat(),
    ]
    result = service.spreadsheets().values().append(
        spreadsheetId=settings.SHEETS_SPREADSHEET_ID,
        range=_range(),
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
    logger.info(f"Expense logged: {vendor} ${amount} ({category})")
    return result


@retry(max_attempts=2)
def get_expenses(limit: int = 50) -> list[dict]:
    """Read all expense rows and return as list of dicts."""
    service = _sheets()
    result = service.spreadsheets().values().get(
        spreadsheetId=settings.SHEETS_SPREADSHEET_ID,
        range=_range(),
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return []

    # First row may be headers — check
    if rows[0][0].lower() == "date":
        rows = rows[1:]

    expenses = []
    for row in rows[-limit:]:
        padded = row + [""] * (len(COLUMNS) - len(row))
        expenses.append({
            "date": padded[0],
            "vendor": padded[1],
            "amount": float(padded[2]) if padded[2] else 0.0,
            "category": padded[3],
            "notes": padded[4],
        })
    return expenses


@retry(max_attempts=2)
def ensure_headers():
    """Create header row if the sheet is empty."""
    service = _sheets()
    result = service.spreadsheets().values().get(
        spreadsheetId=settings.SHEETS_SPREADSHEET_ID,
        range=_range(cells="A1:F1"),
    ).execute()
    if not result.get("values"):
        service.spreadsheets().values().update(
            spreadsheetId=settings.SHEETS_SPREADSHEET_ID,
            range=_range(cells="A1"),
            valueInputOption="USER_ENTERED",
            body={"values": [COLUMNS]},
        ).execute()
        logger.info("Expense sheet headers created.")


# ─────────────────── NLP Parsing ──────────────────────────────

_EXPENSE_SCHEMA = """{
  "action": "log | summary | history",
  "vendor": "string",
  "amount": 0.00,
  "category": "food | transport | office | entertainment | health | travel | other",
  "notes": "string",
  "date": "YYYY-MM-DD"
}"""

_EXPENSE_SYSTEM = f"""Today is {date.today().isoformat()}.
Extract expense information from the user's message.
Return ONLY JSON:
{_EXPENSE_SCHEMA}
For summary/history requests, return only action field.
No markdown, no explanation — ONLY the JSON object."""


def parse_expense(user_message: str) -> dict:
    return extract_json(user_message, schema_description=_EXPENSE_SCHEMA)


# ─────────────────── Summary / Analytics ──────────────────────

def compute_summary(expenses: list[dict]) -> str:
    if not expenses:
        return "No expenses recorded yet."

    total = sum(e["amount"] for e in expenses)
    by_category: dict[str, float] = {}
    for e in expenses:
        cat = e["category"] or "other"
        by_category[cat] = by_category.get(cat, 0.0) + e["amount"]

    lines = [f"💰 *Expense Summary ({len(expenses)} entries)*\n"]
    lines.append(f"*Total:* ${total:,.2f}\n")
    lines.append("*By Category:*")
    for cat, amt in sorted(by_category.items(), key=lambda x: -x[1]):
        pct = (amt / total * 100) if total else 0
        lines.append(f"  • {cat.capitalize()}: ${amt:,.2f} ({pct:.0f}%)")
    return "\n".join(lines)


def recent_expenses_text(expenses: list[dict], limit: int = 10) -> str:
    recent = expenses[-limit:]
    if not recent:
        return "No recent expenses."
    lines = [f"📋 *Last {len(recent)} Expenses:*\n"]
    for e in reversed(recent):
        lines.append(
            f"• `{e['date']}` — *{e['vendor']}* — ${e['amount']:.2f} ({e['category']})"
        )
        if e.get("notes"):
            lines.append(f"  _{e['notes']}_")
    return "\n".join(lines)


# ─────────────────── Natural Language Handler ─────────────────

async def handle_expense(user_message: str) -> str:
    """Main entrypoint called by the Telegram router."""
    try:
        ensure_headers()
        data = parse_expense(user_message)
        action = data.get("action", "log")

        if action == "log":
            if not data.get("vendor") or not data.get("amount"):
                return "❓ Please include the vendor and amount. E.g.: _Spent $25 at Starbucks for coffee_"
            log_expense(
                vendor=data["vendor"],
                amount=float(data["amount"]),
                category=data.get("category", "other"),
                notes=data.get("notes", ""),
                expense_date=data.get("date"),
            )
            return (
                f"✅ *Expense Logged*\n"
                f"🏪 Vendor: {data['vendor']}\n"
                f"💵 Amount: ${float(data['amount']):.2f}\n"
                f"🏷️ Category: {data.get('category', 'other')}\n"
                f"📅 Date: {data.get('date', date.today().isoformat())}"
            )

        elif action == "summary":
            expenses = get_expenses()
            return compute_summary(expenses)

        elif action == "history":
            expenses = get_expenses()
            return recent_expenses_text(expenses)

        else:
            return "❓ I can log expenses, show a summary, or show history. What would you like?"

    except Exception as e:
        logger.error(f"Expense error: {e}", exc_info=True)
        return f"⚠️ Expense error: {e}"
