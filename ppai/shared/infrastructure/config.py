from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    dynamodb_table_prefix: str = "ppai"
    active_task_limit: int = 50
    dedup_window_seconds: int = 300
    rate_limit_per_minute: int = 10
    aws_region: str = "us-east-1"
    # LocalStack: set to http://localhost:4566 for local development, None for AWS prod
    dynamodb_endpoint_url: str | None = None
    # Google Calendar OAuth (ER2)
    google_client_id: str = ""
    google_client_secret: str = ""
    fernet_encryption_key: str = ""

    model_config = {"env_prefix": "", "case_sensitive": False, "env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
