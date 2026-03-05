# 🤖 J.A.R.V.I.S.

### Just A Rather Very Intelligent System
<img width="2048" height="1365" alt="image" src="https://github.com/user-attachments/assets/a7851f7b-d772-4f23-8acd-d3f2838f00a0" />


A **modular AI personal assistant** powered by Claude and controlled through Telegram.

J.A.R.V.I.S integrates **automation, AI reasoning, knowledge retrieval, and personal productivity tools** into a single intelligent system.

---

# 🚀 Project Vision

The goal of this project is to create a **real-life AI assistant** similar to Iron Man's JARVIS.

It can:

• Understand natural language
• Automate daily tasks
• Manage information
• Integrate with real-world services

Future versions aim to evolve into a **fully autonomous personal AI system**.

---

# ✨ Features

✔ Telegram AI assistant
✔ Claude-powered natural language understanding
✔ Email automation (Gmail API)
✔ Calendar scheduling (Google Calendar)
✔ Expense tracking (Google Sheets)
✔ Knowledge retrieval with RAG (Pinecone)
✔ Voice responses with Text-to-Speech
✔ Modular AI agents
✔ Automated workflows using n8n

---

# 🏗 System Architecture

```
User (Telegram)
      │
      ▼
Telegram Bot
      │
      ▼
n8n Workflow Orchestrator
      │
      ▼
FastAPI Server
      │
 ┌────┼──────────────────────────┐
 │    │                          │
 ▼    ▼                          ▼
Email Agent     Calendar Agent     Expense Agent
 │                │                 │
 ▼                ▼                 ▼
Gmail API     Google Calendar     Google Sheets

      │
      ▼
Knowledge Agent (RAG)
      │
      ▼
Pinecone Vector Database
      │
      ▼
Claude LLM
```

---

# 🧠 Tech Stack

| Technology       | Purpose                   |
| ---------------- | ------------------------- |
| Python           | Core backend              |
| FastAPI          | API server                |
| Anthropic Claude | AI reasoning              |
| Telegram Bot API | User interface            |
| n8n              | Workflow automation       |
| Pinecone         | Vector database           |
| Google APIs      | Gmail / Calendar / Sheets |
| OpenAI TTS       | Voice generation          |

---

# 📂 Project Structure

```
Jarvis_V1_
│
├── jarvis
│   │
│   ├── orchestrator
│   │   └── server.py
│   │
│   ├── llm
│   │   └── claude.py
│   │
│   ├── telegram
│   │   └── bot.py
│   │
│   ├── email_agent
│   │   └── agent.py
│   │
│   ├── calendar_agent
│   │   └── agent.py
│   │
│   ├── expenses
│   │   └── tracker.py
│   │
│   ├── knowledge
│   │   └── rag.py
│   │
│   └── tts
│       └── speech.py
│
├── n8n_workflows
│   ├── JARVIS_Main_Workflow.json
│   └── JARVIS_Error_Handler.json
│
├── scripts
│   └── google_auth.py
│
├── requirements.txt
├── .env.example
├── README.md
└── LICENSE
```

---

# ⚙️ Installation

### 1. Clone the repository

```
git clone https://github.com/sohailros786-pixel/Jarvis_V1_.git
cd Jarvis_V1_
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Configure environment variables

```
cp .env.example .env
```

Add your API keys:

* Telegram Bot Token
* Claude API Key
* Google API credentials
* Pinecone API key

---

# 🤖 Telegram Bot Setup

1. Open Telegram
2. Search **@BotFather**
3. Run:

```
/newbot
```

4. Copy the bot token and add it to `.env`.

---

# 📊 Example Commands

Send messages to your Telegram bot:

```
/expense Paid $20 for lunch
/calendar Meeting with team tomorrow 3PM
/email Check unread emails
/knowledge What is our company policy?
/voice Good morning! What's my schedule today?
```

---

# 🔒 Security

• API keys stored in `.env`
• `.env` ignored using `.gitignore`
• Minimal API permissions used
• Sensitive data not logged

---

# 👨‍💻 About the Developer

**Sohail Ahmad**

Student developer passionate about **Artificial Intelligence and automation systems**.

Currently studying in **Class 8**, building advanced projects to explore the future of AI assistants and intelligent software systems.

Interests:

• Artificial Intelligence
• Automation
• AI assistants
• Software engineering

GitHub:

https://github.com/sohailros786-pixel

---

# 🌟 Future Plans

Planned improvements for J.A.R.V.I.S:

• Voice conversation interface
• Long-term memory system
• Autonomous task execution
• Smart home control
• Personal AI operating system

---

# 📜 License

This project is licensed under the **MIT License**.

---

# ⭐ Support

If you like this project, consider giving it a **star ⭐ on GitHub**.
