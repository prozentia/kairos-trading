"""Tests for trade endpoints (list, get, record, stats).

All tests are skipped until the API router and database are wired up.
"""

from datetime import datetime, timezone

import pytest


@pytest.mark.skip(reason="API trade endpoints not implemented yet")
def test_list_trades(client, auth_headers):
    """GET /trades/ should return paginated trade list."""
    # response = await client.get("/trades/", headers=auth_headers)
    # assert response.status_code == 200
    # data = response.json()
    # assert "total" in data
    # assert "trades" in data
    # assert isinstance(data["trades"], list)
    # assert "page" in data
    # assert "per_page" in data


@pytest.mark.skip(reason="API trade endpoints not implemented yet")
def test_get_trade(client, auth_headers):
    """GET /trades/{id} should return a single trade."""
    # # First record a trade
    # trade_data = {
    #     "pair": "BTC/USDT",
    #     "side": "BUY",
    #     "entry_price": 97500.0,
    #     "exit_price": 98000.0,
    #     "quantity": 0.001,
    #     "entry_time": "2026-02-10T12:00:00Z",
    #     "exit_time": "2026-02-10T12:30:00Z",
    #     "pnl_usdt": 0.5,
    #     "pnl_pct": 0.51,
    #     "fees": 0.02,
    #     "strategy_name": "MSB Glissant",
    #     "entry_reason": "MSB_BREAK",
    #     "exit_reason": "TRAILING_STOP",
    # }
    # create_resp = await client.post("/trades/record-complete", json=trade_data, headers=auth_headers)
    # trade_id = create_resp.json()["id"]
    #
    # response = await client.get(f"/trades/{trade_id}", headers=auth_headers)
    # assert response.status_code == 200
    # assert response.json()["pair"] == "BTC/USDT"


@pytest.mark.skip(reason="API trade endpoints not implemented yet")
def test_record_trade(client, auth_headers):
    """POST /trades/record-complete should persist a trade."""
    # trade_data = {
    #     "pair": "BTC/USDT",
    #     "side": "BUY",
    #     "entry_price": 97500.0,
    #     "exit_price": 98100.0,
    #     "quantity": 0.001,
    #     "entry_time": "2026-02-10T12:00:00Z",
    #     "exit_time": "2026-02-10T12:45:00Z",
    #     "pnl_usdt": 0.6,
    #     "pnl_pct": 0.6154,
    #     "fees": 0.02,
    #     "strategy_name": "MSB Glissant",
    #     "entry_reason": "MSB_BREAK",
    #     "exit_reason": "TRAILING_STOP",
    # }
    # response = await client.post("/trades/record-complete", json=trade_data, headers=auth_headers)
    # assert response.status_code == 201
    # data = response.json()
    # assert data["pair"] == "BTC/USDT"
    # assert data["pnl_usdt"] == 0.6
    # assert "id" in data


@pytest.mark.skip(reason="API trade endpoints not implemented yet")
def test_trade_stats(client, auth_headers):
    """GET /trades/stats should return aggregated statistics."""
    # response = await client.get("/trades/stats", headers=auth_headers)
    # assert response.status_code == 200
    # data = response.json()
    # assert "total_trades" in data
    # assert "win_rate" in data
    # assert "total_pnl_usdt" in data
    # assert "profit_factor" in data
    # assert "winning_trades" in data
    # assert "losing_trades" in data
