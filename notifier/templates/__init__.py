"""Notification message templates."""

from notifier.templates.trade_opened import format_trade_opened
from notifier.templates.trade_closed import format_trade_closed
from notifier.templates.risk_gate_rejected import format_risk_gate_rejected
from notifier.templates.daily_report import format_daily_report
from notifier.templates.bot_halted import format_bot_halted

__all__ = [
    "format_trade_opened",
    "format_trade_closed",
    "format_risk_gate_rejected",
    "format_daily_report",
    "format_bot_halted",
]
