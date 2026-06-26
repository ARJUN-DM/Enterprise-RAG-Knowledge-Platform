"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://rag_user:rag_password@localhost:5432/rag_platform"

    # LLM / Embedding
    llm_provider: str = "gemini"
    embedding_provider: str = "sentence-transformers"
    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-001"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # NVIDIA NIM (hosted, OpenAI-compatible)
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.3-70b-instruct"
    nvidia_max_tokens: int = 2048

    # Ollama (local LLM fallback)
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.2"

    # App
    log_level: str = "INFO"
    debug: bool = False
    embedding_dimensions: int = 768

    # MCP
    mcp_port: int = 8100

    # CORS — comma-separated list of origins
    cors_origins_str: str = "http://localhost:3000,http://localhost:8100"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]


settings = Settings()
