"""
J.A.R.V.I.S. 3.0 — Central Configuration
All settings loaded from environment variables.
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ALLOWED_CHAT_IDS: list = None  # None = allow all

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    ANTHROPIC_MAX_TOKENS: int = int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048"))

    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REFRESH_TOKEN: str = os.getenv("GOOGLE_REFRESH_TOKEN", "")
    GOOGLE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"

    # Google Sheets (Expenses)
    SHEETS_SPREADSHEET_ID: str = os.getenv("SHEETS_SPREADSHEET_ID", "")
    SHEETS_EXPENSE_TAB: str = os.getenv("SHEETS_EXPENSE_TAB", "Expenses")

    # Pinecone (Knowledge Base)
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX: str = os.getenv("PINECONE_INDEX", "jarvis-knowledge")
    PINECONE_NAMESPACE: str = os.getenv("PINECONE_NAMESPACE", "default")

    # OpenAI (embeddings + TTS only — LLM is Claude)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "nova")
    TTS_MODEL: str = os.getenv("TTS_MODEL", "tts-1")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")

    # n8n
    N8N_WEBHOOK_BASE_URL: str = os.getenv("N8N_WEBHOOK_BASE_URL", "")

    # App
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/New_York")

    def __post_init__(self):
        allowed = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "")
        self.TELEGRAM_ALLOWED_CHAT_IDS = (
            [int(x) for x in allowed.split(",") if x.strip()]
            if allowed else []
        )


settings = Settings()
