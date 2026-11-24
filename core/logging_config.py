import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging():
    """
    Configure application logging.

    Use rotating file logging when available.
    Fall back to console logging if file logging cannot
    be initialized, so logging problems do not prevent
    the application from starting.
    """

    project_root = Path(__file__).resolve().parents[1]

    log_directory = project_root / "logs"
    log_file = log_directory / "clinic_faq.log"

    logger = logging.getLogger("clinic_faq")

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid installing duplicate handlers.
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    try:

        log_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8"
        )

        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    except OSError:

        # File logging is unavailable.
        # Use console logging instead.
        console_handler = logging.StreamHandler()

        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

        logger.warning(
            "File logging is unavailable. "
            "Using console logging instead."
        )

    return logger
