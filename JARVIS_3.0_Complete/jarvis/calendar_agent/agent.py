"""
J.A.R.V.I.S. 3.0 — Module 4: Calendar Agent
Create, read, update, delete Google Calendar events via natural language.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

from config.settings import settings
from utils.helpers import get_google_credentials, get_logger, retry
from llm.claude import chat, extract_json

logger = get_logger("calendar")

TZ = ZoneInfo(settings.TIMEZONE)


# ─────────────────── Calendar Service ─────────────────────────

def _cal():
    return build("calendar", "v3", credentials=get_google_credentials())


# ─────────────────── CRUD Operations ──────────────────────────

@retry(max_attempts=2)
def get_events(days_ahead: int = 7, max_results: int = 10) -> list[dict]:
    """Return upcoming calendar events."""
    service = _cal()
    now = datetime.now(tz=timezone.utc).isoformat()
    future = (datetime.now(tz=timezone.utc) + timedelta(days=days_ahead)).isoformat()
    result = service.events().list(
        calendarId="primary",
        timeMin=now,
        timeMax=future,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return result.get("items", [])


@retry(max_attempts=2)
def create_event(
    title: str,
    start_dt: str,
    end_dt: str,
    description: str = "",
    attendees: list[str] = None,
) -> dict:
    """Create a new calendar event."""
    service = _cal()
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt, "timeZone": settings.TIMEZONE},
        "end":   {"dateTime": end_dt,   "timeZone": settings.TIMEZONE},
    }
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]
    event = service.events().insert(
        calendarId="primary", body=body, sendUpdates="all"
    ).execute()
    logger.info(f"Event created: {event['id']} — {title}")
    return event


@retry(max_attempts=2)
def update_event(event_id: str, updates: dict) -> dict:
    """Patch an existing event with new fields."""
    service = _cal()
    event = service.events().patch(
        calendarId="primary", eventId=event_id, body=updates, sendUpdates="all"
    ).execute()
    logger.info(f"Event updated: {event_id}")
    return event


@retry(max_attempts=2)
def delete_event(event_id: str):
    """Delete a calendar event."""
    _cal().events().delete(
        calendarId="primary", eventId=event_id, sendUpdates="all"
    ).execute()
    logger.info(f"Event deleted: {event_id}")


# ─────────────────── NLP Event Parsing ────────────────────────

_EVENT_SCHEMA = """
{
  "action": "create | list | delete | update",
  "title": "Event title",
  "startDateTime": "2026-03-06T14:00:00",
  "endDateTime": "2026-03-06T15:00:00",
  "description": "Optional description",
  "attendees": ["email1@example.com"],
  "days_ahead": 7
}
"""

_EVENT_SYSTEM = f"""Today is {datetime.now(tz=TZ).strftime('%A, %Y-%m-%d %H:%M')}.
Extract calendar event details from the user's message.
Return ONLY JSON matching this schema:
{_EVENT_SCHEMA}
For 'list' actions, only return action and days_ahead.
Use ISO 8601 for all datetimes. Infer reasonable end times (1 hour default).
No explanation — ONLY JSON."""


def parse_event_request(user_message: str) -> dict:
    return extract_json(
        user_message,
        schema_description=_EVENT_SCHEMA,
    )


# ─────────────────── Natural Language Handler ─────────────────

async def handle_calendar(user_message: str) -> str:
    """Main entrypoint called by the Telegram router."""
    try:
        data = parse_event_request(user_message)
        action = data.get("action", "list")

        if action == "create":
            return await _create(data)
        elif action == "list":
            return await _list_events(data.get("days_ahead", 7))
        elif action == "delete":
            return await _delete(data)
        elif action == "update":
            return await _update(data)
        else:
            return await _list_events(7)

    except Exception as e:
        logger.error(f"Calendar error: {e}", exc_info=True)
        return f"⚠️ Calendar error: {e}"


async def _list_events(days: int) -> str:
    events = get_events(days_ahead=days)
    if not events:
        return f"📅 No events in the next {days} days."
    lines = [f"📅 *Upcoming Events ({days} days):*\n"]
    for ev in events:
        start = ev["start"].get("dateTime", ev["start"].get("date", ""))
        # Format datetime nicely
        try:
            dt = datetime.fromisoformat(start)
            start_fmt = dt.strftime("%a %b %d, %I:%M %p")
        except Exception:
            start_fmt = start
        lines.append(f"• *{ev.get('summary', 'No title')}*")
        lines.append(f"  🕐 {start_fmt}")
        if ev.get("description"):
            lines.append(f"  _{ev['description'][:80]}_")
    return "\n".join(lines)


async def _create(data: dict) -> str:
    event = create_event(
        title=data.get("title", "New Event"),
        start_dt=data["startDateTime"],
        end_dt=data["endDateTime"],
        description=data.get("description", ""),
        attendees=data.get("attendees", []),
    )
    start_fmt = data.get("startDateTime", "")[:16].replace("T", " ")
    return (
        f"✅ *Event Created:*\n"
        f"📌 {event.get('summary')}\n"
        f"🕐 {start_fmt}\n"
        f"🔗 [Open in Calendar]({event.get('htmlLink', '')})"
    )


async def _delete(data: dict) -> str:
    # Find event by title from upcoming events
    events = get_events(days_ahead=30)
    title_query = data.get("title", "").lower()
    matched = [e for e in events if title_query in e.get("summary", "").lower()]
    if not matched:
        return f"❌ No event found matching: _{data.get('title')}_"
    delete_event(matched[0]["id"])
    return f"🗑️ Deleted event: *{matched[0].get('summary')}*"


async def _update(data: dict) -> str:
    events = get_events(days_ahead=30)
    title_query = data.get("title", "").lower()
    matched = [e for e in events if title_query in e.get("summary", "").lower()]
    if not matched:
        return f"❌ No event found matching: _{data.get('title')}_"
    updates = {}
    if data.get("startDateTime"):
        updates["start"] = {"dateTime": data["startDateTime"], "timeZone": settings.TIMEZONE}
    if data.get("endDateTime"):
        updates["end"] = {"dateTime": data["endDateTime"], "timeZone": settings.TIMEZONE}
    if data.get("description"):
        updates["description"] = data["description"]
    update_event(matched[0]["id"], updates)
    return f"✏️ Updated event: *{matched[0].get('summary')}*"
