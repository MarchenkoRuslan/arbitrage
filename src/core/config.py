from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Screener
    min_score_apr: float = 5.0
    fee_per_side: float = 0.05
    expected_hold_hours: float = 72.0
    basis_weight: float = 0.1
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
