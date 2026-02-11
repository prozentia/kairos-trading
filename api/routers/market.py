"""Market data router - price, candles, ticker, order book."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.auth.jwt import get_current_active_user

router = APIRouter()


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
    # TODO: call market_service.get_price(pair)
    return {"pair": pair.upper(), "price": 0.0, "timestamp": None}


@router.get("/prices")
async def get_all_prices(
    current_user: dict = Depends(get_current_active_user),
):
    """Get current prices for all active pairs.

    Returns a list of {pair, price, change_24h_pct}.
    """
    # TODO: call market_service.get_all_prices()
    return []


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
    # TODO: call market_service.get_candles(pair, timeframe, limit)
    return []


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
    # TODO: call market_service.get_ticker(pair)
    return {
        "pair": pair.upper(),
        "price": 0.0,
        "high_24h": 0.0,
        "low_24h": 0.0,
        "volume_24h": 0.0,
        "change_24h_pct": 0.0,
    }


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
    # TODO: call market_service.get_orderbook(pair, depth)
    return {"pair": pair.upper(), "bids": [], "asks": []}
