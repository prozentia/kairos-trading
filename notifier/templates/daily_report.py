"""Template for daily performance report notification."""


def format_daily_report(
    date: str,
    trades_count: int = 0,
    wins: int = 0,
    losses: int = 0,
    win_rate: float = 0.0,
    pnl: float = 0.0,
    pnl_pct: float = 0.0,
    avg_rr: float = 0.0,
    max_dd: float = 0.0,
    **kwargs,
) -> str:
    sign = "+" if pnl >= 0 else ""

    return (
        f"\U0001f4cb RAPPORT DU JOUR \u2014 {date}\n"
        f"Trades  : {trades_count} ({wins}W / {losses}L)\n"
        f"Win Rate: {win_rate:.1f}%\n"
        f"PnL     : {sign}{pnl:.2f} USDT ({sign}{pnl_pct:.2f}%)\n"
        f"R moyen : {avg_rr:.2f}\n"
        f"Drawdown: {max_dd:.2f}%"
    )
