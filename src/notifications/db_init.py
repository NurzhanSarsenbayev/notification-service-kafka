import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import OperationalError

from notifications.common.config import settings
from notifications.db.models import Base

logger = logging.getLogger(__name__)


async def main() -> None:
    engine = create_async_engine(settings.db_dsn, echo=True, future=True)

    max_attempts = 10
    delay = 2

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                "DB init: trying to create schema (attempt %s/%s) dsn=%s",
                attempt,
                max_attempts,
                settings.db_dsn,
            )
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("DB schema created successfully")
            break
        except OperationalError as e:
            logger.warning(
                "DB init: DB not ready yet (attempt %s/%s): %s",
                attempt,
                max_attempts,
                e,
            )
            if attempt == max_attempts:
                logger.error("DB init: giving up after %s attempts", max_attempts)
                raise
            await asyncio.sleep(delay)

    await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    asyncio.run(main())
