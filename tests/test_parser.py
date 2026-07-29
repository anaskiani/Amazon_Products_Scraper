"""
Unit tests for the product parser module.

Tests the parsing helper functions and parse_single_product()
using mocked WebElement objects — no browser or network needed.

Run with:
    pytest tests/test_parser.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import NoSuchElementException

from scraper.parser import (
    _get_text,
    _get_attribute,
    _get_element_attribute,
    _get_link,
    _get_image_src,
    _element_exists,
    _calculate_discount,
    _extract_numeric_price,
    parse_single_product,
)
from models.product import Product


# ══════════════════════════════════════════════════════════════
# Fixtures — Reusable mock objects
# ══════════════════════════════════════════════════════════════

def create_mock_card(
    asin: str = "B0BKSPYJ89",
    title: str = "JCZT Adjustable Laptop Stand",
    current_price: str = "PKR 6,665.62",
    original_price: str = "PKR 7,499.17",
    rating_text: str = "4.7 out of 5 stars",
    reviews_aria: str = "1,028 ratings",
    has_prime: bool = False,
    has_sponsored: bool = True,
    product_href: str = "/dp/B0BKSPYJ89",
    image_src: str = "https://m.media-amazon.com/images/I/71GkB3XWinL.jpg",
) -> MagicMock:
    """Create a mock WebElement card with configurable fields.

    Each find_element call is configured to return the expected
    sub-elements based on the XPath being searched.
    """
    card = MagicMock()

    # Mock data-asin attribute
    card.get_attribute.return_value = asin

    def mock_find_element(by, xpath):
        """Route find_element calls to the correct mock based on XPath."""
        element = MagicMock()

        if "title-recipe" in xpath and "h2" in xpath:
            if "a[" in xpath:
                # Product link
                element.get_attribute.return_value = product_href
            else:
                # Title text
                element.text = title
            return element

        if "price-recipe" in xpath:
            if "data-a-color='base'" in xpath:
                element.text = current_price
                return element
            if "data-a-strike" in xpath:
                if original_price:
                    element.text = original_price
                    return element
                raise NoSuchElementException("No original price")
            if "%" in xpath:
                raise NoSuchElementException("No discount badge")

        if "reviews-block" in xpath:
            if "reviews-ratings-slot" in xpath:
                element.text = rating_text
                return element
            if "ratings" in xpath:
                element.get_attribute.return_value = reviews_aria
                return element

        if "a-icon-prime" in xpath:
            if has_prime:
                return element
            raise NoSuchElementException("No prime badge")

        if "puis-label-popover-default" in xpath:
            if has_sponsored:
                return element
            raise NoSuchElementException("No sponsored label")

        if "s-product-image" in xpath:
            element.get_attribute.return_value = image_src
            return element

        raise NoSuchElementException(f"Element not found: {xpath}")

    card.find_element.side_effect = mock_find_element
    return card


# ══════════════════════════════════════════════════════════════
# Tests for _get_text()
# ══════════════════════════════════════════════════════════════

class TestGetText:
    """Tests for the _get_text helper function."""

    def test_returns_text_when_element_found(self) -> None:
        """Should return stripped text content."""
        card = MagicMock()
        element = MagicMock()
        element.text = "  Laptop Stand  "
        card.find_element.return_value = element

        result = _get_text(card, ".//span")
        assert result == "Laptop Stand"

    def test_returns_none_when_element_not_found(self) -> None:
        """Should return None when NoSuchElementException is raised."""
        card = MagicMock()
        card.find_element.side_effect = NoSuchElementException("Not found")

        result = _get_text(card, ".//span")
        assert result is None

    def test_returns_none_when_text_is_empty(self) -> None:
        """Should return None when element exists but text is empty."""
        card = MagicMock()
        element = MagicMock()
        element.text = "   "
        card.find_element.return_value = element

        result = _get_text(card, ".//span")
        assert result is None

    def test_returns_none_when_xpath_is_empty(self) -> None:
        """Should return None when xpath is empty string."""
        card = MagicMock()
        result = _get_text(card, "")
        assert result is None


# ══════════════════════════════════════════════════════════════
# Tests for _get_attribute()
# ══════════════════════════════════════════════════════════════

class TestGetAttribute:
    """Tests for the _get_attribute helper function."""

    def test_returns_attribute_value(self) -> None:
        """Should return the attribute value."""
        card = MagicMock()
        card.get_attribute.return_value = "B0BKSPYJ89"

        result = _get_attribute(card, "data-asin")
        assert result == "B0BKSPYJ89"

    def test_returns_none_when_attribute_empty(self) -> None:
        """Should return None when attribute is empty string."""
        card = MagicMock()
        card.get_attribute.return_value = ""

        result = _get_attribute(card, "data-asin")
        assert result is None

    def test_returns_none_when_attribute_is_none(self) -> None:
        """Should return None when attribute doesn't exist."""
        card = MagicMock()
        card.get_attribute.return_value = None

        result = _get_attribute(card, "data-asin")
        assert result is None


# ══════════════════════════════════════════════════════════════
# Tests for _element_exists()
# ══════════════════════════════════════════════════════════════

