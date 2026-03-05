"""
J.A.R.V.I.S. 3.0 — Module 1: Telegram Bot
Main entry point. Receives messages, routes to agents, sends replies.
Uses python-telegram-bot v20+ (async).
"""

import asyncio
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from config.settings import settings
from llm.claude import detect_intent, chat
from utils.helpers import get_logger

# Agent imports
from expenses.tracker import handle_expense
from calendar_agent.agent import handle_calendar
from email_agent.agent import handle_email
from knowledge.rag import handle_knowledge
from tts.speech import handle_tts

logger = get_logger("telegram")

HELP_TEXT = """*J.A.R.V.I.S. 3.0* — Your AI Assistant

*Commands:*
/expense `<description>` — Log or query expenses
/calendar `<request>` — Manage events & schedule
/email `<request>` — Read, send, or reply to emails
/knowledge `<question>` — Search company knowledge base
/faq `<question>` — Company FAQ
/voice `<text>` — Convert text to voice message
/help — Show this menu

*Or just type naturally* — I'll figure out what you need."""


# ─────────────────── Auth Guard ───────────────────────────────

def is_authorized(chat_id: int) -> bool:
    allowed = settings.TELEGRAM_ALLOWED_CHAT_IDS
    return not allowed or chat_id in allowed


# ─────────────────── Command Handlers ─────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_chat.id):
        return
    await update.message.reply_text(
        "👋 *J.A.R.V.I.S. 3.0 online.* How can I assist?",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_chat.id):
        return
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


# ─────────────────── Main Message Router ─────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_authorized(chat_id):
        logger.warning(f"Unauthorized access attempt from chat_id={chat_id}")
        return

    user_text = update.message.text or ""
    if not user_text.strip():
        return

    logger.info(f"Message from {chat_id}: {user_text[:80]}")

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        intent = detect_intent(user_text)
        logger.info(f"Intent detected: {intent}")

        # Route to the correct agent
        if intent == "expense":
            reply = await handle_expense(user_text)
        elif intent == "calendar":
            reply = await handle_calendar(user_text)
        elif intent == "email":
            reply = await handle_email(user_text)
        elif intent in ("knowledge", "faq"):
            reply = await handle_knowledge(user_text)
        elif intent == "tts":
            audio_bytes = await handle_tts(user_text)
            await update.message.reply_voice(voice=audio_bytes)
            return
        elif intent == "help":
            await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)
            return
        else:
            # General conversation fallback
            reply = chat(user_text)

        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await update.message.reply_text(
            f"⚠️ Something went wrong: `{type(e).__name__}`\nPlease try again.",
            parse_mode=ParseMode.MARKDOWN,
        )


# ─────────────────── Error Handler ────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Unhandled error: {context.error}", exc_info=context.error)


# ─────────────────── Webhook Registration ─────────────────────

async def register_webhook(bot_token: str, webhook_url: str):
    """Register Telegram webhook. Call once during setup."""
    async with Bot(token=bot_token) as bot:
        await bot.set_webhook(url=webhook_url)
        info = await bot.get_webhook_info()
        logger.info(f"Webhook set: {info.url}")


# ─────────────────── App Factory ──────────────────────────────

def build_application() -> Application:
    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("expense", handle_message))
    app.add_handler(CommandHandler("calendar", handle_message))
    app.add_handler(CommandHandler("email", handle_message))
    app.add_handler(CommandHandler("knowledge", handle_message))
    app.add_handler(CommandHandler("faq", handle_message))
    app.add_handler(CommandHandler("voice", handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    return app


# ─────────────────── Entry Point ──────────────────────────────

if __name__ == "__main__":
    import sys
    logger.info("Starting J.A.R.V.I.S. 3.0 Telegram Bot (polling mode)...")
    app = build_application()
    app.run_polling(drop_pending_updates=True)
