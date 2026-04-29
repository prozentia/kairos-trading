"""Template for bot halted alert notification."""


def format_bot_halted(
    reason: str = "",
    pnl_pct: float = 0.0,
    **kwargs,
) -> str:
    sign = "+" if pnl_pct >= 0 else ""

    return (
        f"\U0001f6a8 BOT SUSPENDU\n"
        f"Raison  : {reason or 'Inconnue'}\n"
        f"PnL     : {sign}{pnl_pct:.2f}%\n"
        f"Action  : Toutes les positions ferm\u00e9es"
    )
