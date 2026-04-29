"""Template for risk gate rejection notification."""


def format_risk_gate_rejected(
    symbol: str,
    rule_id: str = "",
    rule_name: str = "",
    reason: str = "",
    value: float | str = "",
    threshold: float | str = "",
    **kwargs,
) -> str:
    return (
        f"\u26d4 TRADE REJET\u00c9 \u2014 {symbol}\n"
        f"Gate    : {rule_id} \u2014 {rule_name}\n"
        f"Raison  : {reason or 'N/A'}\n"
        f"Valeur  : {value} (seuil: {threshold})"
    )
