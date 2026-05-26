# Customer Service AI Agent — Design Spec

## Context

Build a general-purpose customer service AI agent as a REST API service. The agent uses Claude (Anthropic) for natural language understanding, supports multi-turn conversations with persistent memory, can execute configurable tools (order lookup, account info, FAQ search, etc.), and escalates to human agents when needed. The goal is a clean, extensible foundation that can be adapted to any business domain by configuring the system prompt, tools, and escalation rules.

## Tech Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI (async)
- **LLM:** Claude via Anthropic Python SDK (`anthropic`, model: `claude-sonnet-4-6`)
- **Database:** PostgreSQL via SQLAlchemy (async) + asyncpg (SQLite/aiosqlite for tests)
- **Config:** Pydantic BaseSettings (`.env`) + `agent_config.yaml` for agent behavior
- **Testing:** pytest + pytest-asyncio
- **Logging:** structlog (structured JSON logging)
- **Build:** hatchling via pyproject.toml

## Architecture

Monolithic FastAPI application with clean module separation:

```
customer-service-agent/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, lifespan, middleware
│   ├── config.py                # Pydantic BaseSettings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── chat.py          # POST /chat, POST /chat/stream
│   │   │   ├── sessions.py      # Session CRUD
│   │   │   └── escalation.py    # Escalation endpoints
│   │   ├── models.py            # Request/response Pydantic models
│   │   └── dependencies.py      # Shared FastAPI dependencies
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── service.py           # Core agent logic — orchestrates Claude calls
│   │   ├── prompt.py            # System prompt builder
│   │   └── tool_executor.py     # Dispatches tool calls from Claude
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py          # Tool registration and discovery
│   │   └── examples/
│   │       ├── order_lookup.py
│   │       ├── account_info.py
│   │       └── faq_search.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── repository.py        # DB operations
│   │   └── database.py          # Async engine/session management (PostgreSQL)
│   └── escalation/
│       ├── __init__.py
│       └── handler.py           # Escalation detection + webhook
├── tests/
│   ├── conftest.py
│   ├── test_agent_service.py
│   ├── test_tool_registry.py
│   ├── test_chat_api.py
│   ├── test_memory.py
│   └── test_escalation.py
├── alembic/
│   └── versions/
├── alembic.ini
├── agent_config.yaml
├── pyproject.toml
├── .env.example
└── README.md
```

## Component Design

### 1. Agent Core (`app/agent/`)

**`service.py` — AgentService**

The central orchestrator. For each user message:

1. Load conversation history from PostgreSQL for the given session
2. Build the messages array: system prompt + history + new user message
3. Call Claude API with the tools list:
   - **Non-streaming (`/chat`):** `client.messages.create()` — returns complete response
   - **Streaming (`/chat/stream`):** `client.messages.stream()` — yields token-by-token SSE events
4. Enter a tool-use loop:
   - If Claude returns `tool_use` blocks → execute each via `tool_executor` → send results back → call Claude again
   - If Claude returns a text response → exit loop
5. Check the response for escalation signals
6. Save user message + assistant response to the database
7. Return the response

Safety: max 10 tool-call iterations per turn to prevent runaway loops.

**`prompt.py` — System Prompt Builder**

- Loads base personality/instructions from `agent_config.yaml`
- Appends runtime context (current date/time, session metadata)
- Injects escalation instructions: tells Claude to output `{"escalate": true, "reason": "..."}` when escalation is needed

**`tool_executor.py` — Tool Executor**

- Receives Claude's `tool_use` content blocks
- Looks up the tool function in the registry by name
- Calls it with the provided JSON input
- Returns the result as a `tool_result` content block
- Wraps exceptions into error messages so Claude can explain failures to the user

### 2. Tool System (`app/tools/`)

**`registry.py` — Decorator-based registration**

```python
@register_tool(
    name="lookup_order",
    description="Look up an order by order ID or customer email",
)
def lookup_order(order_id: str = None, email: str = None) -> dict:
    ...
```

- `@register_tool` captures function name, description, and type hints
- Type hints are auto-converted to JSON Schema for Claude's tool definitions
- Registry builds the complete tools list at startup
- `agent_config.yaml` controls which tools are enabled

**Example tools (stubs with mock data):**
- `order_lookup` — look up order by ID or email
- `account_info` — fetch account details
- `faq_search` — search a FAQ list

Adding a new tool: write a decorated function, add it to the config, done.

### 3. Memory (`app/memory/`)

**Database schema:**

**`sessions` table:**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Session identifier |
| created_at | DateTime | Session start time |
| updated_at | DateTime | Last activity |
| metadata | JSON | Optional data (customer ID, channel) |
| status | Enum | `active`, `escalated`, `closed` |

