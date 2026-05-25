# Customer Service AI Agent — Project Context

## What This Is

A general-purpose customer service AI agent built as a REST API. It uses Claude (Anthropic) for natural language understanding, supports multi-turn conversations with persistent memory, executes configurable tools, and escalates to human agents when needed.

## Tech Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI (async)
- **LLM:** Claude via Anthropic Python SDK (`anthropic`, model: `claude-sonnet-4-6`)
- **Database:** SQLite via SQLAlchemy (async) + aiosqlite
- **Config:** Pydantic BaseSettings (`.env`) + `agent_config.yaml` for agent behavior
- **Testing:** pytest + pytest-asyncio (33 tests, all passing)
- **Logging:** structlog (structured JSON)
- **Build:** hatchling via pyproject.toml

## Architecture

Monolithic FastAPI app with clean module separation:

```
app/
  main.py              # FastAPI app, lifespan, middleware, route includes
  config.py            # Pydantic BaseSettings + YAML config loader
  api/
    models.py          # Request/response Pydantic models
    dependencies.py    # FastAPI DI (AgentService singleton)
    routes/
      chat.py          # POST /chat, POST /chat/stream (SSE)
      sessions.py      # Session CRUD
  agent/
    service.py         # Core agent — orchestrates Claude API calls + tool-use loop
    prompt.py          # System prompt builder from YAML config
    tool_executor.py   # Dispatches tool calls, handles errors
  tools/
    registry.py        # @register_tool decorator, JSON Schema generation
    examples/
      order_lookup.py  # Mock order lookup tool
      account_info.py  # Mock account info tool
      faq_search.py    # FAQ keyword search tool
  memory/
    database.py        # Async SQLAlchemy engine/session factory
    models.py          # Session + Message SQLAlchemy models
    repository.py      # DB CRUD operations
  escalation/
    handler.py         # Escalation tool + webhook dispatch
tests/
  conftest.py          # Fixtures: in-memory DB, mock Anthropic client, helpers
  test_tool_registry.py
  test_memory.py
  test_agent_service.py
  test_escalation.py
  test_chat_api.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /chat | Send message, get response |
| POST | /chat/stream | Send message, get SSE stream |
| POST | /sessions | Create a new session |
| GET | /sessions/{id} | Get session + message history |
| DELETE | /sessions/{id} | Close a session |
| GET | /health | Health check |

## Key Design Decisions

- **No LangChain** — uses Claude's native tool-use API directly. Simpler, easier to debug.
- **Decorator-based tool registration** — `@register_tool` auto-converts type hints to JSON Schema for Claude.
- **Escalation as a tool** — the `escalate` tool is registered like any other tool; Claude calls it when escalation is warranted. Cleaner than parsing JSON from text responses.
- **SQLite for simplicity** — tables auto-created on startup via `Base.metadata.create_all`. No Alembic migrations set up yet (can add later).
- **Context window management** — keeps last N messages (configurable `max_recent_messages` in YAML).
- **Single deployment** — not multi-tenant.

## Configuration

- **`.env`** — secrets: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `ESCALATION_WEBHOOK_URL`, `LOG_LEVEL`
- **`agent_config.yaml`** — agent behavior: personality, model, max_tokens, enabled tools, memory settings, escalation rules

## Running

```bash
# Activate venv
.venv\Scripts\activate

# Run server
uvicorn app.main:app --reload --port 8001

# Run tests
pytest -v
```

Port 8000 was blocked on this machine; use port 8001.

## IntelliJ Debug Setup

- Run/Debug config: Module name `uvicorn`, Parameters `app.main:app --reload --port 8001`
- Working directory: project root
- Interpreter: `.venv\Scripts\python.exe`
- Remove `--reload` from params when using breakpoints (reload spawns a child process)

## Design Spec

Full design document at: `docs/superpowers/specs/2026-05-24-customer-service-agent-design.md`

## What's Not Done Yet

- Alembic migrations (tables are auto-created for now)
- True token-by-token streaming (current SSE returns complete response)
- Authentication/authorization on API endpoints
- Rate limiting
- Production deployment config (Docker, etc.)
