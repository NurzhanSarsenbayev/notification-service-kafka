from __future__ import annotations

import logging
import sys


def configure_logging() -> None:
    """Base logging configuration for the campaign scheduler."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("asyncpg").setLevel(logging.INFO)
