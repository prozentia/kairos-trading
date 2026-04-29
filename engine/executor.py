"""Order executor — manages the lifecycle of trade orders.

Handles entry orders (market buy), stop-loss placement,
take-profit placement, and order status tracking.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OrderResult:
    """Result of an order execution."""

    order_id: str = ""
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    quantity: float = 0.0
    price: float = 0.0
    status: str = "NEW"  # NEW | FILLED | PARTIALLY_FILLED | CANCELLED | FAILED
    timestamp: int = 0
    fees: float = 0.0
    slippage_bps: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status,
            "timestamp": self.timestamp,
            "fees": self.fees,
            "slippage_bps": self.slippage_bps,
            "error": self.error,
        }


class OrderExecutor:
    """Executes orders through the exchange adapter.

    Manages the full order lifecycle:
    1. Place market entry order
    2. Place stop-loss order
    3. Place take-profit order(s)
    4. Track and update order status
    """

    def __init__(self, exchange_rest: Any, dry_run: bool = True) -> None:
        self._exchange = exchange_rest
        self._dry_run = dry_run
        self._pending_orders: dict[str, OrderResult] = {}

    async def execute_market_buy(
        self,
        symbol: str,
        quantity: float,
        reference_price: float,
    ) -> OrderResult:
        """Place a market buy order.

        Args:
            symbol: Trading pair (e.g. BTCUSDT).
            quantity: Order quantity.
            reference_price: Expected entry price for slippage calculation.

        Returns:
            OrderResult with execution details.
        """
        if self._dry_run:
            return self._simulate_fill(symbol, "BUY", "MARKET", quantity, reference_price)

        try:
            result = await self._exchange.place_market_order(symbol, "BUY", quantity)
            fill_price = float(result.get("avgPrice", reference_price))
            slippage = abs(fill_price - reference_price) / reference_price * 10000

            return OrderResult(
                order_id=str(result.get("orderId", "")),
                symbol=symbol,
                side="BUY",
                order_type="MARKET",
                quantity=quantity,
                price=fill_price,
                status="FILLED",
                timestamp=int(time.time()),
                fees=float(result.get("commission", 0)),
                slippage_bps=round(slippage, 2),
            )
        except Exception as e:
            logger.error("Market buy failed for %s: %s", symbol, e)
            return OrderResult(
                symbol=symbol, side="BUY", order_type="MARKET",
                quantity=quantity, status="FAILED", error=str(e),
                timestamp=int(time.time()),
            )

    async def place_stop_loss(
        self,
        symbol: str,
        stop_price: float,
        quantity: float,
    ) -> OrderResult:
        """Place a stop-loss order."""
        if self._dry_run:
            return self._simulate_fill(symbol, "SELL", "STOP_MARKET", quantity, stop_price)

        try:
            result = await self._exchange.place_stop_order(symbol, stop_price, quantity)
            return OrderResult(
                order_id=str(result.get("orderId", "")),
                symbol=symbol,
                side="SELL",
                order_type="STOP_MARKET",
                quantity=quantity,
                price=stop_price,
                status="NEW",
                timestamp=int(time.time()),
            )
        except Exception as e:
            logger.error("Stop-loss placement failed: %s", e)
            return OrderResult(
                symbol=symbol, side="SELL", order_type="STOP_MARKET",
                status="FAILED", error=str(e), timestamp=int(time.time()),
            )

    async def place_take_profit(
        self,
        symbol: str,
        price: float,
        quantity: float,
    ) -> OrderResult:
        """Place a take-profit limit order."""
        if self._dry_run:
            return self._simulate_fill(symbol, "SELL", "LIMIT", quantity, price)

        try:
            result = await self._exchange.place_limit_order(symbol, price, quantity)
            return OrderResult(
                order_id=str(result.get("orderId", "")),
                symbol=symbol,
                side="SELL",
                order_type="LIMIT",
                quantity=quantity,
                price=price,
                status="NEW",
                timestamp=int(time.time()),
            )
        except Exception as e:
            logger.error("Take-profit placement failed: %s", e)
            return OrderResult(
                symbol=symbol, side="SELL", order_type="LIMIT",
                status="FAILED", error=str(e), timestamp=int(time.time()),
            )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an existing order."""
        if self._dry_run:
            return True
        try:
            await self._exchange.cancel_order(symbol, order_id)
            return True
        except Exception as e:
            logger.error("Cancel order failed: %s", e)
            return False

    def _simulate_fill(
        self, symbol: str, side: str, order_type: str,
        quantity: float, price: float,
    ) -> OrderResult:
        """Simulate an order fill in dry-run mode."""
        return OrderResult(
            order_id=f"DRY-{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status="FILLED" if order_type == "MARKET" else "NEW",
            timestamp=int(time.time()),
            fees=0.0,
            slippage_bps=0.0,
        )
