"""Tests for trade endpoints (list, get, record, stats, export, journal).

Uses httpx AsyncClient with SQLite in-memory database.
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trade_payload(pair: str = "BTCUSDT", pnl: float = 5.0) -> dict:
    """Build a sample trade record payload."""
    return {
        "pair": pair,
        "side": "BUY",
        "entry_price": 97500.0,
        "exit_price": 98000.0,
        "quantity": 0.001,
        "entry_time": "2026-02-10T12:00:00",
        "exit_time": "2026-02-10T12:30:00",
        "pnl_usdt": pnl,
        "pnl_pct": 0.51,
        "fees": 0.02,
        "strategy_name": "MSB Glissant",
        "entry_reason": "MSB_BREAK",
        "exit_reason": "TRAILING_STOP",
    }


async def _register_and_login(client: AsyncClient) -> dict[str, str]:
    """Register a user, login, and return auth headers."""
    await client.post("/auth/register", json={
        "email": "trader@kairos.dev",
        "password": "SecureP@ss123",
        "username": "trader",
    })
    resp = await client.post("/auth/login", json={
        "email": "trader@kairos.dev",
        "password": "SecureP@ss123",
    })
    token = resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# List trades
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_trades_empty(client: AsyncClient):
    """GET /trades/ should return empty list when no trades exist."""
    headers = await _register_and_login(client)
    response = await client.get("/trades/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["trades"] == []
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_trades_with_data(client: AsyncClient, internal_headers: dict):
    """GET /trades/ should return trades after recording some."""
    headers = await _register_and_login(client)

    # Record trades via internal endpoint
    for i in range(3):
        await client.post(
            "/trades/record-complete",
            json=_trade_payload(pnl=float(i)),
            headers=internal_headers,
        )

    response = await client.get("/trades/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["trades"]) == 3


@pytest.mark.asyncio
async def test_list_trades_pagination(client: AsyncClient, internal_headers: dict):
    """GET /trades/ should respect pagination parameters."""
    headers = await _register_and_login(client)

    for i in range(5):
        await client.post(
            "/trades/record-complete",
            json=_trade_payload(pnl=float(i)),
            headers=internal_headers,
        )

    response = await client.get("/trades/?page=1&per_page=2", headers=headers)
    data = response.json()
    assert data["total"] == 5
    assert len(data["trades"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert data["pages"] == 3


@pytest.mark.asyncio
async def test_list_trades_filter_pair(client: AsyncClient, internal_headers: dict):
    """GET /trades/?pair=BTCUSDT should filter by pair."""
    headers = await _register_and_login(client)

    await client.post(
        "/trades/record-complete",
        json=_trade_payload(pair="BTCUSDT"),
        headers=internal_headers,
    )
    await client.post(
        "/trades/record-complete",
        json=_trade_payload(pair="ETHUSDT"),
        headers=internal_headers,
    )

    response = await client.get("/trades/?pair=BTCUSDT", headers=headers)
    data = response.json()
    assert data["total"] == 1
    assert data["trades"][0]["pair"] == "BTCUSDT"


# ---------------------------------------------------------------------------
# Get single trade
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_trade_by_id(client: AsyncClient, internal_headers: dict):
    """GET /trades/{id} should return a single trade."""
    headers = await _register_and_login(client)

    create_resp = await client.post(
        "/trades/record-complete",
        json=_trade_payload(),
        headers=internal_headers,
    )
    trade_id = create_resp.json()["id"]

    response = await client.get(f"/trades/{trade_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == trade_id
    assert data["pair"] == "BTCUSDT"


@pytest.mark.asyncio
async def test_get_trade_not_found(client: AsyncClient):
    """GET /trades/{id} with invalid ID should return 404."""
    headers = await _register_and_login(client)
    response = await client.get("/trades/nonexistent-uuid", headers=headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Record trade (internal)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_trade_success(client: AsyncClient, internal_headers: dict):
    """POST /trades/record-complete should persist a trade."""
    payload = _trade_payload()
    response = await client.post(
        "/trades/record-complete",
        json=payload,
        headers=internal_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["pair"] == "BTCUSDT"
    assert data["pnl_usdt"] == 5.0
    assert "id" in data


@pytest.mark.asyncio
async def test_record_trade_without_internal_token(client: AsyncClient):
    """POST /trades/record-complete without internal token should return 401."""
    response = await client.post(
        "/trades/record-complete",
        json=_trade_payload(),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_record_trade_wrong_internal_token(client: AsyncClient):
    """POST /trades/record-complete with wrong token should return 401."""
    response = await client.post(
        "/trades/record-complete",
        json=_trade_payload(),
        headers={"x-internal-token": "wrong-token"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Trade stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trade_stats_empty(client: AsyncClient):
    """GET /trades/stats with no trades should return zeroes."""
    headers = await _register_and_login(client)
    response = await client.get("/trades/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_trades"] == 0
    assert data["win_rate"] == 0.0
    assert data["total_pnl_usdt"] == 0.0


@pytest.mark.asyncio
async def test_trade_stats_with_data(client: AsyncClient, internal_headers: dict):
    """GET /trades/stats should compute correct stats."""
    headers = await _register_and_login(client)

    # Record 3 winning and 2 losing trades
    for pnl in [5.0, 10.0, 3.0, -2.0, -1.0]:
        payload = _trade_payload(pnl=pnl)
        payload["pnl_pct"] = pnl / 100
        await client.post(
            "/trades/record-complete",
            json=payload,
            headers=internal_headers,
        )

    response = await client.get("/trades/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_trades"] == 5
    assert data["winning_trades"] == 3
    assert data["losing_trades"] == 2
    assert data["win_rate"] == 60.0
    assert data["total_pnl_usdt"] == 15.0
    assert data["max_win_usdt"] == 10.0
    assert data["max_loss_usdt"] == -2.0
    assert data["profit_factor"] > 0


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_export_csv_empty(client: AsyncClient):
    """GET /trades/export/csv with no trades should return header only."""
    headers = await _register_and_login(client)
    response = await client.get("/trades/export/csv", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    content = response.text
    assert "id,pair,side" in content


@pytest.mark.asyncio
async def test_export_csv_with_data(client: AsyncClient, internal_headers: dict):
    """GET /trades/export/csv should include trade rows."""
    headers = await _register_and_login(client)

    await client.post(
        "/trades/record-complete",
        json=_trade_payload(),
        headers=internal_headers,
    )

    response = await client.get("/trades/export/csv", headers=headers)
    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert len(lines) == 2  # header + 1 data row
    assert "BTCUSDT" in lines[1]


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journal_crud(client: AsyncClient, internal_headers: dict):
    """POST and GET /trades/{id}/journal should work correctly."""
    headers = await _register_and_login(client)

    # Create a trade
    create_resp = await client.post(
        "/trades/record-complete",
        json=_trade_payload(),
        headers=internal_headers,
    )
    trade_id = create_resp.json()["id"]

    # Add journal entry
    journal_resp = await client.post(
        f"/trades/{trade_id}/journal",
        json={"notes": "Good entry, clean signal", "tags": ["clean", "trend"]},
        headers=headers,
    )
    assert journal_resp.status_code == 201
    entry = journal_resp.json()
    assert entry["notes"] == "Good entry, clean signal"
    assert entry["trade_id"] == trade_id

    # Get journal entries
    list_resp = await client.get(f"/trades/{trade_id}/journal", headers=headers)
    assert list_resp.status_code == 200
    entries = list_resp.json()
    assert len(entries) == 1
    assert entries[0]["notes"] == "Good entry, clean signal"


@pytest.mark.asyncio
async def test_journal_trade_not_found(client: AsyncClient):
    """POST /trades/{id}/journal for nonexistent trade should return 404."""
    headers = await _register_and_login(client)
    response = await client.post(
        "/trades/nonexistent-uuid/journal",
        json={"notes": "test"},
        headers=headers,
    )
    assert response.status_code == 404
