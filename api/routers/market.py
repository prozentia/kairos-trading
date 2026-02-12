"""Market data router - price, candles, ticker, order book."""

from fastapi import APIRouter, Depends, Query

from api.auth.jwt import get_current_active_user
from api.services.market_service import MarketService

router = APIRouter()

# Shared service instance (no DB dependency, optional Redis)
_market_service = MarketService()


# ---------------------------------------------------------------------------
# Spot price
# ---------------------------------------------------------------------------

@router.get("/price/{pair}")
async def get_price(
    pair: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Get the current price for a single pair.

    Returns: {"pair": "BTCUSDT", "price": 98250.50, "timestamp": "..."}
    """
    return await _market_service.get_price(pair)


@router.get("/prices")
async def get_all_prices(
    current_user: dict = Depends(get_current_active_user),
):
    """Get current prices for all active USDT pairs.

    Returns a list of {pair, price, change_24h_pct, volume_24h}.
    """
    return await _market_service.get_all_prices()


# ---------------------------------------------------------------------------
# Historical candles
# ---------------------------------------------------------------------------

@router.get("/candles/{pair}")
async def get_candles(
    pair: str,
    timeframe: str = Query("5m", description="Candle interval (1m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(200, ge=1, le=1000, description="Number of candles"),
    current_user: dict = Depends(get_current_active_user),
):
    """Get historical OHLCV candles for a pair.

    Returns a list of {timestamp, open, high, low, close, volume}.
    """
    return await _market_service.get_candles(pair, timeframe, limit)


# ---------------------------------------------------------------------------
# Ticker (24h stats)
# ---------------------------------------------------------------------------

@router.get("/ticker/{pair}")
async def get_ticker(
    pair: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Get 24h ticker statistics for a pair.

    Returns: {pair, price, high_24h, low_24h, volume_24h, change_24h_pct}.
    """
    return await _market_service.get_ticker(pair)


# ---------------------------------------------------------------------------
# Order book
# ---------------------------------------------------------------------------

@router.get("/orderbook/{pair}")
async def get_orderbook(
    pair: str,
    depth: int = Query(20, ge=5, le=100, description="Number of levels"),
    current_user: dict = Depends(get_current_active_user),
):
    """Get order book snapshot for a pair.

    Returns: {bids: [[price, qty], ...], asks: [[price, qty], ...]}.
    """
    return await _market_service.get_orderbook(pair, depth)
