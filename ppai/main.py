from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, MessageHandler, filters

from ppai.capture.application.capture_service import CaptureService
from ppai.capture.infrastructure.dynamodb_dedup_repo import DynamoDBDedupRepository
from ppai.capture.infrastructure.dynamodb_event_repo import DynamoDBEventRepository
from ppai.capture.infrastructure.dynamodb_task_repo import DynamoDBTaskStateRepository
from ppai.capture.infrastructure.telegram_adapter import TelegramAdapter
from ppai.shared.infrastructure.config import get_settings
from ppai.shared.infrastructure.dynamodb_client import get_dynamodb_resource, table_name
from ppai.shared.infrastructure.logging import setup_logging
from ppai.shared.infrastructure.rate_limiter import InMemoryRateLimiter

logger = logging.getLogger(__name__)


def build_app() -> Application:
    settings = get_settings()

    dynamodb = get_dynamodb_resource(settings.aws_region)
    task_table = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "tasks"))
    event_table = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "events"))
    dedup_table = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "dedup"))

    task_repo = DynamoDBTaskStateRepository(task_table)
    event_repo = DynamoDBEventRepository(event_table)
    dedup_repo = DynamoDBDedupRepository(dedup_table, settings)

    capture_service = CaptureService(
        task_repo=task_repo,
        event_repo=event_repo,
        dedup_repo=dedup_repo,
        active_task_limit=settings.active_task_limit,
    )

    rate_limiter = InMemoryRateLimiter(
        max_requests=settings.rate_limit_per_minute,
        window_seconds=60,
    )

    adapter = TelegramAdapter(capture_service, rate_limiter)

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, adapter.message_handler)
    )
    application.add_error_handler(adapter.error_handler)

    return application


def main() -> None:
    setup_logging()
    logger.info("Starting PPAI bot...")

    settings = get_settings()
    application = build_app()

    application.run_webhook(
        listen="0.0.0.0",
        port=8443,
        webhook_url=f"https://placeholder.execute-api.{settings.aws_region}.amazonaws.com/webhook",
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
