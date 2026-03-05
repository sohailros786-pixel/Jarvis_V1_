"""
J.A.R.V.I.S. 3.0 — Orchestrator
FastAPI webhook server that receives n8n payloads and dispatches to agents.
Also exposes a /health endpoint for uptime monitoring.
"""

from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from config.settings import settings
from utils.helpers import get_logger
from llm.claude import detect_intent, chat
from expenses.tracker import handle_expense
from calendar_agent.agent import handle_calendar
from email_agent.agent import handle_email
from knowledge.rag import handle_knowledge
from tts.speech import handle_tts

import base64

logger = get_logger("orchestrator")


# ─────────────────── FastAPI App ──────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("J.A.R.V.I.S. 3.0 Orchestrator starting up...")
    yield
    logger.info("J.A.R.V.I.S. 3.0 shutting down.")


app = FastAPI(title="J.A.R.V.I.S. 3.0 Orchestrator", version="3.0.0", lifespan=lifespan)


# ─────────────────── Request / Response Models ────────────────

class MessagePayload(BaseModel):
    chat_id: str
    text: str
    user_id: Optional[str] = None
    username: Optional[str] = None


class AgentResponse(BaseModel):
    chat_id: str
    reply: Optional[str] = None
    audio_base64: Optional[str] = None  # for TTS
    intent: str = "general"
    error: Optional[str] = None


# ─────────────────── Endpoints ────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "online", "service": "J.A.R.V.I.S. 3.0"}


@app.post("/webhook/message", response_model=AgentResponse)
async def receive_message(payload: MessagePayload):
    """
    Main webhook. n8n posts here after receiving a Telegram message.
    Returns the agent reply for n8n to send back via Telegram.
    """
    logger.info(f"Webhook | chat_id={payload.chat_id} | text={payload.text[:80]}")

    intent = detect_intent(payload.text)
    logger.info(f"Intent: {intent}")

    try:
        if intent == "expense":
            reply = await handle_expense(payload.text)
            return AgentResponse(chat_id=payload.chat_id, reply=reply, intent=intent)

        elif intent == "calendar":
            reply = await handle_calendar(payload.text)
            return AgentResponse(chat_id=payload.chat_id, reply=reply, intent=intent)

        elif intent == "email":
            reply = await handle_email(payload.text)
            return AgentResponse(chat_id=payload.chat_id, reply=reply, intent=intent)

        elif intent in ("knowledge", "faq"):
            reply = await handle_knowledge(payload.text)
            return AgentResponse(chat_id=payload.chat_id, reply=reply, intent=intent)

        elif intent == "tts":
            audio_buf = await handle_tts(payload.text)
            audio_b64 = base64.b64encode(audio_buf.read()).decode()
            return AgentResponse(
                chat_id=payload.chat_id,
                audio_base64=audio_b64,
                intent=intent,
            )

        elif intent == "help":
            reply = _help_text()
            return AgentResponse(chat_id=payload.chat_id, reply=reply, intent=intent)

        else:
            reply = chat(payload.text)
            return AgentResponse(chat_id=payload.chat_id, reply=reply, intent=intent)

    except Exception as e:
        logger.error(f"Orchestrator error: {e}", exc_info=True)
        return AgentResponse(
            chat_id=payload.chat_id,
            reply=f"⚠️ Internal error ({type(e).__name__}). Please try again.",
            intent=intent,
            error=str(e),
        )


@app.post("/webhook/ingest")
async def ingest_document(request: Request):
    """
    Ingest a document into the knowledge base.
    POST JSON: { "text": "...", "doc_id": "...", "source": "..." }
    """
    from knowledge.rag import ingest_document
    body = await request.json()
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="'text' field required")

    n = ingest_document(
        text=text,
        doc_id=body.get("doc_id"),
        metadata={"source": body.get("source", "API Upload")},
    )
    return {"status": "ok", "chunks_ingested": n}


# ─────────────────── Help Text ────────────────────────────────

def _help_text() -> str:
    return """*J.A.R.V.I.S. 3.0* — Your AI Assistant

*Commands:*
/expense — Log or query expenses
/calendar — Manage events and schedule
/email — Read, send, or reply to emails
/knowledge — Search company knowledge base
/faq — Company FAQ
/voice `<text>` — Convert text to voice message
/help — Show this menu

_Or just type naturally — I'll figure it out._"""


# ─────────────────── Entry Point ──────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "orchestrator.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )
