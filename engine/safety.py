"""Safety layer — kill switch, latency guard, anomaly detection.

Protects the trading engine from abnormal conditions by halting
trading when thresholds are exceeded.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from core.models import BotState

logger = logging.getLogger(__name__)

# Defaults
MAX_ACCEPTABLE_LATENCY_MS = 500
MAX_ATR_ZSCORE = 3.0
MAX_DAILY_LOSS_PCT = 2.0
FLASH_CRASH_PCT = 5.0  # Price drop > 5% in 1m = flash crash


@dataclass
class SafetyConfig:
    """Configuration for safety checks."""

    max_latency_ms: int = MAX_ACCEPTABLE_LATENCY_MS
    max_atr_zscore: float = MAX_ATR_ZSCORE
    max_daily_loss_pct: float = MAX_DAILY_LOSS_PCT
    flash_crash_pct: float = FLASH_CRASH_PCT
    kill_switch: bool = False


class SafetyManager:
    """Monitors safety conditions and halts trading if needed."""

    def __init__(self, config: SafetyConfig | None = None) -> None:
        self._config = config or SafetyConfig()
        self._state: BotState = BotState.ACTIVE
        self._halt_reason: str = ""
        self._halt_time: float = 0.0
        self._price_history: list[tuple[float, float]] = []  # (timestamp, price)

    @property
    def state(self) -> BotState:
        return self._state

    @property
    def halt_reason(self) -> str:
        return self._halt_reason

    def is_halted(self) -> bool:
        """Return True if trading is halted."""
        return self._state == BotState.HALTED or self._config.kill_switch

    def is_safe_mode(self) -> bool:
        """Return True if in safe mode (reduced activity)."""
        return self._state == BotState.SAFE_MODE

    def check_all(
        self,
        latency_ms: int = 0,
        atr_zscore: float = 0.0,
        daily_pnl_pct: float = 0.0,
        current_price: float = 0.0,
    ) -> BotState:
        """Run all safety checks and return updated state.

        Args:
            latency_ms: Current WebSocket latency.
            atr_zscore: Current ATR z-score.
            daily_pnl_pct: Today's PnL percentage.
            current_price: Current market price.

        Returns:
            Current BotState after checks.
        """
        if self._config.kill_switch:
            self.halt("Kill switch activated")
            return self._state

        if self.check_latency(latency_ms):
            return self._state

        if self.check_daily_loss(daily_pnl_pct):
            return self._state

        if self.check_atr_anomaly(atr_zscore):
            return self._state

        if current_price > 0:
            if self.check_flash_crash(current_price):
                return self._state

        # All clear — restore to active if previously in safe mode
        if self._state == BotState.SAFE_MODE:
            self._state = BotState.ACTIVE
            logger.info("Safety checks passed — restored to ACTIVE")

        return self._state

    def check_latency(self, latency_ms: int) -> bool:
        """Check WebSocket latency. Returns True if halted."""
        if latency_ms > self._config.max_latency_ms:
            self._state = BotState.SAFE_MODE
            logger.warning(
                "High latency detected: %d ms (max: %d ms) — entering SAFE_MODE",
                latency_ms, self._config.max_latency_ms,
            )
            return True
        return False

    def check_daily_loss(self, daily_pnl_pct: float) -> bool:
        """Check if daily loss limit exceeded. Returns True if halted."""
        loss = abs(min(0.0, daily_pnl_pct))
        if loss >= self._config.max_daily_loss_pct:
            self.halt(f"Daily loss limit reached: -{loss:.2f}%")
            return True
        return False

    def check_atr_anomaly(self, atr_zscore: float) -> bool:
        """Check for abnormal volatility. Returns True if action taken."""
        if atr_zscore > self._config.max_atr_zscore:
            self._state = BotState.SAFE_MODE
            logger.warning(
                "ATR z-score anomaly: %.2f (max: %.2f) — entering SAFE_MODE",
                atr_zscore, self._config.max_atr_zscore,
            )
            return True
        return False

    def check_flash_crash(self, current_price: float) -> bool:
        """Detect flash crash by price drop percentage. Returns True if halted."""
        now = time.time()
        self._price_history.append((now, current_price))

        # Keep only last 60 seconds
        self._price_history = [(t, p) for t, p in self._price_history if now - t <= 60]

        if len(self._price_history) < 2:
            return False

        oldest_price = self._price_history[0][1]
        if oldest_price == 0:
            return False

        drop_pct = ((oldest_price - current_price) / oldest_price) * 100
        if drop_pct >= self._config.flash_crash_pct:
            self.halt(f"Flash crash detected: -{drop_pct:.2f}% in 60s")
            return True

        return False

    def halt(self, reason: str) -> None:
        """Immediately halt all trading."""
        self._state = BotState.HALTED
        self._halt_reason = reason
        self._halt_time = time.time()
        logger.critical("TRADING HALTED: %s", reason)

    def resume(self) -> None:
        """Resume trading after a halt."""
        if self._state == BotState.HALTED:
            logger.info("Trading resumed from halt (was: %s)", self._halt_reason)
            self._state = BotState.ACTIVE
            self._halt_reason = ""

    def activate_kill_switch(self) -> None:
        """Activate the kill switch."""
        self._config.kill_switch = True
        self.halt("Kill switch activated")

    def deactivate_kill_switch(self) -> None:
        """Deactivate the kill switch."""
        self._config.kill_switch = False
        self.resume()

    def status(self) -> dict[str, Any]:
        """Return current safety status."""
        return {
            "state": self._state.value,
            "halt_reason": self._halt_reason,
            "halt_time": self._halt_time,
            "kill_switch": self._config.kill_switch,
        }
