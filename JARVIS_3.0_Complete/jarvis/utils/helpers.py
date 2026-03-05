"""
J.A.R.V.I.S. 3.0 — Shared Utilities
Logger, Google credentials, retry decorator, error types.
"""

import logging
import time
import functools
from typing import Callable, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

from config.settings import settings


# ─────────────────────────── Logger ───────────────────────────

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
    return logger


logger = get_logger("utils")


# ─────────────────────── Google Auth ──────────────────────────

_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_google_credentials() -> Credentials:
    """Return refreshed Google OAuth2 credentials."""
    creds = Credentials(
        token=None,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        token_uri=settings.GOOGLE_TOKEN_URI,
        scopes=_GOOGLE_SCOPES,
    )
    creds.refresh(GoogleRequest())
    return creds


# ─────────────────────── Retry Decorator ──────────────────────

def retry(max_attempts: int = 3, delay: float = 2.0, exceptions=(Exception,)):
    """Retry a function on failure with fixed delay."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    logger.warning(
                        f"[retry] {func.__name__} failed (attempt {attempt}/{max_attempts}): {e}"
                    )
                    if attempt < max_attempts:
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator


# ─────────────────────── Custom Errors ────────────────────────

class JarvisError(Exception):
    """Base exception for J.A.R.V.I.S."""
    pass

class ParseError(JarvisError):
    """LLM response could not be parsed."""
    pass

class APIError(JarvisError):
    """External API call failed."""
    pass

class AuthError(JarvisError):
    """Authentication / credentials error."""
    pass
