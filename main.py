"""
Amazon Product Search Scraper — Main Entry Point.

This is the CLI entry point that orchestrates the entire scraping
pipeline: argument parsing → driver setup → search & scrape →
filtering → exporting → cleanup.

Usage:
    # Basic usage
    python main.py --keyword "laptop stand" --pages 3

    # With filters
    python main.py --keyword "headphones" --pages 2 --prime-only --min-rating 4.0

    # Watch the browser (non-headless)
    python main.py --keyword "mouse" --pages 1 --no-headless

    # Resume from last interrupted scrape
    python main.py --keyword "laptop stand" --pages 5 --resume

    # Exclude sponsored products
    python main.py --keyword "keyboard" --pages 2 --organic-only
"""

import argparse
import time
import sys
from pathlib import Path

from config.settings import (
    OUTPUT_DIR,
    CSV_FILE_NAME,
    JSON_FILE_NAME,
    SQLITE_DB_NAME,
    ensure_directories,
)
from scraper.driver import create_driver, close_driver
from scraper.search import search_amazon
from filters.product_filter import filter_products
from exporters.csv_exporter import export_to_csv
from exporters.json_exporter import export_to_json
from exporters.sqlite_exporter import export_to_sqlite
from utils.logger import setup_logger
from utils.resume import load_progress, clear_progress

logger = setup_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command-line arguments.

    Returns:
        An argparse.Namespace object with all parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Amazon Product Search Scraper — Scrape product data "
                    "from Amazon search results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --keyword "laptop stand" --pages 3
  python main.py --keyword "headphones" --pages 2 --prime-only
  python main.py --keyword "mouse" --pages 1 --no-headless
  python main.py --keyword "keyboard" --pages 5 --resume --organic-only
        """,
    )

    # ── Required Arguments ────────────────────────────────────
    parser.add_argument(
        "--keyword",
        type=str,
        required=True,
        help="The search keyword to scrape (e.g., 'laptop stand').",
    )

    parser.add_argument(
        "--pages",
        type=int,
        required=True,
        help="Number of search result pages to scrape (e.g., 3).",
    )

    # ── Browser Options ───────────────────────────────────────
    parser.add_argument(
        "--no-headless",
        action="store_true",
        default=False,
        help="Run the browser with a visible window (default: headless).",
    )

    # ── Resume Option (Bonus) ─────────────────────────────────
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume scraping from the last successfully scraped page.",
    )

    # ── Filter Options (Bonus) ────────────────────────────────
    parser.add_argument(
        "--prime-only",
        action="store_true",
        default=False,
        help="Keep only Amazon Prime eligible products.",
    )

    parser.add_argument(
        "--organic-only",
        action="store_true",
        default=False,
        help="Exclude sponsored/ad products from results.",
    )

    parser.add_argument(
        "--min-rating",
        type=float,
        default=None,
        help="Minimum star rating to include (e.g., 4.0).",
    )

    # ── Location Option (Bonus) ───────────────────────────────
    parser.add_argument(
        "--zipcode",
        type=str,
        default=None,
        help="US Zip code to set delivery location before searching.",
    )

    args = parser.parse_args()

    # ── Validation ────────────────────────────────────────────
    if args.pages < 1:
        parser.error("--pages must be at least 1.")

    if args.min_rating is not None and (
        args.min_rating < 0 or args.min_rating > 5
    ):
        parser.error("--min-rating must be between 0 and 5.")

    return args


def main() -> None:
    """Main orchestration function for the Amazon scraper.

    Executes the full pipeline:
      1. Parse CLI arguments
      2. Ensure output directories exist
      3. Create the WebDriver
      4. Check for resume state (if --resume flag is set)
      5. Scrape search results
      6. Apply filters (if any)
      7. Export to CSV, JSON, and SQLite
      8. Clean up the WebDriver
      9. Log a summary
    """
    # ── Step 1: Parse arguments ───────────────────────────────
    args = parse_arguments()

    # ── Step 2: Setup directories and logging ─────────────────
    ensure_directories()

    logger.info("=" * 60)
    logger.info("Amazon Product Search Scraper — Starting")
    logger.info("=" * 60)
    logger.info("Keyword:    %s", args.keyword)
    logger.info("Pages:      %d", args.pages)
    logger.info("Headless:   %s", not args.no_headless)
    logger.info("Resume:     %s", args.resume)
    if args.prime_only:
        logger.info("Filter:     Prime Only")
    if args.organic_only:
        logger.info("Filter:     Organic Only")
    if args.min_rating is not None:
        logger.info("Filter:     Min Rating >= %.1f", args.min_rating)
    if args.zipcode:
        logger.info("Location:   Zip Code %s", args.zipcode)
    logger.info("-" * 60)

    # Record the start time for the summary
    start_time: float = time.time()

    # ── Step 3: Create WebDriver ──────────────────────────────
    headless: bool = not args.no_headless
    driver = None

    try:
        driver = create_driver(headless=headless)

        # ── Step 4: Check resume state ────────────────────────
        start_page: int = 1
        if args.resume:
            start_page = load_progress(args.keyword)

        # ── Step 5: Scrape search results ─────────────────────
        products = search_amazon(
            driver=driver,
            keyword=args.keyword,
            num_pages=args.pages,
            start_page=start_page,
            zipcode=args.zipcode,
        )

        if not products:
            logger.warning("No products were scraped. Exiting.")
            return

        logger.info(
            "Scraping finished: %d products extracted.",
            len(products),
        )

        # ── Step 6: Apply filters ─────────────────────────────
        filtered_products = filter_products(
            products=products,
            prime_only=args.prime_only,
            min_rating=args.min_rating,
            organic_only=args.organic_only,
        )

        if not filtered_products:
            logger.warning(
                "No products remaining after filtering. "
                "Try adjusting your filter criteria."
            )
            return

        # ── Step 7: Export results ────────────────────────────
        csv_path: str = str(OUTPUT_DIR / CSV_FILE_NAME)
        json_path: str = str(OUTPUT_DIR / JSON_FILE_NAME)
        sqlite_path: str = str(OUTPUT_DIR / SQLITE_DB_NAME)

        export_to_csv(filtered_products, csv_path, resume=args.resume)
        export_to_json(filtered_products, json_path, resume=args.resume)
        export_to_sqlite(filtered_products, sqlite_path)

        # Clear resume state after a complete successful scrape
        clear_progress()

        # ── Step 9: Log summary ───────────────────────────────
        elapsed: float = time.time() - start_time
        logger.info("-" * 60)
        logger.info("SCRAPE SUMMARY")
        logger.info("-" * 60)
        logger.info("Keyword:          %s", args.keyword)
        logger.info("Pages scraped:    %d", args.pages)
        logger.info("Products found:   %d", len(products))
        logger.info("After filtering:  %d", len(filtered_products))
        logger.info("Time elapsed:     %.1f seconds", elapsed)
        logger.info("CSV output:       %s", csv_path)
        logger.info("JSON output:      %s", json_path)
        logger.info("SQLite output:    %s", sqlite_path)
        logger.info("=" * 60)
        logger.info("Scraping completed successfully!")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user (Ctrl+C).")
        logger.info(
            "Progress has been saved. Use --resume to continue later."
        )

    except Exception as error:
        logger.error("Fatal error: %s", str(error))
        logger.info(
            "Progress has been saved. Use --resume to continue later."
        )
        raise

    finally:
        # ── Step 8: Cleanup ───────────────────────────────────
        if driver:
            close_driver(driver)


if __name__ == "__main__":
    main()
