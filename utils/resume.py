"""
Resume utility for the Amazon Product Search Scraper.

Saves and loads scraping progress so the scraper can resume
from the last successfully scraped page after an interruption
(crash, network loss, manual stop, etc.).

Progress is stored as a JSON file in the logs directory.

Usage:
    from utils.resume import save_progress, load_progress

    # After successfully scraping page 3:
    save_progress("wireless headphones", page=3)

    # On next run with --resume flag:
    start_page = load_progress("wireless headphones")  # Returns 4
"""

import json
from pathlib import Path

from config.settings import RESUME_FILE
from utils.logger import setup_logger

logger = setup_logger(__name__)


def save_progress(keyword: str, page: int) -> None:
    """Save the last successfully scraped page number.

    Writes a JSON file containing the keyword and the page number
    that was just completed. On resume, scraping will start from
    page + 1.

    Args:
        keyword: The search keyword being scraped.
        page: The page number that was just successfully scraped.
    """
    progress_data: dict = {
        "keyword": keyword,
        "last_completed_page": page,
    }

    try:
        # Ensure the parent directory exists
        RESUME_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(RESUME_FILE, "w", encoding="utf-8") as file:
            json.dump(progress_data, file, indent=2)

        logger.debug(
            "Progress saved: keyword='%s', last_completed_page=%d",
            keyword,
            page,
        )
    except OSError as error:
        logger.error("Failed to save progress: %s", str(error))


def load_progress(keyword: str) -> int:
    """Load the last completed page and return the next page to scrape.

    If no progress file exists, or the saved keyword doesn't match
    the current keyword, scraping starts from page 1.

    Args:
        keyword: The search keyword to check progress for.

    Returns:
        The page number to start scraping from.
        Returns 1 if no matching progress is found.
    """
    if not RESUME_FILE.exists():
        logger.info("No resume file found. Starting from page 1.")
        return 1

    try:
        with open(RESUME_FILE, "r", encoding="utf-8") as file:
            progress_data: dict = json.load(file)

        saved_keyword: str = progress_data.get("keyword", "")
        last_page: int = progress_data.get("last_completed_page", 0)

        # Only resume if the keyword matches
        if saved_keyword.lower() == keyword.lower() and last_page > 0:
            next_page: int = last_page + 1
            logger.info(
                "Resuming from page %d (last completed: %d) "
                "for keyword '%s'.",
                next_page,
                last_page,
                keyword,
            )
            return next_page
        else:
            logger.info(
                "Saved keyword '%s' doesn't match current keyword '%s'. "
                "Starting from page 1.",
                saved_keyword,
                keyword,
            )
            return 1

    except (json.JSONDecodeError, OSError) as error:
        logger.warning(
            "Failed to read resume file: %s. Starting from page 1.",
            str(error),
        )
        return 1


def clear_progress() -> None:
    """Delete the progress file after a successful full scrape.

    Called when all requested pages have been scraped successfully,
    so the next run starts fresh.
    """
    try:
        if RESUME_FILE.exists():
            RESUME_FILE.unlink()
            logger.debug("Progress file cleared.")
    except OSError as error:
        logger.warning("Failed to clear progress file: %s", str(error))
