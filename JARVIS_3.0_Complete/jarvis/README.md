# J.A.R.V.I.S. 3.0

> **Just A Rather Very Intelligent System** — Your modular AI personal assistant

Telegram-driven. Anthropic Claude-powered. Fully automated.

---

## Architecture

```
Telegram Message
      │
      ▼
n8n Cloud (JARVIS_00_Main_Orchestrator)
      │
      ▼
FastAPI Orchestrator (orchestrator/server.py)
      │
      ├── expense  ──►  expenses/tracker.py    ──► Google Sheets
      ├── calendar ──►  calendar_agent/agent.py ──► Google Calendar
      ├── email    ──►  email_agent/agent.py    ──► Gmail
      ├── knowledge──►  knowledge/rag.py        ──► Pinecone + Claude
      ├── tts      ──►  tts/speech.py           ──► OpenAI TTS
      └── general  ──►  llm/claude.py           ──► Anthropic Claude
```

---

## Quick Setup

### 1. Clone & Install

```bash
git clone <your-repo>
cd jarvis
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Create Telegram Bot

1. Open Telegram → search `@BotFather`
2. Send `/newbot` → follow prompts
3. Copy the token to `TELEGRAM_BOT_TOKEN` in `.env`

### 3. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project → enable **Gmail API**, **Google Calendar API**, **Google Sheets API**
3. Create OAuth 2.0 credentials (Desktop app)
4. Run the auth helper to get your refresh token:

```bash
python scripts/google_auth.py
```

Copy the printed values to `.env`.

### 4. Pinecone Setup

1. Create free account at [pinecone.io](https://pinecone.io)
2. Create index: name=`jarvis-knowledge`, dims=`1536`, metric=`cosine`
3. Copy API key to `PINECONE_API_KEY` in `.env`

### 5. Google Sheet for Expenses

1. Create a new Google Sheet
2. Copy the spreadsheet ID from the URL
3. Add to `SHEETS_SPREADSHEET_ID` in `.env`

### 6. Start the Orchestrator

```bash
python main.py server
```

The server runs on `http://0.0.0.0:8000`.
For production, deploy to Railway, Render, or a VPS and expose HTTPS.

### 7. n8n Cloud Setup

1. Create account at [n8n.io](https://n8n.io)
2. Import `n8n_workflows/JARVIS_00_Main_Orchestrator.json`
3. Import `n8n_workflows/JARVIS_99_Error_Handler.json`
4. Add credentials:
   - **Telegram Bot** → your bot token
5. Set environment variable in n8n:
   - `JARVIS_ORCHESTRATOR_URL` → your server URL (e.g., `https://jarvis.yourdomain.com`)
   - `TELEGRAM_ADMIN_CHAT_ID` → your Telegram chat ID for error alerts
6. Activate both workflows

### 8. Ingest Company Knowledge

```bash
python -m knowledge.rag --file path/to/your/document.txt --id doc_001 --source "Company Handbook"
```

---

## Usage

Send messages to your Telegram bot:

| Command | Example |
|---------|---------|
| `/expense` | `/expense Paid $45 at Uber Eats for team lunch` |
| `/calendar` | `/calendar Schedule a meeting with John tomorrow at 2pm` |
| `/email` | `/email Check my inbox` |
| `/knowledge` | `/knowledge What is our remote work policy?` |
| `/voice` | `/voice Good morning, your schedule today is...` |
| Natural language | `How much did I spend on transport this month?` |

---

## Module Summary

| Module | File | Purpose |
|--------|------|---------|
| 1. Telegram | `telegram/bot.py` | Bot entry, routing, polling |
| 2. LLM | `llm/claude.py` | Claude wrapper, intent detection |
| 3. Email | `email_agent/agent.py` | Gmail read/send/reply/label |
| 4. Calendar | `calendar_agent/agent.py` | Google Calendar CRUD |
| 5. Expenses | `expenses/tracker.py` | Log + query via Google Sheets |
| 6. TTS | `tts/speech.py` | Text-to-speech via OpenAI TTS |
| 7. Knowledge | `knowledge/rag.py` | RAG with Pinecone + embeddings |
| Orchestrator | `orchestrator/server.py` | FastAPI webhook server for n8n |

---

## Environment Variables

See `.env.example` for the full list.

---

## Error Handling

- All agents use `@retry` decorator (3 attempts, 2s delay)
- n8n Error Handler workflow sends failures to your Telegram
- `ParseError`, `APIError`, `AuthError` for typed error handling
- Each agent returns user-friendly error messages to Telegram

---

## Data Privacy

- No raw email content is logged — only metadata
- Expense data restricted to service account access
- All secrets in environment variables, never hardcoded
- Use Google service account with minimum required scopes:
  - `gmail.modify`, `calendar.events`, `spreadsheets`
