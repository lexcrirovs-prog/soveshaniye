from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Bitrix24
    bitrix_webhook_url: str = ""

    # Database
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "call_analytics"
    db_user: str = "app"
    db_password: str = "changeme_db_password"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme_minio_password"
    minio_bucket: str = "call-recordings"
    minio_secure: bool = False

    # Whisper
    whisper_provider: str = "openai"  # "openai" (cloud API) or "local" (faster-whisper)
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Email / SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    notify_email_to: str = ""  # comma-separated

    # Features
    crm_auto_comment: bool = False  # Auto-post analysis to CRM deals
    telegram_notifications: bool = False
    email_notifications: bool = False
    low_score_alert_threshold: int = 4  # Alert when score below this

    # App
    secret_key: str = "changeme_secret_key"
    cors_origins: str = "http://localhost:3000,http://localhost:80"

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
