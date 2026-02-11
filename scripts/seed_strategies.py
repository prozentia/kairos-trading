"""Seed default strategies into the database.

Run this script after database migration to populate the strategies
table with the default strategy templates.

Usage:
    python scripts/seed_strategies.py
"""

import json
import sys

# Strategy definitions
STRATEGIES = [
    {
        "name": "MSB Glissant",
        "version": "1.0",
        "description": (
            "Sliding Market Structure Break strategy. "
            "Detects MSB levels on 1m candles, enters when Heikin Ashi 5m is green, "
            "price touches lower Bollinger Band, and closes above MSB level."
        ),
        "pairs": ["BTC/USDT"],
        "timeframe": "5m",
        "entry_conditions": {
            "logic": "AND",
            "conditions": [
                {
                    "indicator": "heikin_ashi",
                    "params": {"timeframe": "5m"},
                    "operator": "is_green",
                },
                {
                    "indicator": "bollinger",
                    "params": {"period": 20, "std_dev": 2.0, "timeframe": "1m"},
                    "operator": "touch_lower",
                },
                {
                    "indicator": "msb_glissant",
                    "params": {},
                    "operator": "break_above",
                },
            ],
        },
        "exit_conditions": {
            "logic": "OR",
            "conditions": [
                {
                    "indicator": "heikin_ashi",
                    "params": {"timeframe": "5m"},
                    "operator": "is_red",
                },
            ],
        },
        "filters": [
            {
                "type": "ema_trend",
                "params": {"indicator": "ema", "period": 50, "operator": "price_above"},
                "enabled": True,
            },
            {
                "type": "trading_hours",
                "params": {"start": "08:00", "end": "22:00", "timezone": "UTC"},
                "enabled": False,
            },
        ],
        "risk": {
            "stop_loss_pct": 1.5,
            "trailing_activation_pct": 0.6,
            "trailing_distance_pct": 0.3,
            "take_profit_levels": [{"pct": 1.0, "close_pct": 50.0}],
            "max_position_size_pct": 10.0,
        },
        "indicators_needed": [
            "heikin_ashi", "bollinger", "msb_glissant", "ema",
        ],
        "is_active": True,
    },
    {
        "name": "Scalping RSI-BB",
        "version": "1.0",
        "description": (
            "Scalping strategy using RSI oversold + Bollinger Band touch "
            "for entries, RSI overbought for exits. Short timeframe, tight stops."
        ),
        "pairs": ["BTC/USDT", "ETH/USDT"],
        "timeframe": "1m",
        "entry_conditions": {
            "logic": "AND",
            "conditions": [
                {"indicator": "rsi", "params": {"period": 14}, "operator": "below", "value": 30},
                {"indicator": "bollinger", "params": {"period": 20, "std_dev": 2.0}, "operator": "touch_lower"},
            ],
        },
        "exit_conditions": {
            "logic": "OR",
            "conditions": [
                {"indicator": "rsi", "params": {"period": 14}, "operator": "above", "value": 70},
                {"indicator": "bollinger", "params": {"period": 20, "std_dev": 2.0}, "operator": "touch_upper"},
            ],
        },
        "filters": [],
        "risk": {
            "stop_loss_pct": 0.5,
            "trailing_activation_pct": 0.3,
            "trailing_distance_pct": 0.15,
            "take_profit_levels": [],
            "max_position_size_pct": 5.0,
        },
        "indicators_needed": ["rsi", "bollinger"],
        "is_active": False,
    },
    {
        "name": "EMA Cross Trend",
        "version": "1.0",
        "description": (
            "Trend-following strategy using EMA 9/21 crossover for entries, "
            "confirmed by ADX strength. Medium timeframe, wider stops."
        ),
        "pairs": ["BTC/USDT"],
        "timeframe": "15m",
        "entry_conditions": {
            "logic": "AND",
            "conditions": [
                {"indicator": "ema_cross", "params": {"fast_period": 9, "slow_period": 21}, "operator": "golden_cross"},
                {"indicator": "adx_dmi", "params": {"period": 14}, "operator": "trending", "value": 25},
            ],
        },
        "exit_conditions": {
            "logic": "OR",
            "conditions": [
                {"indicator": "ema_cross", "params": {"fast_period": 9, "slow_period": 21}, "operator": "death_cross"},
            ],
        },
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
        "is_active": False,
    },
]


def seed():
    """Insert default strategies into the database.

    TODO: Wire up with SQLAlchemy once the database adapter is ready.
    """
    print(f"Seeding {len(STRATEGIES)} default strategies...")

    for strategy in STRATEGIES:
        print(f"  -> {strategy['name']} ({'active' if strategy['is_active'] else 'inactive'})")
        # TODO: Insert into database
        # async with get_session() as session:
        #     existing = await session.execute(
        #         select(StrategyModel).where(StrategyModel.name == strategy["name"])
        #     )
        #     if existing.scalar_one_or_none() is None:
        #         db_strategy = StrategyModel(**strategy)
        #         session.add(db_strategy)
        #         await session.commit()

    print("Done.")


if __name__ == "__main__":
    seed()
