from __future__ import annotations

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from telegram import Update

from ppai.capture.application.capture_service import CaptureService
from ppai.capture.infrastructure.dynamodb_dedup_repo import DynamoDBDedupRepository
from ppai.capture.infrastructure.dynamodb_event_repo import DynamoDBEventRepository
from ppai.capture.infrastructure.dynamodb_task_repo import DynamoDBTaskStateRepository
from ppai.capture.infrastructure.telegram_adapter import TelegramAdapter
from ppai.decision.application.decision_service import DecisionService
from ppai.decision.domain.scoring_engine import ScoringEngine
from ppai.decision.infrastructure.decision_telegram_adapter import DecisionTelegramAdapter
from ppai.decision.infrastructure.dynamodb_cycle_repo import DynamoDBCycleRepository
from ppai.push.application.nudge_scheduler import NudgeScheduler
from ppai.push.application.nudge_service import NudgeService
from ppai.push.infrastructure.cycle_event_repo import DynamoDBCycleEventRepository
from ppai.push.infrastructure.dynamodb_preferences_repo import DynamoDBPreferencesRepository
from ppai.push.infrastructure.config_telegram_adapter import ConfigTelegramAdapter
from ppai.push.infrastructure.telegram_push_adapter import TelegramPushAdapter
from ppai.shared.infrastructure.config import get_settings
from ppai.shared.infrastructure.dynamodb_client import get_dynamodb_resource, table_name
from ppai.shared.infrastructure.logging import setup_logging
from ppai.shared.infrastructure.rate_limiter import InMemoryRateLimiter
from ppai.shared.infrastructure.user_registry import UserRegistry

logger = logging.getLogger(__name__)


def build_app() -> Application:
    settings = get_settings()

    dynamodb = get_dynamodb_resource(settings.aws_region, settings.dynamodb_endpoint_url)
    task_table        = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "tasks"))
    event_table       = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "events"))
    dedup_table       = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "dedup"))
    cycle_table       = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "cycles"))
    preferences_table = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "preferences"))

    task_repo    = DynamoDBTaskStateRepository(task_table)
    event_repo   = DynamoDBEventRepository(event_table)
    dedup_repo   = DynamoDBDedupRepository(dedup_table, settings)
    cycle_repo   = DynamoDBCycleRepository(cycle_table)
    prefs_repo   = DynamoDBPreferencesRepository(preferences_table)
    cycle_event_repo = DynamoDBCycleEventRepository(cycle_table)

    # UOW-01: Capture
    capture_service = CaptureService(
        task_repo=task_repo,
        event_repo=event_repo,
        dedup_repo=dedup_repo,
        active_task_limit=settings.active_task_limit,
    )

    # UOW-02: Decision — invalidate Top 3 cache after each capture
    decision_service = DecisionService(
        task_repo=task_repo,
        cycle_repo=cycle_repo,
        scoring_engine=ScoringEngine(),
    )
    capture_service.on_task_captured = decision_service.invalidate_cache

    rate_limiter = InMemoryRateLimiter(
        max_requests=settings.rate_limit_per_minute,
        window_seconds=60,
    )

    user_registry = UserRegistry()

    capture_adapter  = TelegramAdapter(capture_service, rate_limiter, user_registry)
    decision_adapter = DecisionTelegramAdapter(decision_service, user_registry)
    config_adapter   = ConfigTelegramAdapter(prefs_repo)

    # UOW-03: Push & Scheduling
    telegram_push = TelegramPushAdapter(bot_token=settings.telegram_bot_token)
    nudge_service = NudgeService(
        prefs_repo=prefs_repo,
        cycle_event_repo=cycle_event_repo,
        task_repo=task_repo,
        telegram_port=telegram_push,
        decision_service=decision_service,
    )
    nudge_scheduler = NudgeScheduler(
        nudge_service=nudge_service,
        user_ids_provider=user_registry.get_all,
    )

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # UOW-01: free-text capture
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, capture_adapter.message_handler)
    )

    # UOW-02: /top3 command + inline keyboard callbacks
    application.add_handler(CommandHandler("top3", decision_adapter.top3_handler))
    application.add_handler(
        CallbackQueryHandler(
            decision_adapter.callback_handler,
            pattern=r"^(done|snooze|clarify):.+$",
        )
    )

    # UOW-03: /config command for nudge preferences
    application.add_handler(CommandHandler("config", config_adapter.config_handler))

    application.add_error_handler(capture_adapter.error_handler)

    nudge_scheduler.start()

    return application


def main() -> None:
    setup_logging()
    logger.info("Starting PPAI bot in polling mode...")

    application = build_app()
    application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
