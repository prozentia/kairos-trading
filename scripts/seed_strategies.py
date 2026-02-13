"""Seed default strategies into the database.

Inserts 5 ready-to-use strategy templates into the Strategy Builder.
Idempotent: skips strategies that already exist (matched by name).

Usage:
    # Local
    python scripts/seed_strategies.py

    # Inside Docker
    docker exec kairos-api python -m scripts.seed_strategies
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path (needed inside Docker)
_project_root = str(Path(__file__).resolve().parents[1])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from adapters.database.models import Strategy


# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------

def _get_database_url() -> str:
    """Resolve database URL from environment."""
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://kairos:kairos@db:5432/kairos",
    )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# ---------------------------------------------------------------------------
# Strategy definitions
# ---------------------------------------------------------------------------

STRATEGIES = [
    # ---- 1. MSB Glissant (signature Kairos) ----
    {
        "name": "MSB Glissant",
        "description": (
            "Stratégie Market Structure Break glissant. "
            "Détecte les niveaux MSB sur les bougies 1m, entre quand "
            "Heikin Ashi 5m est vert, que le prix touche la bande "
            "Bollinger inférieure et clôture au-dessus du niveau MSB. "
            "Filtre EMA 50 pour confirmer la tendance haussière."
        ),
        "definition": {
            "name": "MSB Glissant",
            "pairs": ["BTCUSDT"],
            "timeframe": "5m",
            "entry_conditions": [
                {
                    "indicator": "heikin_ashi",
                    "params": {"timeframe": "5m"},
                    "operator": "is_green",
                    "value": None,
                },
                {
                    "indicator": "bollinger",
                    "params": {"period": 20, "std_dev": 2.0, "timeframe": "1m"},
                    "operator": "touch_lower",
                    "value": None,
                },
                {
                    "indicator": "msb_glissant",
                    "params": {},
                    "operator": "break_above",
                    "value": None,
                },
            ],
            "exit_conditions": [
                {
                    "indicator": "heikin_ashi",
                    "params": {"timeframe": "5m"},
                    "operator": "is_red",
                    "value": None,
                },
            ],
            "filters": [
                {
                    "type": "ema_trend",
                    "params": {"indicator": "ema", "period": 50, "operator": "price_above"},
                    "enabled": True,
                },
            ],
            "risk": {
                "stop_loss_pct": 1.5,
                "trailing_activation_pct": 0.6,
                "trailing_distance_pct": 0.3,
                "take_profit_levels": [{"pct": 1.0, "close_pct": 50.0}],
                "max_position_size_pct": 10.0,
            },
            "indicators_needed": ["heikin_ashi", "bollinger", "msb_glissant", "ema"],
            "metadata": {"difficulty": "advanced", "style": "structure"},
        },
    },

    # ---- 2. Scalping RSI-BB ----
    {
        "name": "Scalping RSI-BB",
        "description": (
            "Scalping rapide basé sur le RSI en survente et le toucher "
            "de la bande Bollinger inférieure. Sortie quand le RSI est "
            "en surachat ou touche la bande supérieure. Timeframe 1m, "
            "stops serrés. Idéal pour les marchés volatils latéraux."
        ),
        "definition": {
            "name": "Scalping RSI-BB",
            "pairs": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "1m",
            "entry_conditions": [
                {
                    "indicator": "rsi",
                    "params": {"period": 14},
                    "operator": "below",
                    "value": 30,
                },
                {
                    "indicator": "bollinger",
                    "params": {"period": 20, "std_dev": 2.0},
                    "operator": "touch_lower",
                    "value": None,
                },
            ],
            "exit_conditions": [
                {
                    "indicator": "rsi",
                    "params": {"period": 14},
                    "operator": "above",
                    "value": 70,
                },
                {
                    "indicator": "bollinger",
                    "params": {"period": 20, "std_dev": 2.0},
                    "operator": "touch_upper",
                    "value": None,
                },
            ],
            "filters": [],
            "risk": {
                "stop_loss_pct": 0.5,
                "trailing_activation_pct": 0.3,
                "trailing_distance_pct": 0.15,
                "take_profit_levels": [],
                "max_position_size_pct": 5.0,
            },
            "indicators_needed": ["rsi", "bollinger"],
            "metadata": {"difficulty": "easy", "style": "scalping"},
        },
    },

    # ---- 3. EMA Cross Trend ----
    {
        "name": "EMA Cross Trend",
        "description": (
            "Suivi de tendance avec croisement EMA 9/21 confirmé par "
            "la force du trend via ADX > 25. Filtre EMA 200 pour ne "
            "trader que dans le sens de la tendance majeure. "
            "Deux niveaux de take-profit (2% et 4%). Timeframe 15m."
        ),
        "definition": {
            "name": "EMA Cross Trend",
            "pairs": ["BTCUSDT"],
            "timeframe": "15m",
            "entry_conditions": [
                {
                    "indicator": "ema_cross",
                    "params": {"fast_period": 9, "slow_period": 21},
                    "operator": "golden_cross",
                    "value": None,
                },
                {
                    "indicator": "adx_dmi",
                    "params": {"period": 14},
                    "operator": "above",
                    "value": 25,
                },
            ],
            "exit_conditions": [
                {
                    "indicator": "ema_cross",
                    "params": {"fast_period": 9, "slow_period": 21},
                    "operator": "death_cross",
                    "value": None,
                },
            ],
            "filters": [
                {
                    "type": "ema_trend",
                    "params": {"indicator": "ema", "period": 200, "operator": "price_above"},
                    "enabled": True,
                },
            ],
            "risk": {
                "stop_loss_pct": 2.0,
                "trailing_activation_pct": 1.0,
                "trailing_distance_pct": 0.5,
                "take_profit_levels": [
                    {"pct": 2.0, "close_pct": 50.0},
                    {"pct": 4.0, "close_pct": 100.0},
                ],
                "max_position_size_pct": 10.0,
            },
            "indicators_needed": ["ema_cross", "adx_dmi", "ema"],
            "metadata": {"difficulty": "medium", "style": "trend_following"},
        },
    },

    # ---- 4. RSI MACD Momentum ----
    {
        "name": "RSI MACD Momentum",
        "description": (
            "Combinaison RSI + MACD + Volume pour capturer les retournements "
            "de momentum. Entre quand le RSI est en zone neutre-basse (<40), "
            "que le MACD croise au-dessus du signal et que le volume confirme. "
            "Deux niveaux de TP à 1.5% et 3%. Bon ratio risque/rendement."
        ),
        "definition": {
            "name": "RSI MACD Momentum",
            "pairs": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "5m",
            "entry_conditions": [
                {
                    "indicator": "rsi",
                    "params": {"period": 14},
                    "operator": "below",
                    "value": 40,
                },
                {
                    "indicator": "macd",
                    "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
                    "operator": "cross_above_signal",
                    "value": None,
                },
                {
                    "indicator": "volume",
                    "params": {"sma_period": 20},
                    "operator": "above_sma",
                    "value": None,
                },
            ],
            "exit_conditions": [
                {
                    "indicator": "rsi",
                    "params": {"period": 14},
                    "operator": "above",
                    "value": 75,
                },
                {
                    "indicator": "macd",
                    "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
                    "operator": "cross_below_signal",
                    "value": None,
                },
            ],
            "filters": [],
            "risk": {
                "stop_loss_pct": 1.5,
                "trailing_activation_pct": 0.8,
                "trailing_distance_pct": 0.4,
                "take_profit_levels": [
                    {"pct": 1.5, "close_pct": 50.0},
                    {"pct": 3.0, "close_pct": 100.0},
                ],
                "max_position_size_pct": 8.0,
            },
            "indicators_needed": ["rsi", "macd", "volume"],
            "metadata": {"difficulty": "medium", "style": "momentum"},
        },
    },

    # ---- 5. Breakout Volume ----
    {
        "name": "Breakout Volume",
        "description": (
            "Stratégie de breakout utilisant les canaux Donchian (20 périodes) "
            "confirmée par un pic de volume (>2x la moyenne). "
            "Entre sur cassure du canal supérieur, sort sur cassure inférieure "
            "ou si l'ADX tombe sous 20 (perte de momentum). "
            "Stops larges pour laisser respirer les mouvements."
        ),
        "definition": {
            "name": "Breakout Volume",
            "pairs": ["BTCUSDT", "SOLUSDT"],
            "timeframe": "15m",
            "entry_conditions": [
                {
                    "indicator": "donchian",
                    "params": {"period": 20},
                    "operator": "break_upper",
                    "value": None,
                },
                {
                    "indicator": "volume",
                    "params": {"sma_period": 20, "multiplier": 2.0},
                    "operator": "above_sma_multiplied",
                    "value": None,
                },
            ],
            "exit_conditions": [
                {
                    "indicator": "donchian",
                    "params": {"period": 20},
                    "operator": "break_lower",
                    "value": None,
                },
                {
                    "indicator": "adx_dmi",
                    "params": {"period": 14},
                    "operator": "below",
                    "value": 20,
                },
            ],
            "filters": [
                {
                    "type": "adx_trend",
                    "params": {"indicator": "adx_dmi", "period": 14, "min_value": 25},
                    "enabled": True,
                },
            ],
            "risk": {
                "stop_loss_pct": 2.5,
                "trailing_activation_pct": 1.2,
                "trailing_distance_pct": 0.6,
                "take_profit_levels": [
                    {"pct": 3.0, "close_pct": 50.0},
                    {"pct": 6.0, "close_pct": 100.0},
                ],
                "max_position_size_pct": 8.0,
            },
            "indicators_needed": ["donchian", "volume", "adx_dmi"],
            "metadata": {"difficulty": "advanced", "style": "breakout"},
        },
    },
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

async def seed() -> None:
    """Insert default strategies into the database.

    Idempotent: skips strategies that already exist (matched by name).
    """
    database_url = _get_database_url()
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = 0
    skipped = 0

    async with async_session() as session:
        for strat in STRATEGIES:
            name = strat["name"]

            # Check if strategy already exists
            result = await session.execute(
                select(Strategy).where(Strategy.name == name)
            )
            if result.scalar_one_or_none() is not None:
                print(f"  [SKIP] {name} (already exists)")
                skipped += 1
                continue

            # Insert new strategy
            strategy = Strategy(
                name=name,
                description=strat["description"],
                json_definition=json.dumps(strat["definition"]),
                is_active=False,
                is_validated=True,
                total_trades=0,
                winning_trades=0,
                total_pnl=0.0,
            )
            session.add(strategy)
            print(f"  [NEW]  {name}")
            created += 1

        await session.commit()

    await engine.dispose()

    print(f"\nDone: {created} created, {skipped} skipped (total: {len(STRATEGIES)})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Seeding {len(STRATEGIES)} default strategies...\n")
    asyncio.run(seed())
