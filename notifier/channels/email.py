"""Email notification channel.

Sends emails via SMTP (async). Supports plain HTML emails and
pre-formatted daily report emails.
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)


class EmailChannel:
    """Sends email notifications via SMTP."""

    def __init__(
        self,
        smtp_host: str = "",
        smtp_port: int = 587,
        from_addr: str = "",
        password: str = "",
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_addr = from_addr
        self.password = password

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    async def send(self, to: str, subject: str, body_html: str) -> bool:
        """Send an HTML email.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body_html: HTML body content.

        Returns:
            True on success, False on failure.
        """
        if not self.smtp_host or not self.from_addr:
            logger.error("Email channel not configured (missing SMTP host or from address)")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to
        msg.attach(MIMEText(body_html, "html"))

        # TODO: use aiosmtplib for async SMTP
        # async with aiosmtplib.SMTP(
        #     hostname=self.smtp_host,
        #     port=self.smtp_port,
        #     use_tls=True,
        # ) as smtp:
        #     await smtp.login(self.from_addr, self.password)
        #     await smtp.send_message(msg)
        raise NotImplementedError(
            "Async email sending not yet implemented. "
            "Requires aiosmtplib package."
        )

    async def send_daily_report(self, to: str, stats: dict[str, Any]) -> bool:
        """Send a daily trading report email.

        Args:
            to: Recipient email address.
            stats: Dictionary with daily statistics.

        Returns:
            True on success, False on failure.
        """
        subject = f"Kairos Trading - Daily Report ({stats.get('date', 'Today')})"
        body = self._build_daily_report_html(stats)
        return await self.send(to, subject, body)

    # -----------------------------------------------------------------
    # HTML templates
    # -----------------------------------------------------------------

    @staticmethod
    def _build_daily_report_html(stats: dict[str, Any]) -> str:
        """Build HTML body for the daily report email."""
        total_trades = stats.get("total_trades", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        win_rate = stats.get("win_rate", 0)
        pnl = stats.get("total_pnl_usdt", 0)
        pnl_pct = stats.get("total_pnl_pct", 0)
        balance = stats.get("balance", 0)

        pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
        pnl_sign = "+" if pnl >= 0 else ""

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1e293b;">Kairos Trading - Daily Report</h2>
            <hr style="border: 1px solid #e2e8f0;">

            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr>
                    <td style="padding: 8px; font-weight: bold;">Trades</td>
                    <td style="padding: 8px;">{total_trades} ({wins}W / {losses}L)</td>
                </tr>
                <tr style="background: #f8fafc;">
                    <td style="padding: 8px; font-weight: bold;">Win Rate</td>
                    <td style="padding: 8px;">{win_rate:.1f}%</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold;">P&amp;L</td>
                    <td style="padding: 8px; color: {pnl_color}; font-weight: bold;">
                        {pnl_sign}${pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%)
                    </td>
                </tr>
                <tr style="background: #f8fafc;">
                    <td style="padding: 8px; font-weight: bold;">Balance</td>
                    <td style="padding: 8px;">${balance:,.2f}</td>
                </tr>
            </table>

            <hr style="border: 1px solid #e2e8f0;">
            <p style="color: #94a3b8; font-size: 12px;">
                Kairos Trading Platform - Automated notification
            </p>
        </body>
        </html>
        """
