from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Screener
    min_score_bps: float = 5.0
    min_volume_24h: float = 100_000.0
    min_open_interest: float = 0.0
    min_persistence_hours: float = 0.0
    anti_churn_cooldown_s: float = 14400.0
    anti_churn_score_multiplier: float = 1.5
    hl_fee_per_side: float = 0.035
    lighter_fee_per_side: float = 0.0
    expected_hold_hours: float = 72.0
    basis_weight: float = 0.5
    liquidity_weight: float = 0.0
    timing_penalty_bps_per_hour: float = 0.0
    max_funding_timing_asymmetry_hours: float = 0.0
    max_basis_bps: float = 0.0
    max_basis_trend_bps_per_tick: float = 3.0
    loop_interval_s: float = 30.0
    stale_data_s: float = 35.0

    # API server
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Exchanges
    hl_base_url: str = "https://api.hyperliquid.xyz"
    lighter_base_url: str = "https://mainnet.zklighter.elliot.ai"

    # Resilience
    http_timeout: float = 10.0
    http_max_retries: int = 3

    model_config = {"env_prefix": "ARB_", "env_file": ".env", "env_file_encoding": "utf-8"}
