"""
J.A.R.V.I.S. 3.0 — Module 3: Email Agent
Handles reading, sending, replying, and labeling Gmail messages.
"""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from googleapiclient.discovery import build

from config.settings import settings
from utils.helpers import get_google_credentials, get_logger, retry, APIError
from llm.claude import chat, extract_json

logger = get_logger("email")


# ─────────────────── Gmail Service ────────────────────────────

def _gmail():
    return build("gmail", "v1", credentials=get_google_credentials())


# ─────────────────── Read Emails ──────────────────────────────

@retry(max_attempts=2)
def get_unread_emails(max_results: int = 10) -> list[dict]:
    """Return list of unread emails with id, subject, from, snippet."""
    service = _gmail()
    result = service.users().messages().list(
        userId="me",
        labelIds=["UNREAD"],
        maxResults=max_results,
    ).execute()

    messages = result.get("messages", [])
    emails = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"].get("headers", [])}
        emails.append({
            "id": msg["id"],
            "threadId": detail.get("threadId"),
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", "unknown"),
            "date": headers.get("Date", ""),
            "snippet": detail.get("snippet", ""),
        })
    return emails


@retry(max_attempts=2)
def get_email_body(message_id: str) -> str:
    """Get the full plain-text body of an email."""
    service = _gmail()
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    def extract_body(payload):
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part["body"].get("data", "")
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            for part in payload["parts"]:
                result = extract_body(part)
                if result:
                    return result
        elif payload.get("mimeType") == "text/plain":
            data = payload["body"].get("data", "")
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return ""

    return extract_body(msg.get("payload", {}))


# ─────────────────── Send / Reply ─────────────────────────────

@retry(max_attempts=2)
def send_email(to: str, subject: str, body: str) -> dict:
    """Send a new email."""
    service = _gmail()
    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    logger.info(f"Email sent: id={sent['id']} to={to}")
    return sent


@retry(max_attempts=2)
def reply_email(message_id: str, thread_id: str, to: str, subject: str, body: str) -> dict:
    """Reply to an existing email thread."""
    service = _gmail()
    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    msg["In-Reply-To"] = message_id
    msg["References"] = message_id
    msg.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(
        userId="me", body={"raw": raw, "threadId": thread_id}
    ).execute()
    logger.info(f"Reply sent: threadId={thread_id}")
    return sent


@retry(max_attempts=2)
def label_email(message_id: str, label_ids: list[str]) -> dict:
    """Apply labels to an email."""
    service = _gmail()
    return service.users().messages().modify(
        userId="me", id=message_id,
        body={"addLabelIds": label_ids}
    ).execute()


# ─────────────────── Natural Language Handler ─────────────────

async def handle_email(user_message: str) -> str:
    """
    Main entrypoint called by the Telegram router.
    Interprets the user's intent and executes the appropriate email action.
    """
    intent_prompt = f"""The user wants to do something with email: "{user_message}"
    
Classify into one of: read_inbox, send_email, reply_email, label_email, summarize_email
Return ONLY the action word."""

    action = chat(user_message, system=intent_prompt, max_tokens=20).strip().lower()
    logger.info(f"Email action: {action}")

    try:
        if action == "read_inbox":
            return await _read_inbox()
        elif action == "send_email":
            return await _compose_and_send(user_message)
        elif action == "summarize_email":
            return await _summarize_latest()
        else:
            return await _read_inbox()
    except Exception as e:
        logger.error(f"Email error: {e}", exc_info=True)
        return f"⚠️ Email error: {e}"


async def _read_inbox() -> str:
    emails = get_unread_emails(max_results=5)
    if not emails:
        return "📬 No unread emails."
    lines = ["📧 *Unread Emails:*\n"]
    for i, e in enumerate(emails, 1):
        lines.append(f"*{i}.* From: `{e['from']}`")
        lines.append(f"   Subject: {e['subject']}")
        lines.append(f"   _{e['snippet'][:100]}..._\n")
    return "\n".join(lines)


async def _compose_and_send(user_message: str) -> str:
    schema = '{"to": "email@example.com", "subject": "string", "body": "string"}'
    data = extract_json(user_message, schema_description="to, subject, body fields", example=schema)
    send_email(data["to"], data["subject"], data["body"])
    return f"✅ Email sent to `{data['to']}` — Subject: _{data['subject']}_"


async def _summarize_latest() -> str:
    emails = get_unread_emails(max_results=3)
    if not emails:
        return "📬 No unread emails to summarize."
    summaries = []
    for e in emails:
        body = get_email_body(e["id"])[:1500]
        summary = chat(body, system="Summarize this email in 2 sentences.", max_tokens=150)
        summaries.append(f"*{e['subject']}*\n{summary}")
    return "📧 *Email Summaries:*\n\n" + "\n\n---\n\n".join(summaries)
