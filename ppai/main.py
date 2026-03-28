from __future__ import annotations

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from telegram import Update

from ppai.calendar.application.block_planner import BlockPlanner
from ppai.calendar.application.calendar_service import CalendarService
from ppai.calendar.application.calendar_sync import CalendarSync
from ppai.calendar.application.category_classifier import CategoryClassifier
from ppai.calendar.application.google_oauth_service import GoogleOAuthService
from ppai.calendar.infrastructure.dynamodb_auth_repo import DynamoDBCalendarAuthRepository
from ppai.calendar.infrastructure.dynamodb_block_repo import DynamoDBTimeBlockRepository
from ppai.calendar.infrastructure.google_calendar_adapter import GoogleCalendarAdapter
from ppai.calendar.infrastructure.calendar_telegram_adapter import CalendarTelegramAdapter
from ppai.capture.application.capture_service import CaptureService
from ppai.capture.infrastructure.dynamodb_dedup_repo import DynamoDBDedupRepository
from ppai.capture.infrastructure.dynamodb_event_repo import DynamoDBEventRepository
from ppai.capture.infrastructure.dynamodb_task_repo import DynamoDBTaskStateRepository
from ppai.capture.infrastructure.telegram_adapter import TelegramAdapter
from ppai.decision.application.decision_service import DecisionService
from ppai.decision.domain.scoring_engine import ScoringEngine
from ppai.decision.infrastructure.decision_telegram_adapter import DecisionTelegramAdapter
from ppai.decision.infrastructure.dynamodb_cycle_repo import DynamoDBCycleRepository
from ppai.profile.application.onboarding_service import OnboardingService
from ppai.profile.application.profile_service import ProfileService
from ppai.profile.infrastructure.dynamodb_profile_repo import DynamoDBProfileRepository
from ppai.profile.infrastructure.onboarding_telegram_adapter import OnboardingTelegramAdapter
from ppai.profile.infrastructure.profile_telegram_adapter import ProfileTelegramAdapter
from ppai.push.application.block_reminder_service import BlockReminderService
from ppai.push.application.daily_summary_builder import DailySummaryBuilder
from ppai.push.application.friction_detector import FrictionDetector
from ppai.push.application.gap_detector import GapDetector
from ppai.push.application.midday_checkin import MiddayCheckin
from ppai.push.application.nudge_scheduler import NudgeScheduler
from ppai.push.application.nudge_service import NudgeService
from ppai.push.application.rescue_evaluator import RescueEvaluator
from ppai.push.application.weekly_reporter import WeeklyReporter
from ppai.push.application.zen_session_manager import ZenSessionManager
from ppai.push.infrastructure.cycle_event_repo import DynamoDBCycleEventRepository
from ppai.push.infrastructure.dynamodb_preferences_repo import DynamoDBPreferencesRepository
from ppai.push.infrastructure.config_telegram_adapter import ConfigTelegramAdapter
from ppai.push.infrastructure.er3_callback_adapter import ER3CallbackAdapter
from ppai.push.infrastructure.telegram_push_adapter import TelegramPushAdapter
from ppai.push.infrastructure.zen_telegram_adapter import ZenTelegramAdapter
from ppai.respond.application.response_service import ResponseService
from ppai.respond.infrastructure.dynamodb_interaction_event_repo import DynamoDBInteractionEventRepository
from ppai.respond.infrastructure.response_telegram_adapter import ResponseTelegramAdapter
from ppai.shared.infrastructure.config import get_settings
from ppai.shared.infrastructure.dynamodb_client import get_dynamodb_resource, table_name
from ppai.shared.infrastructure.logging import setup_logging
from ppai.shared.infrastructure.rate_limiter import InMemoryRateLimiter
from ppai.shared.infrastructure.user_registry import UserRegistry
# ER4: LLM intelligence layer
from ppai.intelligence.application.friction_analyzer import FrictionAnalyzerLLM
from ppai.intelligence.application.message_composer import MessageComposer
from ppai.intelligence.application.task_analyzer import TaskAnalyzer
from ppai.intelligence.application.weekly_insight import WeeklyInsightGenerator
from ppai.intelligence.infrastructure.anthropic_adapter import AnthropicAdapter
from ppai.intelligence.infrastructure.llm_rate_limiter import LLMRateLimiter

logger = logging.getLogger(__name__)


