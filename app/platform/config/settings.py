"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://dl_user:dl_pass@db:5432/dl_origination"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    auth_enabled: bool = False

    # AI / LLM
    llm_provider: str = "mock"  # "claude" or "mock"
    llm_model: str = "claude-sonnet-4-6"
    llm_api_key: str = ""
    llm_rate_limit_rpm: int = 50

    # PitchBook
    pitchbook_provider: str = "mock"  # "rest", "mcp", or "mock"
    mcp_pitchbook_url: str = ""
    mcp_pitchbook_token: str = ""
    pitchbook_api_base_url: str = "https://api.pitchbook.com/v2"
    pitchbook_api_key: str = ""
    pitchbook_api_timeout: float = 30.0
    pitchbook_api_max_retries: int = 3

    # NAICS BizAPI
    bizapi_provider: str = "mock"  # "rest" or "mock"
    bizapi_api_url: str = "https://api.naics.com/v1"
    bizapi_sandbox_url: str = "https://sandbox.naics.com/v1"
    bizapi_username: str = ""
    bizapi_password: str = ""
    bizapi_use_sandbox: bool = True
    bizapi_timeout: float = 15.0
    bizapi_max_retries: int = 3
    bizapi_rate_limit_rps: float = 3.0

    # S&P Capital IQ
    capitaliq_provider: str = "mock"  # "rest" or "mock"
    capitaliq_api_url: str = ""
    capitaliq_api_key: str = ""
    capitaliq_timeout: float = 30.0
    capitaliq_max_retries: int = 3
    capitaliq_skip_if_pb_complete: bool = True

    # AI confidence
    ai_confidence_auto_accept_threshold: float = 0.85

    # Storage
    storage_backend: str = "local"  # "local" or "s3"
    storage_path: str = "./data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
