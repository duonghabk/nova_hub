import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging():
    """
    Configure application-wide logging.
    - Creates 'logs/app_hub.log' if not exists.
    - Uses RotatingFileHandler to avoid huge log file.
    """
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "app_hub.log"

    logger = logging.getLogger("app_hub")
    logger.setLevel(logging.DEBUG)

    # Avoid adding multiple handlers if this module is reloaded.
    if logger.handlers:
        return logger

    # Rotating file handler: 1 MB per file, keep last 3 backups.
    handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Optional: also log to console during development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()