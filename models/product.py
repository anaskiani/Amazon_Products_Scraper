"""
Product data model for the Amazon Product Search Scraper.

Defines the Product dataclass that represents a single product
extracted from Amazon search results. This is the central data
structure used across all modules (scraper, filters, exporters).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Product:
    """Represents a single product from Amazon search results.

    Attributes:
        title: The product's display name/title.
        current_price: The current selling price (e.g., "$29.99").
        original_price: The original price before discount, if available.
        discount_percentage: The discount percentage (e.g., "-20%"), if available.
        rating: The product's star rating (e.g., "4.5 out of 5 stars").
        num_reviews: The total number of customer reviews (e.g., "1,234").
        is_prime: Whether the product is eligible for Amazon Prime.
        is_sponsored: Whether the product listing is a sponsored/ad result.
        product_url: The full URL to the product detail page.
        asin: Amazon Standard Identification Number, if available.
        image_url: URL of the product's main image, if available.
    """

    title: str
    current_price: Optional[str] = None
    original_price: Optional[str] = None
    discount_percentage: Optional[str] = None
    rating: Optional[str] = None
    num_reviews: Optional[str] = None
    is_prime: bool = False
    is_sponsored: bool = False
    product_url: str = ""
    asin: Optional[str] = None
    image_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert the Product instance to a dictionary.

        Returns:
            A dictionary with all product fields as key-value pairs.
            This is used by the exporters (CSV, JSON, SQLite) for
            serialization.
        """
        return asdict(self)

    def __str__(self) -> str:
        """Return a human-readable summary of the product."""
        price_display = self.current_price or "N/A"
        rating_display = self.rating or "No rating"
        prime_badge = " [PRIME]" if self.is_prime else ""
        sponsored_badge = " [SPONSORED]" if self.is_sponsored else ""

        return (
            f"{self.title[:80]}... | "
            f"Price: {price_display} | "
            f"Rating: {rating_display} | "
            f"Reviews: {self.num_reviews or 'N/A'}"
            f"{prime_badge}{sponsored_badge}"
        )