def build_app() -> Application:
    settings = get_settings()

    dynamodb = get_dynamodb_resource(settings.aws_region, settings.dynamodb_endpoint_url)
    task_table        = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "tasks"))
    event_table       = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "events"))
    dedup_table       = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "dedup"))
    cycle_table       = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "cycles"))
    preferences_table = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "preferences"))
    profile_table     = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "user-profiles"))

    # ER2: Calendar tables
    calendar_auth_table = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "calendar-auth"))
    time_blocks_table   = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "time-blocks"))

    task_repo    = DynamoDBTaskStateRepository(task_table)
    event_repo   = DynamoDBEventRepository(event_table)
    dedup_repo   = DynamoDBDedupRepository(dedup_table, settings)
    cycle_repo   = DynamoDBCycleRepository(cycle_table)
    prefs_repo   = DynamoDBPreferencesRepository(preferences_table)
    cycle_event_repo = DynamoDBCycleEventRepository(cycle_table)
    profile_repo = DynamoDBProfileRepository(profile_table)

    # ER2: Calendar repos
    calendar_auth_repo = DynamoDBCalendarAuthRepository(calendar_auth_table)
    block_repo         = DynamoDBTimeBlockRepository(time_blocks_table)

    # ER1: Profile & Onboarding
    profile_service = ProfileService(profile_repo=profile_repo)
    onboarding_service = OnboardingService()
    onboarding_adapter = OnboardingTelegramAdapter(onboarding_service, profile_service)
    profile_adapter = ProfileTelegramAdapter(profile_service)

    # ER2: Category classifier (used by capture + plan)
    category_classifier = CategoryClassifier()

    # ER4: LLM intelligence layer (optional — only if API key configured)
    llm_rate_limiter = LLMRateLimiter(daily_cap=settings.llm_daily_cap)
    task_analyzer = None
    message_composer = None
    friction_analyzer_llm = None
    weekly_insight_generator = None

    if settings.anthropic_api_key:
        anthropic_adapter = AnthropicAdapter(
            api_key=settings.anthropic_api_key,
            timeout=5.0,
        )
        task_analyzer = TaskAnalyzer(adapter=anthropic_adapter, rate_limiter=llm_rate_limiter)
        message_composer = MessageComposer(adapter=anthropic_adapter, rate_limiter=llm_rate_limiter)
        friction_analyzer_llm = FrictionAnalyzerLLM(adapter=anthropic_adapter, rate_limiter=llm_rate_limiter)
        weekly_insight_generator = WeeklyInsightGenerator(adapter=anthropic_adapter, rate_limiter=llm_rate_limiter)
        logger.info("ER4: LLM intelligence layer enabled (daily cap: %d)", settings.llm_daily_cap)
    else:
        logger.info("ER4: LLM intelligence layer disabled (no ANTHROPIC_API_KEY)")

    # UOW-01: Capture (with ER2 category classification + ER4 LLM analyzer)
    capture_service = CaptureService(
        task_repo=task_repo,
        event_repo=event_repo,
        dedup_repo=dedup_repo,
        active_task_limit=settings.active_task_limit,
        category_classifier=category_classifier,
        task_analyzer=task_analyzer,
        profile_repo=profile_repo,
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
    config_adapter   = ConfigTelegramAdapter(prefs_repo, profile_adapter)

    # UOW-04: Respond & State Transition
    interaction_event_repo = DynamoDBInteractionEventRepository(event_repo)
    response_service = ResponseService(
        task_repo=task_repo,
        event_repo=interaction_event_repo,
        cycle_event_repo=cycle_event_repo,
        cycle_repo=cycle_repo,
        decision_service=decision_service,
    )
    response_adapter = ResponseTelegramAdapter(response_service, user_registry)

    # ER2: Google Calendar & Block Planning (moved up for ER3 dependencies)
    oauth_service = GoogleOAuthService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )
    google_calendar_provider = GoogleCalendarAdapter()
    calendar_service = CalendarService(
        auth_repo=calendar_auth_repo,
        calendar_provider=google_calendar_provider,
        oauth_service=oauth_service,
        fernet_key=settings.fernet_encryption_key,
    )
    block_planner = BlockPlanner()
    calendar_sync = CalendarSync(calendar_service=calendar_service)
    calendar_adapter = CalendarTelegramAdapter(
        calendar_service=calendar_service,
        oauth_service=oauth_service,
        block_planner=block_planner,
        block_repo=block_repo,
        task_repo=task_repo,
        category_classifier=category_classifier,
        calendar_sync=calendar_sync,
    )

    # UOW-05: Zen, DailySummary, Rescue
    zen_manager = ZenSessionManager()
    daily_summary_builder = DailySummaryBuilder(task_repo)
    rescue_evaluator = RescueEvaluator()

    # Reconstruct zen sessions from persisted preferences
    all_prefs = prefs_repo.get_all()
    zen_manager.reconstruct_from_prefs(all_prefs)

    # UOW-03: Push & Scheduling (extended by UOW-05 and ER3)
    telegram_push = TelegramPushAdapter(bot_token=settings.telegram_bot_token)

    # ER3: Proactive intelligent notifications
    block_reminder_service = BlockReminderService(
        block_repo=block_repo,
        telegram_port=telegram_push,
        cycle_event_repo=cycle_event_repo,
        profile_repo=profile_repo,
    )
    gap_detector = GapDetector(
        calendar_service=calendar_service,
        profile_service=profile_service,
        telegram_port=telegram_push,
        cycle_event_repo=cycle_event_repo,
    )
    friction_detector = FrictionDetector(
        task_repo=task_repo,
        block_repo=block_repo,
        profile_repo=profile_repo,
        cycle_event_repo=cycle_event_repo,
        telegram_port=telegram_push,
        friction_analyzer_llm=friction_analyzer_llm,
    )
    weekly_reporter = WeeklyReporter(
        task_repo=task_repo,
        block_repo=block_repo,
        calendar_service=calendar_service,
        profile_repo=profile_repo,
        cycle_event_repo=cycle_event_repo,
        telegram_port=telegram_push,
        weekly_insight_generator=weekly_insight_generator,
    )
    midday_checkin = MiddayCheckin(
        block_repo=block_repo,
        profile_service=profile_service,
        telegram_port=telegram_push,
        cycle_event_repo=cycle_event_repo,
    )

    nudge_service = NudgeService(
        prefs_repo=prefs_repo,
        cycle_event_repo=cycle_event_repo,
        task_repo=task_repo,
        telegram_port=telegram_push,
        decision_service=decision_service,
        zen_manager=zen_manager,
        daily_summary_builder=daily_summary_builder,
        rescue_evaluator=rescue_evaluator,
        profile_repo=profile_repo,
        block_reminder_service=block_reminder_service,
        gap_detector=gap_detector,
        friction_detector=friction_detector,
        weekly_reporter=weekly_reporter,
        midday_checkin=midday_checkin,
        message_composer=message_composer,
    )
    nudge_scheduler = NudgeScheduler(
        nudge_service=nudge_service,
        user_ids_provider=user_registry.get_all,
        interval_provider=zen_manager.get_min_interval,
        block_repo=block_repo,
    )

    # UOW-05: /zen command
    zen_adapter = ZenTelegramAdapter(prefs_repo, cycle_event_repo, zen_manager)

    # ER3: Callback adapter for proactive notification responses
    er3_adapter = ER3CallbackAdapter(
        block_repo=block_repo,
        task_repo=task_repo,
        friction_detector=friction_detector,
        decision_service=decision_service,
        user_registry=user_registry,
    )

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # ER1: Onboarding ConversationHandler (highest priority — before capture)
    application.add_handler(onboarding_adapter.build_conversation_handler())

    # ER1: /perfil command
    application.add_handler(CommandHandler("perfil", profile_adapter.perfil_handler))

    # ER1: /libre command (days off)
    application.add_handler(CommandHandler("libre", profile_adapter.libre_handler))

    # ER2: /calendar OAuth ConversationHandler
    application.add_handler(calendar_adapter.build_calendar_conversation_handler())

    # UOW-01: free-text capture
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, capture_adapter.message_handler)
    )

    # UOW-02: /top3 command
    application.add_handler(CommandHandler("top3", decision_adapter.top3_handler))

    # UOW-04: Respond callbacks (done, confirm_done, cancel_done, snooze, clarify)
    application.add_handler(
        CallbackQueryHandler(
            response_adapter.callback_handler,
            pattern=r"^(done|confirm_done|cancel_done|snooze|clarify):.+$",
        )
    )

    # ER2: block_done / block_skip callbacks
    application.add_handler(
        CallbackQueryHandler(
            calendar_adapter.block_callback_handler,
            pattern=r"^block_(done|skip):.+$",
        )
    )

    # ER3: Block reminder callbacks (start, delay, skip_reminder, complete, more_time, no_progress)
    application.add_handler(
        CallbackQueryHandler(
            er3_adapter.callback_handler,
            pattern=r"^block_(start|delay|skip_reminder|complete|more_time|no_progress):.+$",
        )
    )

    # ER3: Friction detector callbacks
    application.add_handler(
        CallbackQueryHandler(
            er3_adapter.callback_handler,
            pattern=r"^friction_(divide|info|delete|pomodoro):.+$",
        )
    )

    # ER3: Gap detector callbacks
    application.add_handler(
        CallbackQueryHandler(
            er3_adapter.callback_handler,
            pattern=r"^gap_(reassign|continue|rest):.+$",
        )
    )

    # ER3: Midday check-in callbacks
    application.add_handler(
        CallbackQueryHandler(
            er3_adapter.callback_handler,
            pattern=r"^midday_(afternoon|unplanned|help|now):.+$",
        )
    )

    # UOW-03: /config command for nudge preferences
    application.add_handler(CommandHandler("config", config_adapter.config_handler))

    # UOW-05: /zen command for zen mode
    application.add_handler(CommandHandler("zen", zen_adapter.zen_handler))

    # ER2: /plan command
    application.add_handler(CommandHandler("plan", calendar_adapter.plan_handler))

    # UOW-04: Free-text clarify response (lower priority than commands and capture)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            response_adapter.clarify_response_handler,
        ),
        group=1,
    )

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
