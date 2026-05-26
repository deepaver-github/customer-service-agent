# Customer Service AI Agent

A general-purpose customer service AI agent powered by Claude (Anthropic). Built with Python, FastAPI, and PostgreSQL.

## Features

- **Multi-turn conversations** with persistent session memory
- **Tool calling** — the agent can look up orders, check accounts, search FAQs
- **Human escalation** — detects when to hand off to a human agent via webhook
- **Token-by-token streaming** — real-time SSE responses using Claude's streaming API
- **Configurable** — customize personality, tools, and escalation rules via YAML

## Quick Start

### 1. Install

```bash
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -e ".[dev]"
```

### 2. Configure

```bash
copy .env .env
```

Edit `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8001`. API docs at `http://localhost:8001/docs`.

> **Note:** Port 8000 is blocked on some machines; this project defaults to port 8001.

### Prerequisites

- **PostgreSQL** — run via Docker:
  ```bash
  docker compose up -d
  ```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Send a message, get a response |
| `POST` | `/chat/stream` | Send a message, get SSE stream |
| `POST` | `/sessions` | Create a new session |
| `GET` | `/sessions/{id}` | Get session details + messages |
| `DELETE` | `/sessions/{id}` | Close a session |
| `GET` | `/health` | Health check |

### Example: Chat

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Where is my order ORD-1234?"}'
```

Response:

```json
{
  "session_id": "uuid-here",
  "response": "I found your order ORD-1234. It has been shipped...",
  "escalated": false,
  "tools_used": ["lookup_order"]
}
```

### Example: Continue a conversation

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "uuid-from-above", "message": "When will it arrive?"}'
```

## Configuration

### Agent Behavior (`agent_config.yaml`)

- **personality** — system prompt / agent instructions
- **model** — Claude model to use (default: `claude-sonnet-4-6`)
- **enabled_tools** — which tools the agent can use
- **escalation** — when to hand off to a human

### Adding Custom Tools

1. Create a file in `app/tools/examples/` (or any module)
2. Use the `@register_tool` decorator:

```python
from app.tools.registry import register_tool

@register_tool(
    name="my_tool",
    description="What this tool does",
)
def my_tool(param1: str, param2: int = 0) -> dict:
    # Your logic here
    return {"result": "..."}
```

3. Add the tool name to `enabled_tools` in `agent_config.yaml`
4. Import the module in `app/tools/examples/__init__.py`

## Testing

```bash
pytest -v
```

## Project Structure

```
app/
  main.py              # FastAPI app entry point
  config.py            # Settings and config loading
  api/routes/          # REST endpoints
  agent/               # Claude integration and orchestration
  tools/               # Pluggable tool system
  memory/              # PostgreSQL conversation persistence
  escalation/          # Human handoff logic
tests/                 # Test suite
agent_config.yaml      # Agent behavior configuration
```
