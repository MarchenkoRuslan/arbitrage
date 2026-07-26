from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Screener filters
    min_net_apr: float = 0.05
    min_volume_24h: float = 100_000.0
    max_apr_ratio_1h_24h: float = 0.0
    max_apr_ratio_24h_7d: float = 0.0
    loop_interval_s: int = 10
    stale_data_s: float = 30.0

    # VOOI Perps API
    vooi_api_url: str = "https://perps-api.vooi.io"
    vooi_bearer_token: str = ""
    vooi_target_exchanges: str = "hyperliquid,lighter"
    vooi_opportunity_limit: int = 100

    # Resilience
    http_timeout: float = 10.0
    http_max_retries: int = 3

    model_config = {"env_prefix": "ARB_"}
