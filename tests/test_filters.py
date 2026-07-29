"""
Unit tests for the product filters module.

Tests the filtering logic for prime_only, organic_only, and
min_rating constraints.

Run with:
    pytest tests/test_filters.py -v
"""

import pytest

from models.product import Product
from filters.product_filter import filter_products, _get_numeric_rating


# ══════════════════════════════════════════════════════════════
# Fixtures — Test Data
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def sample_products() -> list[Product]:
    """Provide a diverse list of products for testing filters."""
    return [
        Product(
            title="Product A - Prime, Organic, 4.5 Stars",
            is_prime=True,
            is_sponsored=False,
            rating="4.5 out of 5 stars",
        ),
        Product(
            title="Product B - Non-Prime, Sponsored, 3.8 Stars",
            is_prime=False,
            is_sponsored=True,
            rating="3.8 out of 5 stars",
        ),
        Product(
            title="Product C - Prime, Sponsored, 5.0 Stars",
            is_prime=True,
            is_sponsored=True,
            rating="5.0 out of 5 stars",
        ),
        Product(
            title="Product D - Non-Prime, Organic, No Rating",
            is_prime=False,
            is_sponsored=False,
            rating=None,
        ),
        Product(
            title="Product E - Prime, Organic, 4.0 Stars",
            is_prime=True,
            is_sponsored=False,
            rating="4.0",
        ),
    ]


# ══════════════════════════════════════════════════════════════
# Tests for _get_numeric_rating()
# ══════════════════════════════════════════════════════════════

class TestGetNumericRating:
    """Tests for the internal rating parsing helper."""

    def test_parses_standard_amazon_format(self) -> None:
        """Should extract number from 'X.X out of 5 stars'."""
        assert _get_numeric_rating("4.7 out of 5 stars") == 4.7
        assert _get_numeric_rating("3.0 out of 5 stars") == 3.0

    def test_parses_bare_number(self) -> None:
        """Should handle just the number string."""
        assert _get_numeric_rating("4.2") == 4.2
        assert _get_numeric_rating("5") == 5.0

    def test_handles_none_and_empty(self) -> None:
        """Should return 0.0 for None or empty strings."""
        assert _get_numeric_rating(None) == 0.0
        assert _get_numeric_rating("") == 0.0
        assert _get_numeric_rating("   ") == 0.0

    def test_handles_invalid_formats(self) -> None:
        """Should return 0.0 if parsing fails entirely."""
        assert _get_numeric_rating("Not rated yet") == 0.0


# ══════════════════════════════════════════════════════════════
# Tests for filter_products()
# ══════════════════════════════════════════════════════════════

class TestFilterProducts:
    """Tests for the main filtering function."""

    def test_no_filters_returns_all(
        self, sample_products: list[Product]
    ) -> None:
        """Should return the original list if no flags are set."""
        filtered = filter_products(sample_products)
        assert len(filtered) == 5
        assert filtered == sample_products

    def test_prime_only_filter(
        self, sample_products: list[Product]
    ) -> None:
        """Should keep only products with is_prime=True."""
        filtered = filter_products(sample_products, prime_only=True)

        assert len(filtered) == 3
        assert all(p.is_prime for p in filtered)
        # Verify specific products were kept
        titles = [p.title for p in filtered]
        assert "Product A - Prime, Organic, 4.5 Stars" in titles
        assert "Product C - Prime, Sponsored, 5.0 Stars" in titles
        assert "Product E - Prime, Organic, 4.0 Stars" in titles

    def test_organic_only_filter(
        self, sample_products: list[Product]
    ) -> None:
        """Should exclude products with is_sponsored=True."""
        filtered = filter_products(sample_products, organic_only=True)

        assert len(filtered) == 3
        assert all(not p.is_sponsored for p in filtered)
        titles = [p.title for p in filtered]
        assert "Product A - Prime, Organic, 4.5 Stars" in titles
        assert "Product D - Non-Prime, Organic, No Rating" in titles
        assert "Product E - Prime, Organic, 4.0 Stars" in titles

    def test_min_rating_filter(
        self, sample_products: list[Product]
    ) -> None:
        """Should keep products with rating >= min_rating."""
        filtered = filter_products(sample_products, min_rating=4.5)

        assert len(filtered) == 2
        titles = [p.title for p in filtered]
        assert "Product A - Prime, Organic, 4.5 Stars" in titles
        assert "Product C - Prime, Sponsored, 5.0 Stars" in titles
        # Product D (no rating = 0.0) should be excluded

    def test_combined_filters(
        self, sample_products: list[Product]
    ) -> None:
        """Should apply all filters together with AND logic."""
        # Want: Prime AND Organic AND Rating >= 4.0
        filtered = filter_products(
            sample_products,
            prime_only=True,
            organic_only=True,
            min_rating=4.0,
        )

        assert len(filtered) == 2
        titles = [p.title for p in filtered]
        assert "Product A - Prime, Organic, 4.5 Stars" in titles
        assert "Product E - Prime, Organic, 4.0 Stars" in titles
        # Product C is Prime and 5.0 stars, but Sponsored -> Excluded

    def test_empty_list(self) -> None:
        """Should handle an empty product list safely."""
        filtered = filter_products([], prime_only=True)
        assert filtered == []
