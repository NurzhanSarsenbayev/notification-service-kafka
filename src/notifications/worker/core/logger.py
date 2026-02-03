import logging


def configure_logging() -> None:
    """Global logging configuration for the worker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
