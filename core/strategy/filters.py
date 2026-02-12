"""Post-signal filters applied after the strategy evaluator produces a BUY.

These are portfolio-level and timing-level checks that can reject an
otherwise valid signal.  Each filter returns the signal unchanged if it
passes, or a NO_SIGNAL if filtered out.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.models import Candle, Signal, SignalType, StrategyConfig


class SignalFilter:
    """Post-signal filters to reduce false signals."""

    # ------------------------------------------------------------------
    # Individual filters
    # ------------------------------------------------------------------

    def filter_by_trend(
        self,
        signal: Signal,
        candles: list[Candle],
        period: int = 50,
    ) -> Signal:
        """Only take signals in trend direction.

        For BUY signals, the current price must be above the SMA of
        *period* candles.  For SELL signals, price must be below.

        Args:
            signal: The incoming signal.
            candles: Recent candle history (oldest first).
            period: SMA lookback period (default 50).

        Returns:
            Original signal if it passes, NO_SIGNAL otherwise.
        """
        if not signal.is_actionable:
            return signal

        if len(candles) < period:
            # Not enough data to compute trend; let signal through.
            return signal

        closes = [c.close for c in candles[-period:]]
        sma = sum(closes) / len(closes)

        if signal.type == SignalType.BUY and signal.price < sma:
            return self._no_signal(signal, f"Trend filter: price {signal.price:.2f} < SMA({period}) {sma:.2f}")

        if signal.type == SignalType.SELL and signal.price > sma:
            return self._no_signal(signal, f"Trend filter: price {signal.price:.2f} > SMA({period}) {sma:.2f}")

        return signal

    def filter_by_volume(
        self,
        signal: Signal,
        candles: list[Candle],
        min_ratio: float = 1.5,
    ) -> Signal:
        """Reject if current volume is too low relative to the average.

        Args:
            signal: The incoming signal.
            candles: Recent candle history (oldest first).
            min_ratio: Minimum volume / average volume ratio (default 1.5).

        Returns:
            Original signal if it passes, NO_SIGNAL otherwise.
        """
        if not signal.is_actionable or not candles:
            return signal

        # Use the last candle's volume as "current".
        current_volume = candles[-1].volume

        # Average volume over the available candles (excluding the last).
        if len(candles) < 2:
            return signal

        avg_volume = sum(c.volume for c in candles[:-1]) / (len(candles) - 1)

        if avg_volume <= 0.0:
            return signal

        ratio = current_volume / avg_volume
        if ratio < min_ratio:
            return self._no_signal(
                signal,
                f"Volume filter: ratio {ratio:.2f} < min {min_ratio:.2f}",
            )

        return signal

    def filter_by_volatility(
        self,
        signal: Signal,
        candles: list[Candle],
        min_atr: float | None = None,
        max_atr: float | None = None,
        atr_period: int = 14,
    ) -> Signal:
        """Reject in extreme volatility conditions.

        Computes a simple ATR over *atr_period* candles and checks
        that it falls within [min_atr, max_atr].

        Args:
            signal: The incoming signal.
            candles: Recent candle history (oldest first).
            min_atr: Minimum acceptable ATR (None = no lower bound).
            max_atr: Maximum acceptable ATR (None = no upper bound).
            atr_period: Number of candles for ATR computation.

        Returns:
            Original signal if it passes, NO_SIGNAL otherwise.
        """
        if not signal.is_actionable:
            return signal

        if len(candles) < atr_period + 1:
            return signal

        if min_atr is None and max_atr is None:
            return signal

        # Simple ATR: average of (high - low) over the period.
        atr = sum(c.high - c.low for c in candles[-atr_period:]) / atr_period

        if min_atr is not None and atr < min_atr:
            return self._no_signal(
                signal,
                f"Volatility filter: ATR {atr:.2f} < min {min_atr:.2f}",
            )

        if max_atr is not None and atr > max_atr:
            return self._no_signal(
                signal,
                f"Volatility filter: ATR {atr:.2f} > max {max_atr:.2f}",
            )

        return signal

    def filter_by_time(
        self,
        signal: Signal,
        excluded_hours: list[int] | None = None,
    ) -> Signal:
        """No trading during specific hours.

        Args:
            signal: The incoming signal.
            excluded_hours: List of UTC hours during which trading is
                blocked (e.g. [0, 1, 2, 3, 4, 5] for overnight).

        Returns:
            Original signal if it passes, NO_SIGNAL otherwise.
        """
        if not signal.is_actionable:
            return signal

        if excluded_hours is None or not excluded_hours:
            return signal

        current_hour = signal.timestamp.hour

        if current_hour in excluded_hours:
            return self._no_signal(
                signal,
                f"Time filter: hour {current_hour} is excluded.",
            )

        return signal

    def filter_by_spread(
        self,
        signal: Signal,
        bid: float,
        ask: float,
        max_spread_pct: float = 0.1,
    ) -> Signal:
        """Reject if the bid-ask spread is too wide.

        Args:
            signal: The incoming signal.
            bid: Current best bid price.
            ask: Current best ask price.
            max_spread_pct: Maximum spread as a percentage of mid price.

        Returns:
            Original signal if it passes, NO_SIGNAL otherwise.
        """
        if not signal.is_actionable:
            return signal

        if bid <= 0.0 or ask <= 0.0:
            return signal

        mid = (bid + ask) / 2.0
        spread_pct = ((ask - bid) / mid) * 100.0

        if spread_pct > max_spread_pct:
            return self._no_signal(
                signal,
                f"Spread filter: spread {spread_pct:.4f}% > max {max_spread_pct:.4f}%",
            )

        return signal

    def filter_by_consecutive(
        self,
        signal: Signal,
        recent_signals: list[Signal],
        max_same: int = 3,
    ) -> Signal:
        """Avoid overtrading in the same direction.

        Rejects a signal if the last *max_same* signals were all in
        the same direction.

        Args:
            signal: The incoming signal.
            recent_signals: List of recent signals (most recent last).
            max_same: Max consecutive signals in the same direction.

        Returns:
            Original signal if it passes, NO_SIGNAL otherwise.
        """
        if not signal.is_actionable or not recent_signals:
            return signal

        if len(recent_signals) < max_same:
            return signal

        # Check the last max_same signals.
        last_n = recent_signals[-max_same:]
        if all(s.type == signal.type for s in last_n):
            return self._no_signal(
                signal,
                f"Consecutive filter: {max_same} consecutive {signal.type.value} signals.",
            )

        return signal

    # ------------------------------------------------------------------
    # Master filter chain
    # ------------------------------------------------------------------

    def apply_filters(
        self,
        signal: Signal,
        candles: list[Candle],
        filter_config: dict[str, Any],
    ) -> Signal:
        """Apply all configured filters to a signal.

        The filter_config dict maps filter names to their parameters.
        Supported keys:
            trend:        {"period": int}
            volume:       {"min_ratio": float}
            volatility:   {"min_atr": float, "max_atr": float, "period": int}
            time:         {"excluded_hours": list[int]}
            spread:       {"bid": float, "ask": float, "max_spread_pct": float}
            consecutive:  {"recent_signals": list[Signal], "max_same": int}

        Args:
            signal: The incoming signal.
            candles: Recent candle history.
            filter_config: Configuration for each filter.

        Returns:
            The signal (possibly unchanged) or NO_SIGNAL.
        """
        if not signal.is_actionable:
            return signal

        # Trend filter.
        if "trend" in filter_config:
            cfg = filter_config["trend"]
            signal = self.filter_by_trend(
                signal, candles, period=cfg.get("period", 50),
            )
            if not signal.is_actionable:
                return signal

        # Volume filter.
        if "volume" in filter_config:
            cfg = filter_config["volume"]
            signal = self.filter_by_volume(
                signal, candles, min_ratio=cfg.get("min_ratio", 1.5),
            )
            if not signal.is_actionable:
                return signal

        # Volatility filter.
        if "volatility" in filter_config:
            cfg = filter_config["volatility"]
            signal = self.filter_by_volatility(
                signal, candles,
                min_atr=cfg.get("min_atr"),
                max_atr=cfg.get("max_atr"),
                atr_period=cfg.get("period", 14),
            )
            if not signal.is_actionable:
                return signal

        # Time filter.
        if "time" in filter_config:
            cfg = filter_config["time"]
            signal = self.filter_by_time(
                signal, excluded_hours=cfg.get("excluded_hours"),
            )
            if not signal.is_actionable:
                return signal

        # Spread filter.
        if "spread" in filter_config:
            cfg = filter_config["spread"]
            signal = self.filter_by_spread(
                signal,
                bid=cfg.get("bid", 0.0),
                ask=cfg.get("ask", 0.0),
                max_spread_pct=cfg.get("max_spread_pct", 0.1),
            )
            if not signal.is_actionable:
                return signal

        # Consecutive filter.
        if "consecutive" in filter_config:
            cfg = filter_config["consecutive"]
            signal = self.filter_by_consecutive(
                signal,
                recent_signals=cfg.get("recent_signals", []),
                max_same=cfg.get("max_same", 3),
            )
            if not signal.is_actionable:
                return signal

        return signal

    # ------------------------------------------------------------------
    # Legacy API (PostSignalFilters compatibility)
    # ------------------------------------------------------------------

    def check_all(
        self,
        strategy_config: StrategyConfig,
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Run every enabled filter. Returns (True, "") if all pass.

        This method provides backward compatibility with the original
        PostSignalFilters interface.

        Args:
            strategy_config: Strategy definition (filters section).
            context: Runtime context with current state data.

        Returns:
            (True, "") on success, (False, reason) on first failure.
        """
        filters = strategy_config.filters
        if not filters:
            return True, ""

        checks = [
            ("ema_trend", self._check_ema_trend),
            ("trading_hours", self._check_trading_hours),
            ("loss_cooldown", self._check_loss_cooldown),
            ("max_daily_trades", self._check_max_daily_trades),
            ("max_daily_loss", self._check_max_daily_loss),
        ]

        for filter_key, check_fn in checks:
            if filter_key in filters:
                cfg = filters[filter_key]
                # Support both {"enabled": true, ...} and direct config.
                if isinstance(cfg, dict) and not cfg.get("enabled", True):
                    continue
                passed, reason = check_fn(cfg, context)
                if not passed:
                    return False, reason

        return True, ""

    # ------------------------------------------------------------------
    # Legacy filter implementations
    # ------------------------------------------------------------------

    def _check_ema_trend(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Reject BUY if price is below a macro EMA."""
        ema_value = context.get("ema_trend_value", 0.0)
        price = context.get("price", 0.0)

        if ema_value <= 0.0 or price <= 0.0:
            return True, ""

        if price < ema_value:
            return False, (
                f"EMA trend filter: price {price:.2f} < EMA {ema_value:.2f}."
            )

        return True, ""

    def _check_trading_hours(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Reject BUY outside configured trading hours."""
        start_hour = config.get("start_hour", 0)
        end_hour = config.get("end_hour", 24)
        timestamp: datetime | None = context.get("timestamp")

        if timestamp is None:
            return True, ""

        current_hour = timestamp.hour

        if start_hour <= end_hour:
            # Normal range (e.g. 8 to 22).
            if not (start_hour <= current_hour < end_hour):
                return False, (
                    f"Trading hours filter: hour {current_hour} "
                    f"outside [{start_hour}, {end_hour})."
                )
        else:
            # Overnight range (e.g. 22 to 8).
            if end_hour <= current_hour < start_hour:
                return False, (
                    f"Trading hours filter: hour {current_hour} "
                    f"outside [{start_hour}, {end_hour})."
                )

        return True, ""

    def _check_loss_cooldown(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Reject BUY if a loss occurred within the cooldown window."""
        cooldown_minutes = config.get("cooldown_minutes", 0)
        last_loss_time: datetime | None = context.get("last_loss_time")
        timestamp: datetime | None = context.get("timestamp")

        if cooldown_minutes <= 0 or last_loss_time is None or timestamp is None:
            return True, ""

        elapsed = timestamp - last_loss_time
        if elapsed < timedelta(minutes=cooldown_minutes):
            remaining = cooldown_minutes - (elapsed.total_seconds() / 60.0)
            return False, (
                f"Loss cooldown: {remaining:.0f} min remaining "
                f"(cooldown={cooldown_minutes} min)."
            )

        return True, ""

    def _check_max_daily_trades(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Reject BUY if the daily trade count limit is reached."""
        max_trades = config.get("max_trades", 0)
        daily_count = context.get("daily_trade_count", 0)

        if max_trades <= 0:
            return True, ""

        if daily_count >= max_trades:
            return False, (
                f"Max daily trades: {daily_count}/{max_trades} reached."
            )

        return True, ""

    def _check_max_daily_loss(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Reject BUY if daily cumulative loss exceeds threshold."""
        max_loss_pct = config.get("max_loss_pct", 0.0)
        daily_pnl_pct = context.get("daily_pnl_pct", 0.0)

        if max_loss_pct <= 0.0:
            return True, ""

        if daily_pnl_pct < 0 and abs(daily_pnl_pct) >= max_loss_pct:
            return False, (
                f"Max daily loss: {daily_pnl_pct:.2f}% "
                f"(limit: -{max_loss_pct:.2f}%)."
            )

        return True, ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _no_signal(original: Signal, reason: str = "") -> Signal:
        """Create a NO_SIGNAL preserving context from the original."""
        return Signal(
            type=SignalType.NO_SIGNAL,
            pair=original.pair,
            timeframe=original.timeframe,
            price=original.price,
            timestamp=original.timestamp,
            strategy_name=original.strategy_name,
            reason=reason,
        )