class TestElementExists:
    """Tests for the _element_exists helper function."""

    def test_returns_true_when_element_found(self) -> None:
        """Should return True when the element exists."""
        card = MagicMock()
        card.find_element.return_value = MagicMock()

        result = _element_exists(card, ".//i[@class='a-icon-prime']")
        assert result is True

    def test_returns_false_when_element_not_found(self) -> None:
        """Should return False when NoSuchElementException is raised."""
        card = MagicMock()
        card.find_element.side_effect = NoSuchElementException("Not found")

        result = _element_exists(card, ".//i[@class='a-icon-prime']")
        assert result is False

    def test_returns_false_when_xpath_is_empty(self) -> None:
        """Should return False when xpath is empty string."""
        card = MagicMock()
        result = _element_exists(card, "")
        assert result is False


# ══════════════════════════════════════════════════════════════
# Tests for _calculate_discount()
# ══════════════════════════════════════════════════════════════

class TestCalculateDiscount:
    """Tests for the _calculate_discount helper function."""

    def test_calculates_correct_percentage(self) -> None:
        """Should calculate discount from PKR prices."""
        result = _calculate_discount("PKR 6,665.62", "PKR 7,499.17")
        assert result == "-11%"

    def test_large_discount(self) -> None:
        """Should handle a 50% discount."""
        result = _calculate_discount("$50.00", "$100.00")
        assert result == "-50%"

    def test_returns_none_when_no_discount(self) -> None:
        """Should return None when current >= original."""
        result = _calculate_discount("$100.00", "$100.00")
        assert result is None

    def test_returns_none_for_invalid_prices(self) -> None:
        """Should return None when price strings can't be parsed."""
        result = _calculate_discount("N/A", "free")
        assert result is None


# ══════════════════════════════════════════════════════════════
# Tests for _extract_numeric_price()
# ══════════════════════════════════════════════════════════════

class TestExtractNumericPrice:
    """Tests for the _extract_numeric_price helper function."""

    def test_usd_price(self) -> None:
        """Should extract numeric value from USD price."""
        result = _extract_numeric_price("$29.99")
        assert result == 29.99

    def test_pkr_price_with_commas(self) -> None:
        """Should handle PKR prices with commas and spaces."""
        result = _extract_numeric_price("PKR 6,665.62")
        assert result == 6665.62

    def test_price_with_non_breaking_space(self) -> None:
        """Should handle non-breaking space (\\xa0) in prices."""
        result = _extract_numeric_price("PKR\xa06,665.62")
        assert result == 6665.62

    def test_raises_for_empty_string(self) -> None:
        """Should raise ValueError for strings with no numbers."""
        with pytest.raises(ValueError):
            _extract_numeric_price("free")


# ══════════════════════════════════════════════════════════════
# Tests for parse_single_product()
# ══════════════════════════════════════════════════════════════

class TestParseSingleProduct:
    """Tests for the parse_single_product function."""

    def test_parses_complete_product(self) -> None:
        """Should extract all fields from a complete product card."""
        card = create_mock_card()
        product = parse_single_product(card)

        assert product is not None
        assert product.title == "JCZT Adjustable Laptop Stand"
        assert product.current_price == "PKR 6,665.62"
        assert product.original_price == "PKR 7,499.17"
        assert product.rating == "4.7 out of 5 stars"
        assert product.num_reviews == "1,028 ratings"
        assert product.is_prime is False
        assert product.is_sponsored is True
        assert product.asin == "B0BKSPYJ89"

    def test_parses_prime_product(self) -> None:
        """Should correctly detect Prime eligibility."""
        card = create_mock_card(has_prime=True)
        product = parse_single_product(card)

        assert product is not None
        assert product.is_prime is True

    def test_parses_organic_product(self) -> None:
        """Should correctly detect non-sponsored products."""
        card = create_mock_card(has_sponsored=False)
        product = parse_single_product(card)

        assert product is not None
        assert product.is_sponsored is False

    def test_skips_card_without_asin(self) -> None:
        """Should return None for cards with empty ASIN (headers, etc.)."""
        card = MagicMock()
        card.get_attribute.return_value = ""

        product = parse_single_product(card)
        assert product is None

    def test_skips_card_without_title(self) -> None:
        """Should return None when title cannot be extracted."""
        card = create_mock_card(title="")
        # Override to make title return empty
        original_side_effect = card.find_element.side_effect

        def mock_find(by, xpath):
            if "title-recipe" in xpath and "h2" in xpath and "a[" not in xpath:
                element = MagicMock()
                element.text = ""
                return element
            return original_side_effect(by, xpath)

        card.find_element.side_effect = mock_find
        product = parse_single_product(card)
        assert product is None

    def test_handles_missing_original_price(self) -> None:
        """Should set original_price to None when not available."""
        card = create_mock_card(original_price=None)
        product = parse_single_product(card)

        assert product is not None
        assert product.original_price is None

    def test_calculates_discount_from_prices(self) -> None:
        """Should auto-calculate discount when no badge exists."""
        card = create_mock_card(
            current_price="PKR 6,665.62",
            original_price="PKR 7,499.17",
        )
        product = parse_single_product(card)

        assert product is not None
        assert product.discount_percentage == "-11%"

    def test_product_to_dict(self) -> None:
        """Should convert Product to a dictionary correctly."""
        card = create_mock_card()
        product = parse_single_product(card)

        assert product is not None
        product_dict = product.to_dict()
        assert isinstance(product_dict, dict)
        assert product_dict["title"] == "JCZT Adjustable Laptop Stand"
        assert product_dict["asin"] == "B0BKSPYJ89"
        assert product_dict["is_sponsored"] is True
