from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from src.api.schemas import (
    ConfigResponse,
    OpportunitiesResponse,
    StatusResponse,
    build_opportunities_response,
)

if TYPE_CHECKING:
    from src.core.app import App

router = APIRouter()


def _get_app(request: Request) -> "App":
    return request.app.state.screener_app


@router.get("/opportunities", response_model=OpportunitiesResponse)
async def get_opportunities(request: Request) -> OpportunitiesResponse:
    app = _get_app(request)
    ts = app.last_updated_at.isoformat() if app.last_updated_at is not None else None
    return build_opportunities_response(app.last_validated, updated_at=ts)


@router.get("/config", response_model=ConfigResponse)
async def get_config(request: Request) -> ConfigResponse:
    app = _get_app(request)
    s = app.settings
    return ConfigResponse(
        api_host=s.api_host,
        api_port=s.api_port,
        min_score_bps=s.min_score_bps,
        min_volume_24h=s.min_volume_24h,
        min_open_interest=s.min_open_interest,
        min_persistence_hours=s.min_persistence_hours,
        anti_churn_cooldown_s=s.anti_churn_cooldown_s,
        anti_churn_score_multiplier=s.anti_churn_score_multiplier,
        hl_fee_per_side=s.hl_fee_per_side,
        lighter_fee_per_side=s.lighter_fee_per_side,
        expected_hold_hours=s.expected_hold_hours,
        basis_weight=s.basis_weight,
        loop_interval_s=s.loop_interval_s,
        stale_data_s=s.stale_data_s,
    )


@router.get("/status", response_model=StatusResponse)
async def get_status(request: Request) -> StatusResponse:
    app = _get_app(request)
    now = datetime.now(timezone.utc)
    uptime_s = (now - app.started_at).total_seconds()
    return StatusResponse(
        uptime_s=round(uptime_s, 3),
        started_at=app.started_at.isoformat(),
        last_updated_at=app.last_updated_at.isoformat() if app.last_updated_at else None,
        last_poll_started_at=app.last_poll_started_at.isoformat() if app.last_poll_started_at else None,
        last_poll_finished_at=app.last_poll_finished_at.isoformat() if app.last_poll_finished_at else None,
        last_poll_duration_ms=round(app.last_poll_duration_ms, 3)
        if app.last_poll_duration_ms is not None
        else None,
        poll_count_total=app.poll_count_total,
        poll_count_success=app.poll_count_success,
        poll_count_failed=app.poll_count_failed,
        exchange_last_ok=app.exchange_last_ok,
    )
