from __future__ import annotations

import asyncio
import logging

from notifications.campaign_scheduler.core.logger import configure_logging
from notifications.campaign_scheduler.service.scheduler_service import run_scheduler

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    logger.info("Campaign scheduler main() starting")
    asyncio.run(run_scheduler())
    logger.info("Campaign scheduler main() exited")


if __name__ == "__main__":
    main()
