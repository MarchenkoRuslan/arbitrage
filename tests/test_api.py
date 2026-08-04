import asyncio
import contextlib
import json
import socket
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import uvicorn
import websockets
from httpx import ASGITransport, AsyncClient

from src.api.server import create_api
from src.api.schemas import build_opportunities_response
from src.core.app import App
from src.core.config import Settings
from src.core.models import ArbitrageOpportunity, ValidatedOpportunity


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _settings() -> Settings:
    return Settings(
        min_score_bps=0.0, min_volume_24h=0.0, min_persistence_hours=0.0,
        hl_fee_per_side=0.0, lighter_fee_per_side=0.0,
        expected_hold_hours=72.0, basis_weight=0.0, stale_data_s=60.0,
    )


def _validated_opp(symbol: str = "BTC", score: float = 50.0) -> ValidatedOpportunity:
    return ValidatedOpportunity(
        opportunity=ArbitrageOpportunity(
            symbol=symbol,
            long_exchange="hyperliquid",
            short_exchange="lighter",
            persistence_hours=6.0,
            long_rate_apr=5.0,
            short_rate_apr=20.0,
            funding_diff_apr=15.0,
            funding_edge_bps=57.0,
            basis_bps=10.0,
            basis_bonus_bps=5.0,
            fee_impact_bps=7.0,
            min_profitable_hours=10.0,
            hours_to_breakeven=None,
            combined_score=score,
        ),
        status="ready",
        reasons=[],
    )


@pytest.fixture
def app() -> App:
    a = App(_settings())
    a.hl.get_market_data = AsyncMock(return_value=({}, {}))
    a.lighter.get_market_data = AsyncMock(return_value=({}, {}))
    return a


@pytest.fixture
def fastapi_app(app: App):
    return create_api(app)


@pytest.mark.asyncio
async def test_get_opportunities_returns_empty_before_poll(app: App, fastapi_app) -> None:
    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/opportunities")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["ready_count"] == 0
    assert data["opportunities"] == []


@pytest.mark.asyncio
async def test_get_opportunities_returns_stored_results(app: App, fastapi_app) -> None:
    app.last_validated = [_validated_opp("ETH", 80.0), _validated_opp("BTC", 50.0)]
    app.last_updated_at = datetime.now(timezone.utc)
    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/opportunities")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["ready_count"] == 2
    assert data["updated_at"] is not None
    assert data["opportunities"][0]["symbol"] == "ETH"
    assert data["opportunities"][0]["combined_score"] == 80.0
    assert data["opportunities"][0]["status"] == "ready"
    assert data["opportunities"][1]["symbol"] == "BTC"


@pytest.mark.asyncio
async def test_get_config_returns_current_settings(app: App, fastapi_app) -> None:
    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/config")

    assert resp.status_code == 200
    data = resp.json()
    assert data["api_host"] == "127.0.0.1"
    assert data["api_port"] == 8000
    assert data["min_score_bps"] == 0.0
    assert data["expected_hold_hours"] == 72.0
    assert data["hl_fee_per_side"] == 0.0
    assert data["loop_interval_s"] == 30.0


@pytest.mark.asyncio
async def test_get_status_returns_runtime_metrics(app: App, fastapi_app) -> None:
    app.poll_count_total = 3
    app.poll_count_success = 2
    app.poll_count_failed = 1
    app.exchange_last_ok["hyperliquid"] = True
    app.exchange_last_ok["lighter"] = False

    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["uptime_s"] >= 0
    assert data["started_at"] is not None
    assert data["poll_count_total"] == 3
    assert data["poll_count_success"] == 2
    assert data["poll_count_failed"] == 1
    assert data["exchange_last_ok"]["hyperliquid"] is True
    assert data["exchange_last_ok"]["lighter"] is False


@pytest.mark.asyncio
async def test_openapi_contract_contains_phase2_paths_and_status_schema(app: App, fastapi_app) -> None:
    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")

    assert resp.status_code == 200
    spec = resp.json()
    paths = spec["paths"]
    assert "/opportunities" in paths
    assert "/config" in paths
    assert "/status" in paths

    schemas = spec["components"]["schemas"]
    assert "OpportunitiesResponse" in schemas
    assert "ConfigResponse" in schemas
    assert "StatusResponse" in schemas
    assert "OpportunityItem" in schemas
    assert schemas["OpportunityItem"]["properties"]["status"]["enum"] == [
        "ready",
        "watching",
        "blocked",
    ]


@pytest.mark.asyncio
async def test_poll_once_updates_status_and_opportunities(fastapi_app) -> None:
    """Integration: a real poll cycle updates both /status and /opportunities."""
    from decimal import Decimal

    from src.core.models import FundingRate, Ticker

    app: App = fastapi_app.state.screener_app
    now = datetime.now(timezone.utc)
    app.hl.get_market_data = AsyncMock(return_value=(
        {"BTC": FundingRate(symbol="BTC", period_hours=1, apr=5.0, timestamp=now)},
        {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), index_price=Decimal("100"), volume_24h=1e6)},
    ))
    app.lighter.get_market_data = AsyncMock(return_value=(
        {"BTC": FundingRate(symbol="BTC", period_hours=1, apr=50.0, timestamp=now)},
        {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), index_price=Decimal("100"), volume_24h=1e6)},
    ))

    await app.poll_once()

    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        status = (await client.get("/status")).json()
        opps = (await client.get("/opportunities")).json()

    assert status["poll_count_success"] == 1
    assert status["last_poll_duration_ms"] is not None
    assert status["exchange_last_ok"]["hyperliquid"] is True
    assert status["exchange_last_ok"]["lighter"] is True
    assert opps["count"] >= 1
    assert opps["updated_at"] is not None


@pytest.mark.asyncio
async def test_ws_receives_broadcast_on_update(app: App, fastapi_app) -> None:
    app.last_validated = [_validated_opp("SOL", 60.0)]
    port = _get_free_port()

    config = uvicorn.Config(
        fastapi_app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        lifespan="on",
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    try:
        deadline = asyncio.get_running_loop().time() + 5
        while not server.started:
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("Uvicorn server did not start within 5 seconds")
            await asyncio.sleep(0.01)

        async with websockets.connect(f"ws://127.0.0.1:{port}/ws/opportunities") as ws:
            payload = build_opportunities_response(app.last_validated).model_dump()
            await fastapi_app.state.ws_manager.broadcast(payload)
            message = await asyncio.wait_for(ws.recv(), timeout=2)
            data = json.loads(message)
            assert data["count"] == 1
            assert data["opportunities"][0]["symbol"] == "SOL"
    finally:
        server.should_exit = True
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=3)
