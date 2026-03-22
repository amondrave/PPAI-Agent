"""Local development entry point — polling mode.

Uses python-telegram-bot's run_polling() instead of run_webhook().
Polling doesn't require a public URL, making it ideal for local dev with LocalStack.

Usage:
    1. Start LocalStack:        docker-compose up -d
    2. Copy env file:           cp .env.example .env  (fill in your token)
    3. Uncomment in .env:       DYNAMODB_ENDPOINT_URL=http://localhost:4566
    4. Activate venv:           source .venv/bin/activate
    5. Run:                     python -m ppai.local
"""
from __future__ import annotations

import logging

from ppai.main import build_app
from ppai.shared.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    logger.info("Starting PPAI bot in LOCAL POLLING mode...")
    logger.info("Make sure LocalStack is running: docker-compose up -d")

    app = build_app()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
