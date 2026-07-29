"""
Product parser for the Amazon Product Search Scraper.

Extracts product information from Amazon search result page cards.
Each field is extracted independently with its own error handling,
so a single failing field won't skip the entire product.

XPaths in this module are built using stable HTML attributes:
  - data-cy          (test/automation attributes — very stable)
  - data-component-type (component identifiers — very stable)
  - data-a-*         (Amazon custom data attributes — stable)
  - aria-label       (accessibility attributes — stable)
  - Semantic tags    (h2, img — stable)

Class names are avoided wherever possible.

Usage:
    from scraper.parser import parse_products

    products = parse_products(driver)  # Returns list of Product objects
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException

from models.product import Product
from config.settings import BASE_URL
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ══════════════════════════════════════════════════════════════
# XPaths — Built from user-inspected HTML using stable attributes
# ══════════════════════════════════════════════════════════════

# Each product card on the search results page
# Uses data-component-type (component identifier — very stable)
PRODUCT_CARD_XPATH: str = (
    "//div[@data-component-type='s-search-result']"
)

# ── Title ─────────────────────────────────────────────────────
# Path: div[data-cy="title-recipe"] > a > h2 > span
# Uses data-cy (test attribute — very stable) + semantic h2 tag
TITLE_XPATH: str = (
    ".//div[@data-cy='title-recipe']//h2//span"
)

# ── Current Price ─────────────────────────────────────────────
# Path: div[data-cy="price-recipe"] > span.a-price[data-a-color="base"]
#       > span.a-offscreen
# Uses data-cy + data-a-color (Amazon data attribute — stable)
# The a-offscreen span contains the full price text like "PKR 6,665.62"
CURRENT_PRICE_XPATH: str = (
    ".//div[@data-cy='price-recipe']"
    "//span[@class='a-price' and @data-a-color='base']"
    "/span[@class='a-offscreen']"
)

# ── Original Price (before discount) ─────────────────────────
# Path: div[data-cy="price-recipe"] > span[data-a-strike="true"]
#       > span.a-offscreen
# Uses data-a-strike="true" which marks the struck-through price
ORIGINAL_PRICE_XPATH: str = (
    ".//div[@data-cy='price-recipe']"
    "//span[@data-a-strike='true']"
    "/span[@class='a-offscreen']"
)

# ── Discount Percentage ──────────────────────────────────────
# Some products display a discount badge (e.g., "-20%" or "Save 11%")
# This varies by product and isn't always present.
# If not found, the parser will calculate it from prices.
DISCOUNT_XPATH: str = (
    ".//div[@data-cy='price-recipe']"
    "//span[contains(text(), '%')]"
)

# ── Rating (star rating) ─────────────────────────────────────
# Path: div[data-cy="reviews-block"] > i[data-cy="reviews-ratings-slot"]
#       > span.a-icon-alt
# Uses two data-cy attributes (very stable). The a-icon-alt span
# contains text like "4.7 out of 5 stars"
RATING_XPATH: str = (
    ".//div[@data-cy='reviews-block']"
    "//i[@data-cy='reviews-ratings-slot']"
    "//span[@class='a-icon-alt']"
)

# ── Number of Reviews ─────────────────────────────────────────
# Path: div[data-cy="reviews-block"] > a[aria-label*="ratings"]
# The aria-label contains the exact count like "1,028 ratings"
# We extract from aria-label for precision (displayed text shows "1K")
NUM_REVIEWS_XPATH: str = (
    ".//div[@data-cy='reviews-block']"
    "//a[contains(@aria-label, 'ratings')]"
)

# ── Prime Eligibility ────────────────────────────────────────
# Prime products display an <i> with class containing "a-icon-prime"
# This is one of the few cases where class is the most reliable
# selector, as Prime badges don't have data-cy attributes
PRIME_XPATH: str = (
    ".//i[contains(@class, 'a-icon-prime')]"
)

# ── Sponsored Status ─────────────────────────────────────────
# Sponsored products have a label with class "puis-label-popover-default"
# containing the text "Sponsored"
SPONSORED_XPATH: str = (
    ".//span[contains(@class, 'puis-label-popover-default')]"
)

# ── Product Link ──────────────────────────────────────────────
# Path: div[data-cy="title-recipe"] > a (the one containing h2)
# Uses data-cy + semantic h2 to find the correct <a> tag
PRODUCT_LINK_XPATH: str = (
    ".//div[@data-cy='title-recipe']//a[.//h2]"
)

# ── Product Image ─────────────────────────────────────────────
# Path: span[data-component-type="s-product-image"] > a > div > img
# Uses data-component-type (component identifier — very stable)
IMAGE_XPATH: str = (
    ".//span[@data-component-type='s-product-image']//img"
)


def parse_products(driver: webdriver.Chrome) -> list[Product]:
    """Find all product cards on the current page and parse each one.

    Args:
        driver: The active Chrome WebDriver on a search results page.

    Returns:
        A list of Product objects successfully parsed from the page.
        Products that fail to parse are skipped with a warning log.
    """
    products: list[Product] = []

    try:
        cards: list[WebElement] = driver.find_elements(
            By.XPATH, PRODUCT_CARD_XPATH
        )
        logger.info("Found %d product cards on the page.", len(cards))
    except Exception as error:
        logger.error("Failed to find product cards: %s", str(error))
        return products

    for index, card in enumerate(cards, start=1):
        try:
            product: Product | None = parse_single_product(card)
            if product:
                products.append(product)
                logger.debug(
                    "Product %d parsed: %s",
                    index,
                    product.title[:60],
                )
        except Exception as error:
            logger.warning(
                "Failed to parse product card %d: %s",
                index,
                str(error),
            )
            continue

    return products


def parse_single_product(card: WebElement) -> Product | None:
    """Extract all fields from a single product card.

    Each field is extracted independently with its own try/except
    so that one missing field doesn't prevent extracting the others.

    Args:
        card: A WebElement representing one product card.

    Returns:
        A Product object with all extracted fields, or None if
        the product has no title (minimum required field).
    """
    # ── ASIN (from the card's data-asin attribute) ────────────
    asin: str | None = _get_attribute(card, "data-asin")

    # Skip cards that are not actual products (e.g., header cards
    # that have an empty data-asin)
    if not asin:
        logger.debug("Skipping card — no ASIN found (likely a header/ad).")
        return None

    # ── Title (required — skip product if missing) ────────────
    title: str | None = _get_text(card, TITLE_XPATH)
    if not title:
        logger.debug("Skipping product (ASIN: %s) — no title found.", asin)
        return None

    # ── Current Price ─────────────────────────────────────────
    current_price: str | None = _get_text(card, CURRENT_PRICE_XPATH)

    # ── Original Price ────────────────────────────────────────
    original_price: str | None = _get_text(card, ORIGINAL_PRICE_XPATH)

    # ── Discount Percentage ───────────────────────────────────
    # Try to find an explicit discount badge first
    discount_percentage: str | None = _get_text(card, DISCOUNT_XPATH)

    # If no badge exists but both prices are available, calculate it
    if not discount_percentage and current_price and original_price:
        discount_percentage = _calculate_discount(
            current_price, original_price
        )

    # ── Rating ────────────────────────────────────────────────
    rating: str | None = _get_text(card, RATING_XPATH)

    # ── Number of Reviews ─────────────────────────────────────
    # Extract from the aria-label attribute for the precise count
    # (e.g., "1,028 ratings" instead of the displayed "(1K)")
    num_reviews: str | None = _get_element_attribute(
        card, NUM_REVIEWS_XPATH, "aria-label"
    )

    # ── Prime Eligibility ─────────────────────────────────────
    is_prime: bool = _element_exists(card, PRIME_XPATH)

    # ── Sponsored Status ──────────────────────────────────────
    is_sponsored: bool = _element_exists(card, SPONSORED_XPATH)

    # ── Product URL ───────────────────────────────────────────
    product_url: str = _get_link(card, PRODUCT_LINK_XPATH)

    # ── Image URL ─────────────────────────────────────────────
    image_url: str | None = _get_image_src(card, IMAGE_XPATH)

    return Product(
        title=title,
        current_price=current_price,
        original_price=original_price,
        discount_percentage=discount_percentage,
        rating=rating,
        num_reviews=num_reviews,
        is_prime=is_prime,
        is_sponsored=is_sponsored,
        product_url=product_url,
        asin=asin,
        image_url=image_url,
    )


# ══════════════════════════════════════════════════════════════
# Helper functions for safe element extraction
# ══════════════════════════════════════════════════════════════

def _get_text(card: WebElement, xpath: str) -> str | None:
    """Safely extract text content from an element within a card.

    Uses get_attribute('textContent') instead of .text because Amazon
    hides some text (like prices) using the .a-offscreen CSS class,
    and Selenium's .text property only returns visible text.

    Args:
        card: The parent product card WebElement.
        xpath: The relative XPath to the target element.

    Returns:
        The stripped text content, or None if not found.
    """
    if not xpath:
        return None
    try:
        element = card.find_element(By.XPATH, xpath)
        # Use textContent to capture text even if it is visually hidden
        content: str | None = element.get_attribute("textContent")
        if content:
            text: str = content.strip()
            return text if text else None
        return None
    except NoSuchElementException:
        return None
    except Exception as error:
        logger.debug("Error extracting text with xpath '%s': %s", xpath, error)
        return None


def _get_attribute(card: WebElement, attribute: str) -> str | None:
    """Safely extract an attribute value from the card element itself.

    Args:
        card: The product card WebElement.
        attribute: The attribute name to extract (e.g., 'data-asin').

    Returns:
        The attribute value, or None if not found or empty.
    """
    try:
        value: str | None = card.get_attribute(attribute)
        return value if value else None
    except Exception:
        return None


def _get_element_attribute(
    card: WebElement,
    xpath: str,
    attribute: str,
) -> str | None:
    """Safely extract an attribute from a child element within a card.

    Used when the desired data is in an HTML attribute (like aria-label)
    rather than the element's text content.

    Args:
        card: The parent product card WebElement.
        xpath: The relative XPath to the target element.
        attribute: The attribute name to extract from the found element.

    Returns:
        The attribute value, or None if not found.
    """
    if not xpath:
        return None
    try:
        element = card.find_element(By.XPATH, xpath)
        value: str | None = element.get_attribute(attribute)
        return value if value else None
    except NoSuchElementException:
        return None
    except Exception as error:
        logger.debug(
            "Error extracting attribute '%s' with xpath '%s': %s",
            attribute, xpath, error,
        )
        return None


def _get_link(card: WebElement, xpath: str) -> str:
    """Safely extract and normalize a product URL from a link element.

    Args:
        card: The parent product card WebElement.
        xpath: The relative XPath to the <a> element.

    Returns:
        The full product URL, or an empty string if not found.
    """
    if not xpath:
        return ""
    try:
        element = card.find_element(By.XPATH, xpath)
        href: str | None = element.get_attribute("href")
        if href:
            # If href is a relative path, prepend the base URL
            if href.startswith("/"):
                return BASE_URL + href
            return href
        return ""
    except NoSuchElementException:
        return ""
    except Exception as error:
        logger.debug("Error extracting link with xpath '%s': %s", xpath, error)
        return ""


def _get_image_src(card: WebElement, xpath: str) -> str | None:
    """Safely extract the src attribute from an image element.

    Args:
        card: The parent product card WebElement.
        xpath: The relative XPath to the <img> element.

    Returns:
        The image URL, or None if not found.
    """
    if not xpath:
        return None
    try:
        element = card.find_element(By.XPATH, xpath)
        return element.get_attribute("src")
    except NoSuchElementException:
        return None
    except Exception as error:
        logger.debug("Error extracting image with xpath '%s': %s", xpath, error)
        return None


def _element_exists(card: WebElement, xpath: str) -> bool:
    """Check if an element exists within the card (for boolean fields).

    Used for Prime eligibility and Sponsored status checks.

    Args:
        card: The parent product card WebElement.
        xpath: The relative XPath to check for.

    Returns:
        True if the element exists, False otherwise.
    """
    if not xpath:
        return False
    try:
        card.find_element(By.XPATH, xpath)
        return True
    except NoSuchElementException:
        return False
    except Exception:
        return False


def _calculate_discount(
    current_price: str,
    original_price: str,
) -> str | None:
    """Calculate the discount percentage from current and original prices.

    Extracts numeric values from price strings (removing currency
    symbols, commas, etc.) and calculates the percentage difference.

    Args:
        current_price: The current price string (e.g., "PKR 6,665.62").
        original_price: The original price string (e.g., "PKR 7,499.17").

    Returns:
        A discount string like "-11%" or None if calculation fails.
    """
    try:
        # Extract numeric value by keeping only digits, dots, and minus
        current_value: float = _extract_numeric_price(current_price)
        original_value: float = _extract_numeric_price(original_price)

        if original_value > 0 and current_value < original_value:
            discount: float = (
                (original_value - current_value) / original_value * 100
            )
            return f"-{discount:.0f}%"

        return None
    except (ValueError, ZeroDivisionError):
        return None


def _extract_numeric_price(price_str: str) -> float:
    """Extract a numeric value from a price string.

    Handles various formats like:
      - "$29.99"
      - "PKR 6,665.62"
      - "PKR\\xa06,665.62" (non-breaking space)

    Args:
        price_str: The raw price string from Amazon.

    Returns:
        The numeric price as a float.

    Raises:
        ValueError: If no numeric value can be extracted.
    """
    # Remove everything except digits, dots, and minus signs
    cleaned: str = ""
    for char in price_str:
        if char.isdigit() or char == "." or char == "-":
            cleaned += char
        elif char == ",":
            # Skip commas (thousand separators)
            continue

    if not cleaned:
        raise ValueError(f"No numeric value found in '{price_str}'")

    return float(cleaned)
