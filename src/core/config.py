from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Screener
    min_score_bps: float = 5.0
    min_volume_24h: float = 100_000.0
    min_persistence_hours: float = 0.0
    hl_fee_per_side: float = 0.035
    aster_fee_per_side: float = 0.05
    expected_hold_hours: float = 72.0
    basis_weight: float = 0.5
    loop_interval_s: int = 10
    stale_data_s: float = 30.0

    # Exchanges
    hl_base_url: str = "https://api.hyperliquid.xyz"
    hl_ws_url: str = "wss://api.hyperliquid.xyz/ws"
    aster_base_url: str = "https://fapi.asterdex.com"
    aster_ws_url: str = "wss://fstream.asterdex.com/ws"

    # Resilience
    http_timeout: float = 10.0
    http_max_retries: int = 3

    model_config = {"env_prefix": "ARB_"}
