"""
Centralized configuration settings for the Amazon Product Search Scraper.

All configurable constants are defined here so they can be easily
adjusted without modifying the core scraper logic.
"""

import os
import logging
from pathlib import Path


# ──────────────────────────────────────────────
# Project Paths
# ──────────────────────────────────────────────

# Root directory of the project (parent of the config/ folder)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Directory where scraped output files (CSV, JSON, SQLite) are saved
OUTPUT_DIR: Path = PROJECT_ROOT / "output"

# Directory where log files are stored
LOG_DIR: Path = PROJECT_ROOT / "logs"

# Directory where error screenshots are saved (bonus feature)
SCREENSHOT_DIR: Path = PROJECT_ROOT / "screenshots"

# File used to save/resume scraping progress (bonus feature)
RESUME_FILE: Path = PROJECT_ROOT / "logs" / "resume_state.json"


# ──────────────────────────────────────────────
# Amazon URLs
# ──────────────────────────────────────────────

# Base Amazon URL — change this if targeting a different region
BASE_URL: str = "https://www.amazon.com"

# Search URL template — {keyword} and {page} are replaced at runtime
SEARCH_URL_TEMPLATE: str = BASE_URL + "/s?k={keyword}&page={page}"


# ──────────────────────────────────────────────
# WebDriver Settings
# ──────────────────────────────────────────────

# Whether to run the browser in headless mode (no visible window)
HEADLESS: bool = True

# Browser window size (used even in headless mode for consistent rendering)
WINDOW_WIDTH: int = 1920
WINDOW_HEIGHT: int = 1080

# User-Agent string to make the browser look like a real user
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


# ──────────────────────────────────────────────
# Timeouts & Waits
# ──────────────────────────────────────────────

# Maximum seconds to wait for elements to appear (explicit waits)
DEFAULT_TIMEOUT: int = 15

# Maximum seconds to wait for a page to fully load
PAGE_LOAD_TIMEOUT: int = 30

# Random delay range to simulate human behavior (anti-detection)
MIN_DELAY: float = 1.0
MAX_DELAY: float = 3.0


# ──────────────────────────────────────────────
# Retry Settings (Bonus Feature)
# ──────────────────────────────────────────────

# Maximum number of retry attempts for failed operations
MAX_RETRIES: int = 3

# Delay in seconds between retry attempts
RETRY_DELAY: float = 2.0


# ──────────────────────────────────────────────
# Logging Settings
# ──────────────────────────────────────────────

# Minimum log level for the file handler (captures everything)
FILE_LOG_LEVEL: int = logging.DEBUG

# Minimum log level for the console handler (user-friendly output)
CONSOLE_LOG_LEVEL: int = logging.INFO

# Log message format
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Log date format
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# Log file name
LOG_FILE_NAME: str = "scraper.log"


# ──────────────────────────────────────────────
# Output File Names
# ──────────────────────────────────────────────

CSV_FILE_NAME: str = "results.csv"
JSON_FILE_NAME: str = "results.json"
SQLITE_DB_NAME: str = "results.db"


# ──────────────────────────────────────────────
# Ensure directories exist at import time
# ──────────────────────────────────────────────

def ensure_directories() -> None:
    """Create output, log, and screenshot directories if they don't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
