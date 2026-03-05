"""
J.A.R.V.I.S. 3.0 — Main Entry Point
Run the orchestrator server (default) or the Telegram polling bot.

Usage:
  python main.py server    # Run FastAPI webhook server (for n8n Cloud)
  python main.py bot       # Run Telegram bot in polling mode (standalone)
"""

import sys
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "server"

    if mode == "bot":
        from telegram.bot import build_application
        print("Starting J.A.R.V.I.S. 3.0 in Telegram polling mode...")
        app = build_application()
        app.run_polling(drop_pending_updates=True)

    elif mode == "server":
        import uvicorn
        from config.settings import settings
        print("Starting J.A.R.V.I.S. 3.0 orchestrator server on port 8000...")
        uvicorn.run(
            "orchestrator.server:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level=settings.LOG_LEVEL.lower(),
        )

    else:
        print(f"Unknown mode: {mode}. Use 'server' or 'bot'.")
        sys.exit(1)
