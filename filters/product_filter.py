"""
Product filters for the Amazon Product Search Scraper.

Provides post-scraping filters to narrow down results based on
user preferences like Prime eligibility, minimum rating, and
sponsored/organic status.

Usage:
    from filters.product_filter import filter_products

    filtered = filter_products(
        products,
        prime_only=True,
        min_rating=4.0,
        organic_only=True,
    )
"""

from models.product import Product
from utils.logger import setup_logger

logger = setup_logger(__name__)


def filter_products(
    products: list[Product],
    prime_only: bool = False,
    min_rating: float | None = None,
    organic_only: bool = False,
) -> list[Product]:
    """Apply filters to a list of scraped products.

    All filters are optional — if no filters are enabled, the
    original list is returned unchanged.

    Args:
        products: The full list of scraped Product objects.
        prime_only: If True, keep only Prime-eligible products.
        min_rating: If set, keep only products with a rating
                    at or above this value (e.g., 4.0).
        organic_only: If True, exclude sponsored/ad products.

    Returns:
        A filtered list of Product objects matching all criteria.
    """
    original_count: int = len(products)
    filtered: list[Product] = products

    # ── Prime-Only Filter ─────────────────────────────────────
    if prime_only:
        filtered = [p for p in filtered if p.is_prime]
        logger.info(
            "Prime filter: %d → %d products",
            original_count,
            len(filtered),
        )

    # ── Organic-Only Filter (exclude sponsored) ───────────────
    if organic_only:
        before: int = len(filtered)
        filtered = [p for p in filtered if not p.is_sponsored]
        logger.info(
            "Organic filter: %d → %d products",
            before,
            len(filtered),
        )

    # ── Minimum Rating Filter ─────────────────────────────────
    if min_rating is not None:
        before = len(filtered)
        filtered = [
            p for p in filtered
            if _get_numeric_rating(p.rating) >= min_rating
        ]
        logger.info(
            "Rating filter (>= %.1f): %d → %d products",
            min_rating,
            before,
            len(filtered),
        )

    # ── Summary ───────────────────────────────────────────────
    if original_count != len(filtered):
        logger.info(
            "Filtering complete: %d → %d products remaining",
            original_count,
            len(filtered),
        )
    else:
        logger.info("No filters applied. All %d products kept.", len(filtered))

    return filtered


def _get_numeric_rating(rating: str | None) -> float:
    """Extract a numeric rating value from the rating string.

    Handles formats like:
      - "4.7 out of 5 stars"
      - "4.5"
      - None or empty string

    Args:
        rating: The raw rating string from the Product object.

    Returns:
        The numeric rating as a float, or 0.0 if parsing fails.
    """
    if not rating:
        return 0.0

    try:
        # Take the first word/number from the string
        # "4.7 out of 5 stars" → "4.7"
        first_part: str = rating.strip().split()[0]
        return float(first_part)
    except (ValueError, IndexError):
        return 0.0