**`messages` table:**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Message identifier |
| session_id | UUID (FK → sessions) | Parent session |
| role | String | `user`, `assistant` |
| content | JSON | Message content (text or structured blocks) |
| created_at | DateTime | Timestamp |

**Context window management:**
- Configurable token threshold (default: 50,000 tokens)
- When exceeded: keep first message + last N messages
- Threshold and strategy configurable in `agent_config.yaml`

### 4. Escalation (`app/escalation/`)

**Triggers:**
1. Explicit user request ("talk to a human", "speak to an agent")
2. Claude detects high frustration/anger
3. Agent fails to resolve after N turns (default: 5)
4. Critical tool failure

**Mechanism:**
- System prompt instructs Claude to use a dedicated `escalate` tool (registered like any other tool) with parameters `{"reason": "..."}` when escalation is warranted
- `handler.py` detects when Claude calls the `escalate` tool and triggers the escalation flow
- On escalation:
  1. Set session status to `escalated`
  2. Fire webhook to configured URL with session context
  3. Return a handoff message to the user

**Webhook payload:**
```json
{
  "session_id": "...",
  "reason": "Customer requested human agent",
  "summary": "Customer asked about refund for order #1234...",
  "messages_count": 8,
  "customer_metadata": {}
}
```

If no webhook URL is configured, escalation is logged only (graceful degradation for dev).

## API Design

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Send a message, get a response |
| `POST` | `/chat/stream` | Send a message, get SSE stream |
| `POST` | `/sessions` | Create a new session |
| `GET` | `/sessions/{id}` | Get session details + messages |
| `DELETE` | `/sessions/{id}` | Close a session |
| `GET` | `/health` | Health check |

**`POST /chat` request:**
```json
{
  "session_id": "optional-uuid",
  "message": "Where is my order #1234?"
}
```

**`POST /chat` response:**
```json
{
  "session_id": "uuid",
  "response": "I found your order #1234. It shipped on...",
  "escalated": false,
  "tools_used": ["lookup_order"]
}
```

**Streaming:** `POST /chat/stream` returns Server-Sent Events (SSE) with true token-by-token streaming via `client.messages.stream()`. Events emitted:

| Event | When | Data |
|-------|------|------|
| `stream_start` | Once at start | `{"session_id": "..."}` |
| `text_delta` | Each text chunk from Claude | `{"delta": "Hello"}` |
| `tool_start` | Claude begins a tool call | `{"tool_name": "...", "tool_use_id": "..."}` |
| `tool_result` | After tool execution | `{"tool_name": "...", "tool_use_id": "...", "result": {...}}` |
| `escalation` | Escalation triggered | `{"reason": "..."}` |
| `error` | On failure | `{"error": "message"}` |
| `done` | Stream complete | `{"response": "full text", "session_id": "...", "escalated": false, "tools_used": [...]}` |

## Configuration

**`.env` (secrets and infrastructure):**
```
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:5432/customer_service
ESCALATION_WEBHOOK_URL=https://...
LOG_LEVEL=INFO
```

**`agent_config.yaml` (agent behavior):**
```yaml
agent:
  model: claude-sonnet-4-6
  max_tokens: 1024
  max_tool_iterations: 10

  personality: |
    You are a helpful, professional customer service agent.
    Be concise, empathetic, and solution-oriented.
    If you cannot resolve an issue, escalate to a human agent.

  enabled_tools:
    - order_lookup
    - account_info
    - faq_search

  memory:
    max_context_tokens: 50000
    strategy: keep_first_and_recent

  escalation:
    max_turns_before_escalate: 5
    webhook_url_env: ESCALATION_WEBHOOK_URL
```

## Error Handling

- Pydantic validation on all requests (automatic 422)
- Global exception handler: consistent `{"error": "...", "code": "ERROR_CODE"}` format
- Anthropic API errors (rate limits, overload) → 503 with retry guidance
- Tool errors → caught and fed back to Claude as tool_result errors
- Structured logging via `structlog` for all errors

## Testing Strategy

- **Unit tests:** tool registry, prompt builder, escalation logic, memory repository
- **Integration tests:** full chat flow with mocked Anthropic API responses
- **Test fixtures:** realistic conversation scenarios (happy path, tool use, escalation)
- **Coverage target:** core agent logic and tool system

## Verification Plan

1. Start PostgreSQL via `docker compose up -d`
2. Start the FastAPI server with `uvicorn app.main:app --reload --port 8001`
3. Create a session via `POST /sessions`
4. Send messages via `POST /chat` and verify:
   - Multi-turn conversation works (context is maintained)
   - Tool calls are executed and results appear in responses
   - Escalation triggers correctly on explicit request
5. Check PostgreSQL database for persisted sessions and messages
6. Run `pytest` and verify all tests pass
7. Test streaming endpoint via `POST /chat/stream` — verify token-by-token text delivery, tool_start/tool_result events, and escalation flow
