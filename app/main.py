from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings, get_agent_config
from app.memory.database import init_db


structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    get_agent_config()
    await init_db(settings.database_url)
    log.info("application_started")
    yield
    log.info("application_shutdown")


app = FastAPI(
    title="Customer Service AI Agent",
    description="General-purpose customer service agent powered by Claude",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


from app.api.routes import admin, auth, chat, participants, sessions  # noqa: E402

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(participants.router, prefix="/participants", tags=["participants"])
app.include_router(admin.router, tags=["admin"])

STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


class SPAStaticFiles(StaticFiles):
    """Static-files mount that falls back to index.html on 404 so Angular's
    client-side router can handle paths like /login when no API route matched.
    Real missing assets (.js/.css/.png) still 404 because they contain a dot.
    """

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and "." not in path.rsplit("/", 1)[-1]:
                return await super().get_response("index.html", scope)
            raise


def _is_browser_navigation(request: Request) -> bool:
    if request.method != "GET":
        return False
    accept = request.headers.get("accept", "")
    return "text/html" in accept


@app.exception_handler(StarletteHTTPException)
async def spa_fallback_handler(request: Request, exc: StarletteHTTPException):
    """Browser GETs that hit an API route which 401/404/405s should fall through
    to the SPA so Angular can render /login, /participants/:id, etc. XHR clients
    (Accept: application/json) still receive proper JSON errors."""
    if (
        exc.status_code in (401, 404, 405)
        and _is_browser_navigation(request)
        and INDEX_HTML.is_file()
    ):
        return FileResponse(INDEX_HTML)
    return await http_exception_handler(request, exc)


app.mount("/", SPAStaticFiles(directory=STATIC_DIR, html=True), name="static")
