"""
Centralized logging configuration for the Amazon Product Search Scraper.

Sets up a dual-handler logging system:
  - File handler:    Captures DEBUG-level and above to logs/scraper.log
  - Console handler: Displays INFO-level and above to stdout

Usage:
    from utils.logger import setup_logger
    logger = setup_logger(__name__)
    logger.info("Scraping started")
"""

import logging
from pathlib import Path
from config.settings import (
    LOG_DIR,
    LOG_FILE_NAME,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    FILE_LOG_LEVEL,
    CONSOLE_LOG_LEVEL,
)


def setup_logger(name: str) -> logging.Logger:
    """Create and configure a logger with file and console handlers.

    Each module should call this once with __name__ to get its own
    named logger. All loggers share the same file and console handlers
    to ensure consistent output.

    Args:
        name: The name for the logger, typically __name__ of the
              calling module.

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if setup_logger is called
    # multiple times for the same module name
    if logger.handlers:
        return logger

    # Set the logger to the lowest level; handlers will filter further
    logger.setLevel(logging.DEBUG)

    # Create the formatter used by both handlers
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )

    # ── File Handler ──────────────────────────────────────────
    # Ensure the log directory exists before creating the file handler
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file_path: Path = LOG_DIR / LOG_FILE_NAME

    file_handler = logging.FileHandler(
        filename=str(log_file_path),
        mode="a",           # Append mode — preserves logs across runs
        encoding="utf-8",
    )
    file_handler.setLevel(FILE_LOG_LEVEL)
    file_handler.setFormatter(formatter)

    # ── Console Handler ───────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(CONSOLE_LOG_LEVEL)
    console_handler.setFormatter(formatter)

    # Attach both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
