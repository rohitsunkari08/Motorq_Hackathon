"""Agent Configuration Module."""

import os
from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    AGENT_PORT: int = 8001
    API_URL: str = os.getenv("API_URL", "http://localhost:8000/api/v1")
    POSTGRES_URL: str = os.getenv(
        "POSTGRES_URL",
        f"postgresql://evc:{os.getenv('PG_PASSWORD', 'change_me')}@localhost:5432/evc",
    )
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change_me_long_random")
    
    # LLM Provider settings per NOTE.md §4:
    # Gemini free tier via LiteLLM; fallback Groq free; fallback Ollama local.
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")
    
    # Guardrail settings per NOTE.md §6.6
    MAX_TOOL_CALLS_PER_TURN: int = 6
    TEMPERATURE: float = 0.0
    REQUEST_TIMEOUT_SECONDS: float = 15.0

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = AgentSettings()
