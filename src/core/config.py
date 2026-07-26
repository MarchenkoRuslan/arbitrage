from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    min_score_apr: float = 5.0
    fee_per_side: float = 0.05
    loop_interval_s: int = 30

    hl_base_url: str = "https://api.hyperliquid.xyz"
    aster_base_url: str = "https://fapi.asterdex.com"

    model_config = {"env_prefix": "ARB_"}


settings = Settings()
