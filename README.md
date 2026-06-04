# Special Care Australia — AI Care Assistant

A customer-facing AI assistant for **Special Care Australia**, an NDIS-registered disability support provider. Participants, families, support coordinators, and staff chat with the assistant to look up participant records, find services, ask NDIS questions, and reach a human when needed.

Backend is a FastAPI + PostgreSQL app using Claude (Anthropic) for natural language. Frontend is an Angular SPA served from the same origin. The database is the **system of record** for SCA's operations (participants, plans, shifts, notes, incidents) — billing is intentionally excluded and handled by external software.

For the deeper docs, see:

- **[CLAUDE.md](./CLAUDE.md)** — architecture, conventions, API surface, what's done / what's left
- **[DB_Design.md](./DB_Design.md)** — full schema, FKs, triggers, soft-delete, phase status
- **[PLAN.md](./PLAN.md)** — single working plan: what's implemented and what's next, in shippable phases

## Prerequisites

- Python 3.10+
- Node 20+ and npm (for the Angular frontend)
- Docker (for PostgreSQL)
- An Anthropic API key

## Quick start

```bash
# 1. Install Python deps
python -m venv .venv
.venv\Scripts\activate                    # Windows
# source .venv/bin/activate                # macOS/Linux
pip install -e ".[dev]"

# 2. Configure secrets — create .env with at minimum:
#    ANTHROPIC_API_KEY=sk-ant-...
#    DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:5432/customer_service

# 3. Start PostgreSQL
docker compose up -d

# 4. Seed the database (creates tables + triggers + sample NDIS data + user accounts)
python -m app.memory.seed

# 5. Build the Angular SPA into app/static/
cd frontend && npm ci && npm run build && cd ..

# 6. Run the backend (serves API + SPA)
uvicorn app.main:app --reload --port 8001
```

Visit **http://127.0.0.1:8001** — you'll be redirected to `/login`.

> **Port note:** port 8000 is blocked on some Windows setups; this project defaults to **8001**.

## Default login (dev only)

The seed creates six accounts, all with password **`ChangeMe!2026`**:

| Email | Role | Sees |
|---|---|---|
| `admin@specialcareaust.example` | Administrator | All participants; own chats + every `escalated` chat across users |
| `maria.lo@specialcareaust.example` | Coordinator (staff) | All participants; own chats only |
| `tom.s@specialcareaust.example` | Support worker (staff) | All participants; own chats only |
| `aisha.p@example.com` | Participant | Only her own record; own chats only |
| `ben.n@example.com` | Participant | Only Ben's record; own chats only |
| `chloe.r@example.com` | Participant | Only Chloe's record; own chats only |

> **Rotate this password before any real participant data lands.** It's in source.

## Frontend dev server (hot reload)

```bash
cd frontend && npm start          # serves http://localhost:4200, proxies /chat /sessions /participants /auth … to :8001
```

## Tests

```bash
pytest -v
# 98 pass, 4 known-failing streaming-mock tests, 3 Postgres-only immutability tests skipped

# To run the Postgres-only tests against the local docker DB (Windows PowerShell):
$env:TEST_DATABASE_URL = "postgresql+asyncpg://agent:agent@localhost:5432/customer_service"
pytest tests/test_immutability.py -v
```

## License

Internal. Not for redistribution.
