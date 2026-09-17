"""
Application settings.

Rules enforced here (Instructions Section 18 VALIDATION; SKILL —
Production Backend Engineering "NEVER ... exposer secrets"):

  - Nothing is hardcoded. Every value is sourced from the environment
    (or a mounted secrets file via `_file` suffix support in
    pydantic-settings), with safe non-secret defaults only for local dev
    convenience (e.g. default ports).
  - This module never logs its own values. Call sites must not dump
    `Settings().model_dump()` into logs — see
    infrastructure/observability/logging.py for the redaction policy.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OKAPI_",
        extra="ignore",
    )

    # --- Service identity ---
    service_name: str = "okapi-copilot"
    environment: str = Field(default="local")  # local | staging | production
    contract_version: str = "1"

    # --- HTTP ---
    http_host: str = "0.0.0.0"
    http_port: int = 8000

    # --- SurrealDB (Document 2 Section 6 reference stack) ---
    surrealdb_url: str = "ws://surrealdb:8000/rpc"
    surrealdb_namespace: str = "okapi"
    surrealdb_database: str = "copilot"
    surrealdb_username: str = ""
    surrealdb_password: str = ""

    # --- Redis (cache contract, Document 9 Section 61) ---
    redis_url: str = "redis://redis:6379/0"

    # --- RabbitMQ / event broker (Document 9 Section 31) ---
    broker_url: str = "amqp://guest:guest@rabbitmq:5672/"

    # --- Keycloak (Document 9 Section 12) ---
    keycloak_issuer_url: str = ""
    keycloak_audience: str = "okapi-copilot"

    # --- Observability (Document 2 Section 6: OpenTelemetry) ---
    otel_exporter_endpoint: str = ""
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
