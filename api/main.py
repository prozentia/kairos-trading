"""Kairos Trading API - FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    ai_reports,
    alerts,
    auth,
    backtests,
    bot,
    daily_stats,
    market,
    portfolio,
    settings,
    strategies,
    trades,
    websocket,
)
from api.middleware.rate_limit import RateLimitMiddleware

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Startup: initialise database connection pool, Redis, seed data.
    Shutdown: close connections gracefully.
    """
    from api.deps import init_db, close_db

    # -- Startup ---------------------------------------------------------------
    print("[Kairos API] Starting up...")
    await init_db()
    print("[Kairos API] Database initialised.")
    yield
    # -- Shutdown --------------------------------------------------------------
    await close_db()
    print("[Kairos API] Shutting down...")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Kairos Trading API",
    version="1.0.0",
    description="Multi-pair automated trading platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://kairos.prozentia.com",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Custom middleware
# ---------------------------------------------------------------------------

app.add_middleware(RateLimitMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(trades.router, prefix="/trades", tags=["Trades"])
app.include_router(strategies.router, prefix="/strategies", tags=["Strategies"])
app.include_router(market.router, prefix="/market", tags=["Market"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(bot.router, prefix="/bot", tags=["Bot"])
app.include_router(backtests.router, prefix="/backtests", tags=["Backtests"])
app.include_router(ai_reports.router, prefix="/ai-reports", tags=["AI Reports"])
app.include_router(daily_stats.router, prefix="/daily-stats", tags=["Daily Stats"])
app.include_router(settings.router, prefix="/settings", tags=["Settings"])
app.include_router(websocket.router, tags=["WebSocket"])


# ---------------------------------------------------------------------------
# Root endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}
