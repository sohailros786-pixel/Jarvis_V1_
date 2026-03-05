"""
J.A.R.V.I.S. 3.0 — Module 2: LLM (Anthropic Claude)
All AI calls go through this module.
"""

import json
import re
from typing import Optional

import anthropic

from config.settings import settings
from utils.helpers import get_logger, retry, ParseError

logger = get_logger("llm")

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

JARVIS_SYSTEM_PROMPT = """You are J.A.R.V.I.S. 3.0 — a highly capable personal AI assistant.
You are concise, precise, and professional. You help with emails, calendar management,
expense tracking, and answering questions from the company knowledge base.

When responding via Telegram, keep answers brief and well-formatted using Markdown.
Use bullet points for lists. Use *bold* for emphasis. Never use HTML tags."""


# ─────────────────────── Core Chat ────────────────────────────

@retry(max_attempts=3, delay=2.0, exceptions=(anthropic.APIStatusError, anthropic.APIConnectionError))
def chat(
    user_message: str,
    system: Optional[str] = None,
    context: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Send a message to Claude and return the text response.

    Args:
        user_message: The user's input text.
        system: Override system prompt (uses JARVIS default if None).
        context: Optional context string prepended to the user message.
        max_tokens: Override max tokens.
    """
    system_prompt = system or JARVIS_SYSTEM_PROMPT
    content = f"{context}\n\n{user_message}" if context else user_message

    logger.info(f"Claude request | tokens_limit={max_tokens or settings.ANTHROPIC_MAX_TOKENS}")

    response = _client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=max_tokens or settings.ANTHROPIC_MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    )
    text = response.content[0].text
    logger.info(f"Claude response | input_tokens={response.usage.input_tokens} output_tokens={response.usage.output_tokens}")
    return text


# ─────────────────── Structured JSON Extraction ───────────────

@retry(max_attempts=2, delay=1.0)
def extract_json(user_message: str, schema_description: str, example: str = "") -> dict:
    """
    Ask Claude to extract structured JSON from natural language.

    Args:
        user_message: Raw user input to parse.
        schema_description: Description of the expected JSON fields.
        example: Optional example JSON string.
    """
    example_block = f"\nExample output:\n{example}" if example else ""
    system = (
        f"You extract structured data from user messages.\n"
        f"Return ONLY valid JSON matching this schema:\n{schema_description}"
        f"{example_block}\n"
        f"No explanation, no markdown fences, no extra text — ONLY the JSON object."
    )

    raw = chat(user_message, system=system, max_tokens=512)

    # Strip any accidental fences
    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}\nRaw: {raw}")
        raise ParseError(f"Could not parse LLM response as JSON: {e}") from e


# ─────────────────── Routing Intent Detection ─────────────────

INTENT_SYSTEM = """Classify the user's intent into exactly one of these categories:
expense, calendar, email, knowledge, faq, tts, general

Rules:
- expense: anything about spending money, payments, receipts, credit card
- calendar: scheduling, meetings, events, reminders, availability
- email: inbox, sending/replying to email, reading messages
- knowledge: company docs, internal info, policies, procedures
- faq: 'how do I', 'what is', general company questions
- tts: /voice prefix, 'speak this', 'read this aloud'
- general: everything else

Respond with ONLY the single category word. No punctuation."""


def detect_intent(message: str) -> str:
    """Return the intent category for a user message."""
    # Fast path: explicit slash commands
    lower = message.lower().strip()
    command_map = {
        "/expense": "expense",
        "/calendar": "calendar",
        "/email": "email",
        "/knowledge": "knowledge",
        "/faq": "faq",
        "/voice": "tts",
        "/help": "help",
    }
    for cmd, intent in command_map.items():
        if lower.startswith(cmd):
            return intent

    intent = chat(message, system=INTENT_SYSTEM, max_tokens=10).strip().lower()
    valid = {"expense", "calendar", "email", "knowledge", "faq", "tts", "general"}
    return intent if intent in valid else "general"


# ─────────────────── Summarization Helper ─────────────────────

def summarize(text: str, max_words: int = 100) -> str:
    """Summarize a long text into a concise response."""
    return chat(
        text,
        system=f"Summarize the following in under {max_words} words. Be direct and factual.",
        max_tokens=300,
    )
