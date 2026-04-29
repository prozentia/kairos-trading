"""Template for trade opened notification."""


def format_trade_opened(
    symbol: str,
    setup_type: str = "",
    confidence: float = 0.0,
    reward_risk: float = 0.0,
    entry_price: float = 0.0,
    stop_loss: float = 0.0,
    take_profit: float = 0.0,
    agent_scores: dict[str, float] | None = None,
    **kwargs,
) -> str:
    sl_pct = abs((stop_loss - entry_price) / entry_price * 100) if entry_price else 0
    tp_pct = abs((take_profit - entry_price) / entry_price * 100) if entry_price else 0
    scores = agent_scores or {}

    return (
        f"\U0001f7e2 TRADE OUVERT \u2014 {symbol}\n"
        f"Setup   : {setup_type or 'N/A'}\n"
        f"Conf.   : {confidence:.0f}%  |  R/R : {reward_risk:.2f}\n"
        f"Entr\u00e9e  : {entry_price:,.2f} USDT\n"
        f"SL      : {stop_loss:,.2f} (-{sl_pct:.2f}%)\n"
        f"TP      : {take_profit:,.2f} (+{tp_pct:.2f}%)\n"
        f"\U0001f4ca Agents : "
        f"T:{scores.get('technical', 0):.2f} | "
        f"M:{scores.get('momentum', 0):.2f} | "
        f"C:{scores.get('context', 0):.2f} | "
        f"R:{scores.get('risk', 0):.2f}"
    )
