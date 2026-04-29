"""Template for trade closed notification."""


def format_trade_closed(
    symbol: str,
    pnl: float = 0.0,
    pnl_pct: float = 0.0,
    duration: str = "",
    exit_reason: str = "",
    entry_price: float = 0.0,
    exit_price: float = 0.0,
    **kwargs,
) -> str:
    emoji = "\u2705" if pnl >= 0 else "\u274c"
    sign = "+" if pnl >= 0 else ""

    return (
        f"{emoji} TRADE FERM\u00c9 \u2014 {symbol}\n"
        f"PnL     : {sign}{pnl:.2f} USDT ({sign}{pnl_pct:.2f}%)\n"
        f"Dur\u00e9e   : {duration or 'N/A'}\n"
        f"Sortie  : {exit_reason or 'N/A'}\n"
        f"Entr\u00e9e  : {entry_price:,.2f} \u2192 Sortie : {exit_price:,.2f}"
    )
