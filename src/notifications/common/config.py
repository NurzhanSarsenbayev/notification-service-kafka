from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # FastAPI
    project_name: str = "Notification API"
    api_v1_prefix: str = "/api/v1"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:29092"

    kafka_outbox_topic: str = "notifications.outbox"
    kafka_dlq_topic: str = "notifications.dlq"
    kafka_consumer_group: str = "notification-worker"

    # Postgres
    db_host: str = "notifications-db"
    db_port: int = 5432
    db_name: str = "notifications"
    db_user: str = "notifications"
    db_password: str = "notifications"

    db_echo: bool = False

    @property
    def db_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def db_asyncpg_dsn(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # Worker settings
    max_attempts: int = 3
    retry_delays_seconds_raw: str = "1,3,10"
    max_send_delay_seconds: int = 300

    # Auth service (optional). If unset/empty, worker falls back to fake contacts.
    auth_base_url: Optional[str] = None

    @property
    def retry_delays_seconds(self) -> List[float]:
        parts = [p.strip() for p in self.retry_delays_seconds_raw.split(",") if p.strip()]
        if not parts:
            raise ValueError(
                "RETRY_DELAYS_SECONDS_RAW is empty. Expected comma-separated numbers, e.g. '1,3,10'."
            )
        try:
            return [float(p) for p in parts]
        except ValueError as e:
            raise ValueError(
                "Invalid RETRY_DELAYS_SECONDS_RAW. Expected comma-separated numbers, e.g. '1,3,10'."
            ) from e

    # Scheduler settings
    api_base_url: str = "http://notifications-api:8000"
    scheduler_poll_interval_seconds: int = 60

    # Mailpit
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_from: str = "noreply@example.com"


settings = Settings()
