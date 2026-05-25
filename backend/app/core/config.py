from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "Doc-Hub"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    API_DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    AUTH_DISABLED: bool = False

    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "documents"
    SUPABASE_SIGNED_URL_EXPIRES: int = Field(default=3600, ge=60, le=604800)

    # Database (local postgres OR Supabase connection string)
    DATABASE_URL: PostgresDsn | str = "postgresql://dochub:dochub@localhost:5432/dochub"

    # Redis
    REDIS_URL: RedisDsn | str = "redis://localhost:6379/0"

    # Graph DB
    GRAPH_DB_URL: str = "redis://localhost:6380"
    GRAPH_DB_NAME: str = "dochub_knowledge"
    GRAPH_DB_ENABLED: bool = False

    # Observability (OpenTelemetry → Grafana Cloud Tempo)
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_GRAFANA_INSTANCE_ID: str = ""
    OTEL_GRAFANA_API_TOKEN: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # AI (Phase 1 — used by workers later)
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 1536
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"

    # Ingestion
    INGESTION_CHUNK_SIZE: int = Field(default=512, ge=128, le=8192)
    INGESTION_CHUNK_OVERLAP: int = Field(default=64, ge=0, le=512)
    INGESTION_AUTO_START: bool = True

    # Ingestion 2.0
    TRIPLE_EXTRACTION_ENABLED: bool = False
    TRIPLE_EXTRACTION_MODEL: str = "gpt-4o-mini"
    CONFIDENCE_THRESHOLD: float = 0.6

    # Provenance
    PROVENANCE_ENABLED: bool = True

    # Extended Parsers
    AUDIO_TRANSCRIPTION_ENABLED: bool = False
    MAX_DOCUMENT_SIZE_MB: int = 25
    MAX_AUDIO_SIZE_MB: int = 100
    SUPPORTED_AUDIO_FORMATS: str = "mp3,mp4,m4a,wav,webm,ogg"

    # RAG / Chat
    RAG_TOP_K: int = Field(default=8, ge=1, le=20)
    RAG_VECTOR_WEIGHT: float = Field(default=0.7, ge=0.0, le=1.0)
    RAG_MAX_CONTEXT_CHARS: int = Field(default=12000, ge=1000, le=100000)

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1)

    # Personal pilot
    PILOT_INVITE_REQUIRED: bool = True
    PILOT_ADMIN_EMAILS: str = ""
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_ROLE_KEY)

    @property
    def redis_configured(self) -> bool:
        return bool(self.REDIS_URL)

    @property
    def graph_configured(self) -> bool:
        return self.GRAPH_DB_ENABLED and bool(self.GRAPH_DB_URL)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def audio_enabled(self) -> bool:
        return self.AUDIO_TRANSCRIPTION_ENABLED and bool(self.OPENAI_API_KEY)

    @property
    def max_document_bytes(self) -> int:
        return self.MAX_DOCUMENT_SIZE_MB * 1024 * 1024

    @property
    def max_audio_bytes(self) -> int:
        return self.MAX_AUDIO_SIZE_MB * 1024 * 1024

    @property
    def auth_disabled(self) -> bool:
        """Dev/test only — never enable in production."""
        return self.AUTH_DISABLED and self.ENVIRONMENT == "development"

    @property
    def pilot_admin_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.PILOT_ADMIN_EMAILS.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
