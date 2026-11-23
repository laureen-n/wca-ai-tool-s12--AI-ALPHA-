
import logging

from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging():
    """
    Configure application-wide logging.

    Logs are stored in logs/clinic_faq.log.
    The log file rotates at approximately 1 MB.
    """

    project_root = Path(__file__).resolve().parents[1]

    log_directory = project_root / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)

    log_file = log_directory / "clinic_faq.log"

    logger = logging.getLogger("clinic_faq")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Prevent duplicate handlers
    if not logger.handlers:

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8"
        )

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger
