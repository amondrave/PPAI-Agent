from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    dynamodb_table_prefix: str = "ppai"
    active_task_limit: int = 50
    dedup_window_seconds: int = 300
    rate_limit_per_minute: int = 10
    aws_region: str = "us-east-1"

    model_config = {"env_prefix": "", "case_sensitive": False}


def get_settings() -> Settings:
    return Settings()
