"""Application Configuration
Loads settings from environment variables or .env file.
"""

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


BASE_DIR = Path(__file__).resolve().parent.parent
CERTS_DIR = BASE_DIR / "certs"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "EV Fleet Charging & Battery-Health Copilot API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Databases
    POSTGRES_URL: str = Field(
        default_factory=lambda: os.getenv(
            "POSTGRES_URL",
            f"postgresql://evc:{os.getenv('PG_PASSWORD', 'change_me')}@localhost:5432/evc"
        )
    )
    CLICKHOUSE_HOST: str = Field(default_factory=lambda: os.getenv("CLICKHOUSE_HOST", "localhost"))
    CLICKHOUSE_PORT: int = Field(default_factory=lambda: int(os.getenv("CLICKHOUSE_PORT", "8123")))
    CLICKHOUSE_USER: str = Field(default_factory=lambda: os.getenv("CLICKHOUSE_USER", "evc"))
    CLICKHOUSE_PASSWORD: str = Field(default_factory=lambda: os.getenv("CH_PASSWORD", "change_me"))
    CLICKHOUSE_DB: str = Field(default_factory=lambda: os.getenv("CLICKHOUSE_DB", "evc"))

    REDIS_URL: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    # Security & JWT (RS256)
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    CERTS_DIR_PATH: str = str(CERTS_DIR)

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_TOKENS_PER_MINUTE: int = 120

    # Differential Privacy
    DP_DEFAULT_EPSILON: float = 1.0
    DP_K_ANONYMITY_FLOOR: int = 20
    DP_TENANT_BUDGET: float = 20.0

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
