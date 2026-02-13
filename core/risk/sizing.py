"""Position sizing algorithms.

Standalone functions that compute how much capital to allocate to a
single trade.  All functions are pure and stateless.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from core.models import RiskLimits


# Trust levels map score ranges to maximum capital fractions.
TRUST_LEVELS: dict[str, tuple[float, float, float]] = {
    # name: (min_score, max_score, max_capital_fraction)
    "CRAWL":  (0.0, 40.0, 0.00),
    "WALK":   (40.0, 65.0, 0.25),
    "RUN":    (65.0, 80.0, 0.50),
    "SPRINT": (80.0, 100.0, 0.80),
}


@dataclass(frozen=True)
class SymbolInfo:
    """Minimal symbol/pair trading constraints from the exchange."""

    min_qty: float = 0.0
    max_qty: float = float("inf")
    step_size: float = 0.0
    min_notional: float = 0.0
    tick_size: float = 0.01


class PositionSizer:
    """Calculate position size based on risk parameters."""

    def __init__(self, risk_limits: RiskLimits) -> None:
        self.risk_limits = risk_limits

    # ------------------------------------------------------------------
    # Core sizing methods
    # ------------------------------------------------------------------

    @staticmethod
    def fixed_percentage(capital: float, pct: float) -> float:
        """Allocate a fixed percentage of capital.

        Args:
            capital: Total available capital (quote currency).
            pct: Percentage to allocate (e.g. 10.0 for 10%).

        Returns:
            Position size in quote currency.
        """
        if capital <= 0.0 or pct <= 0.0:
            return 0.0
        return capital * (pct / 100.0)

    @staticmethod
    def kelly_criterion(
        win_rate: float,
        risk_reward: float,
        capital: float,
        fraction: float = 0.5,
    ) -> float:
        """Kelly Criterion position sizing.

        Calculates the theoretically optimal bet size.  *fraction* is
        a safety multiplier (half-Kelly by default) to reduce variance.

        f* = (p * b - q) / b
        where p = win_rate, q = 1 - p, b = risk_reward ratio.

        Args:
            win_rate: Historical win rate (0.0 - 1.0).
            risk_reward: Average win / average loss ratio.
            capital: Total available capital.
            fraction: Kelly fraction multiplier (0.5 = half-Kelly).

        Returns:
            Position size in quote currency. Returns 0 if Kelly is negative
            (i.e. the system has negative expectancy).
        """
        if capital <= 0.0 or win_rate <= 0.0 or risk_reward <= 0.0:
            return 0.0
        if win_rate >= 1.0:
            # Cannot have 100% win rate in Kelly formula context.
            win_rate = 0.999

        q = 1.0 - win_rate
        kelly_f = (win_rate * risk_reward - q) / risk_reward

        # Negative Kelly means negative expectancy: do not trade.
        if kelly_f <= 0.0:
            return 0.0

        return capital * kelly_f * fraction

    @staticmethod
    def atr_based(
        capital: float,
        atr: float,
        risk_pct: float,
        price: float = 1.0,
    ) -> float:
        """ATR-based position sizing.

        Sizes the position so that a 1-ATR adverse move equals
        *risk_pct* of capital.  Larger ATR = smaller position.

        Args:
            capital: Total available capital.
            atr: Current ATR value.
            risk_pct: Maximum risk per trade as percentage (e.g. 1.0).
            price: Current asset price (for converting to quantity).

        Returns:
            Position size in quote currency.
        """
        if capital <= 0.0 or atr <= 0.0 or risk_pct <= 0.0 or price <= 0.0:
            return 0.0

        risk_amount = capital * (risk_pct / 100.0)
        # Quantity that risks risk_amount on a 1-ATR move.
        quantity = risk_amount / atr
        # Convert to quote currency.
        return quantity * price

    # ------------------------------------------------------------------
    # Risk-based sizing
    # ------------------------------------------------------------------

    def calculate_size(
        self,
        balance: float,
        entry_price: float,
        stop_loss_price: float,
        symbol_info: SymbolInfo | None = None,
    ) -> float:
        """Calculate position size based on risk per trade.

        Risk per trade = balance * position_size_pct (from RiskLimits).
        Size = risk_amount / abs(entry_price - stop_loss_price).
        Result is clamped to symbol constraints.

        Args:
            balance: Available balance in quote currency.
            entry_price: Planned entry price.
            stop_loss_price: Planned stop-loss price.
            symbol_info: Exchange constraints (min/max/step).

        Returns:
            Position size in base currency (quantity).
        """
        if balance <= 0.0 or entry_price <= 0.0:
            return 0.0

        price_diff = abs(entry_price - stop_loss_price)
        if price_diff <= 0.0:
            return 0.0

        risk_amount = balance * (self.risk_limits.position_size_pct / 100.0)
        quantity = risk_amount / price_diff

        # Clamp to symbol info if provided.
        if symbol_info is not None:
            quantity = self._clamp_to_symbol(quantity, entry_price, symbol_info)

        return quantity

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr_value: float,
        multiplier: float = 2.0,
    ) -> float:
        """Calculate ATR-based stop-loss price for a long position.

        SL = entry_price - (atr_value * multiplier).

        Args:
            entry_price: The entry price of the trade.
            atr_value: Current ATR value.
            multiplier: ATR multiplier (default 2.0).

        Returns:
            Stop-loss price. Always >= 0.
        """
        if entry_price <= 0.0 or atr_value <= 0.0 or multiplier <= 0.0:
            return 0.0
        sl = entry_price - (atr_value * multiplier)
        return max(sl, 0.0)

    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        risk_reward_ratio: float = 2.0,
    ) -> float:
        """Calculate take-profit price based on risk/reward.

        TP = entry_price + (entry_price - stop_loss) * risk_reward_ratio.

        Args:
            entry_price: The entry price.
            stop_loss: The stop-loss price.
            risk_reward_ratio: Desired R:R ratio (default 2.0).

        Returns:
            Take-profit price.
        """
        if entry_price <= 0.0 or risk_reward_ratio <= 0.0:
            return 0.0

        risk = abs(entry_price - stop_loss)
        return entry_price + (risk * risk_reward_ratio)

    def validate_order(
        self,
        balance: float,
        size: float,
        price: float,
    ) -> tuple[bool, str]:
        """Check whether a proposed order is valid given the balance.

        Args:
            balance: Available balance in quote currency.
            size: Proposed quantity (base currency).
            price: Proposed entry price.

        Returns:
            (True, "") if valid, (False, reason) otherwise.
        """
        if size <= 0.0:
            return False, "Position size must be positive."

        if price <= 0.0:
            return False, "Price must be positive."

        notional = size * price
        if notional > balance:
            return False, (
                f"Insufficient balance: need {notional:.2f} "
                f"but only have {balance:.2f}."
            )

        # Check against max exposure.
        max_exposure = balance * (self.risk_limits.max_exposure_pct / 100.0)
        if notional > max_exposure:
            return False, (
                f"Order notional {notional:.2f} exceeds max exposure "
                f"{max_exposure:.2f} ({self.risk_limits.max_exposure_pct}% of balance)."
            )

        return True, ""

    def adjust_for_trust_level(self, size: float, trust_score: float) -> float:
        """Reduce position size based on trust score.

        Trust levels:
            CRAWL  (0-40):  0% capital -> force dry run.
            WALK   (40-65): 25% max capital.
            RUN    (65-80): 50% max capital.
            SPRINT (80-100): 80% max capital.

        Args:
            size: Original position size (quote currency or quantity).
            trust_score: Current trust score (0-100).

        Returns:
            Adjusted position size.
        """
        if size <= 0.0:
            return 0.0

        trust_score = max(0.0, min(100.0, trust_score))
        max_fraction = 0.0

        for _name, (low, high, frac) in TRUST_LEVELS.items():
            if low <= trust_score < high:
                max_fraction = frac
                break
        else:
            # Score == 100 falls into SPRINT.
            if trust_score >= 100.0:
                max_fraction = 0.80

        return size * max_fraction

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp_to_symbol(
        quantity: float,
        price: float,
        info: SymbolInfo,
    ) -> float:
        """Clamp quantity to exchange symbol constraints."""
        # Round to step size.
        if info.step_size > 0.0:
            steps = math.floor(quantity / info.step_size)
            quantity = steps * info.step_size
            # Fix floating-point precision (e.g. 0.000060000001 -> 0.00006)
            precision = max(0, -int(math.floor(math.log10(info.step_size))))
            quantity = round(quantity, precision)

        # Enforce min/max quantity.
        if info.min_qty > 0.0 and quantity < info.min_qty:
            return 0.0
        if info.max_qty < float("inf") and quantity > info.max_qty:
            quantity = info.max_qty

        # Enforce min notional.
        if info.min_notional > 0.0 and (quantity * price) < info.min_notional:
            return 0.0

        return quantity
