# ic_agent

## Local Agent Commands

### Terminal chat demo

```powershell
venv\Scripts\python.exe interface.py
```

### Health check

```powershell
venv\Scripts\python.exe scripts\agent_healthcheck.py
```

### Verify Claude and build RAG index

```powershell
venv\Scripts\python.exe train.py
```

## Optional ReAct routing for web chat

Set this in `.env` to route `/api/chat_query` through the LangChain ReAct agent:

```env
CHAT_USE_REACT_AGENT=1
```

When `CHAT_USE_REACT_AGENT` is off (default), the existing deterministic chat flow remains active.

## Telegram Bot Setup

### Prerequisites
1. Create a Telegram bot using BotFather and obtain the bot token.
2. Add the bot token to the `.env` file:

```env
TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
```

### Running the Bot

Start the bot using the following command:

```powershell
venv\Scripts\python.exe -m ic_agent.web
```

The bot will handle queries and provide project progress updates directly in Telegram.