"""Core test fixtures for Kairos Trading.

Provides realistic BTC/USDT candle data, positions, trades,
and strategy configuration objects for use across core tests.
"""

import random
from datetime import datetime, timedelta, timezone

import pytest

from core.models import (
    Candle,
    Position,
    PositionStatus,
    RiskLimits,
    Signal,
    SignalType,
    StrategyConfig,
    Trade,
)


# Reproducible random data
_RNG = random.Random(42)


def _generate_candles(
    count: int = 500,
    pair: str = "BTC/USDT",
    timeframe: str = "1m",
    start_price: float = 97_500.0,
    start_time: datetime | None = None,
) -> list[Candle]:
    """Generate *count* realistic OHLCV candles using a random walk.

    Properties guaranteed:
        - high >= max(open, close)
        - low  <= min(open, close)
        - volume > 0
    """
    if start_time is None:
        start_time = datetime(2026, 2, 10, 0, 0, 0, tzinfo=timezone.utc)

    candles: list[Candle] = []
    price = start_price

    for i in range(count):
        # Random walk: -0.3% to +0.3% per candle
        change_pct = _RNG.uniform(-0.003, 0.003)
        open_price = round(price, 2)

        close_price = round(open_price * (1 + change_pct), 2)

        # Intra-candle wick noise
        wick_up = round(abs(_RNG.gauss(0, open_price * 0.001)), 2)
        wick_down = round(abs(_RNG.gauss(0, open_price * 0.001)), 2)

        high_price = round(max(open_price, close_price) + wick_up, 2)
        low_price = round(min(open_price, close_price) - wick_down, 2)

        # Ensure low is always positive
        low_price = max(low_price, round(min(open_price, close_price) * 0.999, 2))

        volume = round(_RNG.uniform(0.5, 25.0), 6)

        ts = start_time + timedelta(minutes=i)

        candles.append(
            Candle(
                timestamp=ts,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                pair=pair,
                timeframe=timeframe,
                is_closed=True,
            )
        )

        # Next candle opens around last close
        price = close_price

    return candles


@pytest.fixture
def sample_candles() -> list[Candle]:
    """500 BTC/USDT 1m candles with realistic OHLCV data."""
    return _generate_candles(count=500)


@pytest.fixture
def sample_candle() -> Candle:
    """A single BTC/USDT 1m candle."""
    return Candle(
        timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        open=97_500.00,
        high=97_620.50,
        low=97_410.30,
        close=97_580.00,
        volume=3.14159,
        pair="BTC/USDT",
        timeframe="1m",
        is_closed=True,
    )


@pytest.fixture
def sample_position() -> Position:
    """An open BTC/USDT long position."""
    return Position(
        pair="BTC/USDT",
        side="BUY",
        entry_price=97_500.00,
        quantity=0.001,
        entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        stop_loss=96_037.50,  # -1.5%
        trailing_active=False,
        trailing_high=0.0,
        take_profit_levels=[],
        current_pnl_pct=0.0,
        status=PositionStatus.OPEN,
        entry_reason="MSB_BREAK",
    )


@pytest.fixture
def sample_trade() -> Trade:
    """A completed BTC/USDT trade (round-trip)."""
    return Trade(
        pair="BTC/USDT",
        side="BUY",
        entry_price=97_500.00,
        exit_price=98_100.00,
        quantity=0.001,
        entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        exit_time=datetime(2026, 2, 10, 12, 45, 0, tzinfo=timezone.utc),
        pnl_usdt=0.60,
        pnl_pct=0.6154,
        fees=0.02,
        strategy_name="MSB Glissant",
        entry_reason="MSB_BREAK",
        exit_reason="TRAILING_STOP",
    )


@pytest.fixture
def sample_strategy_config() -> StrategyConfig:
    """MSB Glissant strategy configuration dict-style."""
    return StrategyConfig(
        name="MSB Glissant",
        version="1.0",
        description="Sliding Market Structure Break strategy for BTC/USDT",
        pairs=["BTC/USDT"],
        timeframe="5m",
        entry_conditions={
            "logic": "AND",
            "conditions": [
                {
                    "indicator": "heikin_ashi",
                    "params": {"timeframe": "5m"},
                    "operator": "is_green",
                },
                {
                    "indicator": "bollinger",
                    "params": {"period": 20, "std_dev": 2.0},
                    "operator": "touch_lower",
                },
                {
                    "indicator": "msb_glissant",
                    "params": {},
                    "operator": "break_above",
                },
            ],
        },
        exit_conditions={
            "logic": "OR",
            "conditions": [
                {
                    "indicator": "heikin_ashi",
                    "params": {"timeframe": "5m"},
                    "operator": "is_red",
                },
            ],
        },
        filters={
            "ema_trend": {"indicator": "ema", "params": {"period": 50}, "operator": "price_above"},
            "trading_hours": {"start": "08:00", "end": "22:00", "timezone": "UTC"},
        },
        risk={
            "stop_loss_pct": 1.5,
            "trailing_activation_pct": 0.6,
            "trailing_distance_pct": 0.3,
            "take_profit_levels": [{"pct": 1.0, "close_pct": 50.0}],
            "max_position_size_pct": 10.0,
        },
        indicators_needed=[
            "heikin_ashi", "bollinger", "msb_glissant", "ema",
        ],
        is_active=True,
    )


@pytest.fixture
def sample_risk_limits() -> RiskLimits:
    """Conservative risk limits for testing."""
    return RiskLimits(
        max_positions=3,
        max_exposure_pct=30.0,
        max_daily_loss_pct=3.0,
        max_drawdown_pct=10.0,
        position_size_pct=10.0,
        max_daily_trades=15,
    )
