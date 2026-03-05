"""
J.A.R.V.I.S. 3.0 — Module 6: Text-to-Speech
Converts text responses to MP3 audio via OpenAI TTS.
Returns bytes ready to send as Telegram voice message.
"""

import re
from io import BytesIO

from openai import OpenAI

from config.settings import settings
from utils.helpers import get_logger, retry

logger = get_logger("tts")

_client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ─────────────────── TTS Core ─────────────────────────────────

@retry(max_attempts=2, delay=1.0)
def synthesize(text: str, voice: str = None) -> bytes:
    """
    Convert text to MP3 audio bytes.

    Args:
        text: The text to convert. Max ~4096 chars.
        voice: One of: alloy, echo, fable, onyx, nova, shimmer.

    Returns:
        Raw MP3 bytes.
    """
    voice = voice or settings.TTS_VOICE
    clean = _clean_text(text)

    # Truncate if too long (OpenAI TTS limit)
    if len(clean) > 4000:
        clean = clean[:4000] + "..."
        logger.warning("TTS input truncated to 4000 chars.")

    logger.info(f"TTS request: voice={voice}, length={len(clean)} chars")
    response = _client.audio.speech.create(
        model=settings.TTS_MODEL,
        voice=voice,
        input=clean,
    )
    return response.content


def synthesize_to_buffer(text: str, voice: str = None) -> BytesIO:
    """Return audio as a BytesIO buffer (for Telegram's reply_voice)."""
    audio_bytes = synthesize(text, voice=voice)
    buf = BytesIO(audio_bytes)
    buf.name = "jarvis_response.mp3"
    buf.seek(0)
    return buf


# ─────────────────── Text Cleaning ────────────────────────────

def _clean_text(text: str) -> str:
    """Remove Telegram Markdown and other symbols that sound bad when spoken."""
    # Remove markdown formatting
    text = re.sub(r"\*\*?(.*?)\*\*?", r"\1", text)   # bold/italic
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)
    text = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", text, flags=re.DOTALL)
    # Remove URLs
    text = re.sub(r"https?://\S+", "link", text)
    # Remove emoji-like symbols and special chars
    text = re.sub(r"[🔊📅📧💰⚠️✅❌🗑️✏️📋📌🕐🏪💵🏷️🔗👋]", "", text)
    # Collapse whitespace
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ─────────────────── Natural Language Handler ─────────────────

async def handle_tts(user_message: str) -> BytesIO:
    """
    Main entrypoint called by the Telegram router.
    Strips the /voice command prefix and synthesizes the remaining text.
    Returns a BytesIO buffer.
    """
    # Strip command prefix
    text = re.sub(r"^/voice\s*", "", user_message, flags=re.IGNORECASE).strip()

    if not text:
        # Default greeting if no text given
        text = "J.A.R.V.I.S. 3.0 is online and ready to assist."

    logger.info(f"TTS handle: '{text[:60]}...'")
    return synthesize_to_buffer(text)
