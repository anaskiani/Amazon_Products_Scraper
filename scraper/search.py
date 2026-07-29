"""
Search and pagination logic for the Amazon Product Search Scraper.

Handles:
  1. Navigating to Amazon's homepage
  2. Typing the keyword into the search bar and submitting
  3. Paginating through search result pages
  4. Calling the parser to extract products from each page
  5. Saving progress after each successful page (bonus)
  6. Taking screenshots on errors (bonus)

Usage:
    from scraper.search import search_amazon

    products = search_amazon(driver, keyword="laptop stand", num_pages=3)
"""

import time
import random
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)
from config.settings import (
    BASE_URL,
    SEARCH_URL_TEMPLATE,
    DEFAULT_TIMEOUT,
    SCREENSHOT_DIR,
    MIN_DELAY,
    MAX_DELAY,
)
from models.product import Product
from scraper.parser import parse_products
from utils.logger import setup_logger
from utils.retry import retry
from utils.resume import save_progress

logger = setup_logger(__name__)

# ── XPaths for the search bar ─────────────────────────────────
# These come directly from inspecting amazon.com's search bar
SEARCH_INPUT_XPATH: str = "//input[@id='twotabsearchtextbox']"
SEARCH_SUBMIT_XPATH: str = "//input[@id='nav-search-submit-button']"


def take_error_screenshot(driver: webdriver.Chrome, page: int) -> None:
    """Save a screenshot when an error occurs on a page.

    Screenshots are saved to the screenshots/ directory with a
    timestamp for easy debugging.

    Args:
        driver: The active Chrome WebDriver instance.
        page: The page number where the error occurred.
    """
    try:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename: str = f"error_page{page}_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename
        driver.save_screenshot(str(filepath))
        logger.info("Error screenshot saved: %s", filename)
    except Exception as error:
        logger.warning("Failed to save screenshot: %s", str(error))


@retry(max_attempts=3, delay=2.0)
def perform_initial_search(
    driver: webdriver.Chrome,
    keyword: str,
) -> None:
    """Navigate to Amazon and perform the initial search via the search bar.

    Types the keyword into the search input field and clicks the
    submit button, just like a real user would.

    Args:
        driver: The active Chrome WebDriver instance.
        keyword: The search term to type into the search bar.

    Raises:
        TimeoutException: If the search bar doesn't load in time.
    """
    logger.info("Navigating to Amazon homepage...")
    driver.get(BASE_URL)

    # Wait for the search input to be present and interactable
    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    search_input = wait.until(
        EC.element_to_be_clickable((By.XPATH, SEARCH_INPUT_XPATH))
    )
    logger.debug("Search input found. Typing keyword: '%s'", keyword)

    # Clear any existing text, pause, then type the keyword
    search_input.clear()
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    search_input.send_keys(keyword)

    # Human pause before clicking search
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    # Click the search/submit button
    submit_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, SEARCH_SUBMIT_XPATH))
    )
    submit_button.click()

    logger.info("Search submitted for keyword: '%s'", keyword)

    # Wait for the search results to load before returning
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[@data-component-type='s-search-result']")
        )
    )

    # Human pause after results load
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def navigate_to_page(
    driver: webdriver.Chrome,
    keyword: str,
    page: int,
) -> None:
    """Navigate to a specific page of search results using URL parameters.

    For page 1, we use the search bar (perform_initial_search).
    For pages 2+, we construct the URL directly — this is more
    reliable than clicking "Next" buttons.

    Args:
        driver: The active Chrome WebDriver instance.
        keyword: The search keyword (used to build the URL).
        page: The page number to navigate to (1-indexed).

    Raises:
        TimeoutException: If the page doesn't load in time.
    """
    url: str = SEARCH_URL_TEMPLATE.format(keyword=keyword, page=page)
    logger.info("Navigating to page %d: %s", page, url)
    driver.get(url)

    # Wait for search results to appear on the page.
    # We wait for the main results container to be present.
    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[@data-component-type='s-search-result']")
        )
    )

    # Human pause after page loads
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    logger.debug("Page %d loaded successfully.", page)


def set_delivery_location(driver: webdriver.Chrome, zipcode: str) -> None:
    """Set the delivery location on Amazon to a specific US zipcode.

    Args:
        driver: The active Chrome WebDriver instance.
        zipcode: The 5-digit US zip code.
    """
    logger.info("Setting delivery location to zipcode: %s", zipcode)
    driver.get(BASE_URL)

    wait = WebDriverWait(driver, 10)
    try:
        # Click the location popover link
        loc_link = wait.until(
            EC.element_to_be_clickable((By.ID, "nav-global-location-popover-link"))
        )
        loc_link.click()

        # Wait for the zip code input field
        zip_input = wait.until(
            EC.visibility_of_element_located((By.ID, "GLUXZipUpdateInput"))
        )
        time.sleep(random.uniform(0.5, 1.5))
        zip_input.clear()
        zip_input.send_keys(zipcode)
        time.sleep(random.uniform(0.5, 1.0))

        # Click the Apply button (using JS to avoid click interception by the modal overlay)
        apply_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='GLUXZipUpdate']//input | //*[@id='GLUXZipUpdate']//span[contains(@class, 'a-button-inner')]"))
        )
        driver.execute_script("arguments[0].click();", apply_btn)
        time.sleep(random.uniform(1.5, 2.5))

        # Wait for the Continue or Done button and click if it appears
        try:
            # Look for either the Continue button or the Done button
            continue_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='GLUXConfirmClose'] | //*[@id='GLUXConfirmClose-announce'] | //*[@name='glowDoneButton']"))
            )
            driver.execute_script("arguments[0].click();", continue_btn)
            time.sleep(random.uniform(1.0, 2.0))
        except TimeoutException:
            pass  # Some regions auto-refresh or do not show a continue button

        driver.refresh()
        
        # Human pause after setting location before starting the search
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        
        logger.info("Delivery location successfully updated.")
    except Exception as e:
        logger.warning("Failed to set delivery location: %s", str(e))



def search_amazon(
    driver: webdriver.Chrome,
    keyword: str,
    num_pages: int,
    start_page: int = 1,
    zipcode: str | None = None,
) -> list[Product]:
    """Scrape multiple pages of Amazon search results.

    This is the main orchestration function for the scraper.
    It handles the full flow: initial search → pagination →
    parsing → progress saving.

    Args:
        driver: The active Chrome WebDriver instance.
        keyword: The search term to scrape results for.
        num_pages: Total number of pages to scrape.
        start_page: The page to start scraping from (used for
                     resume functionality). Defaults to 1.

    Returns:
        A list of Product objects extracted from all scraped pages.
    """
    all_products: list[Product] = []
    end_page: int = num_pages
    last_page_asins: set[str] = set()

    logger.info(
        "Starting scrape: keyword='%s', pages %d to %d",
        keyword,
        start_page,
        end_page,
    )

    # ── Session & Location Initialization ──
    if zipcode:
        # Setting the delivery location visits the homepage and establishes a session
        set_delivery_location(driver, zipcode)
    elif start_page > 1:
        # If resuming without a zipcode, we must still visit the homepage first
        # to establish cookies. Direct linking to page 3 without cookies triggers a CAPTCHA.
        logger.info("Resuming scrape. Establishing session on homepage...")
        driver.get(BASE_URL)
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    for page in range(start_page, end_page + 1):
        logger.info(
            "━━━ Scraping page %d of %d ━━━",
            page,
            end_page,
        )

        try:
            # Page 1 (and it's the first page we're scraping):
            # use the search bar for a more natural interaction
            if page == 1 and start_page == 1:
                perform_initial_search(driver, keyword)
            else:
                # Pages 2+ (or resuming from a later page):
                # use direct URL navigation
                navigate_to_page(driver, keyword, page)

            # Parse products from the current page
            page_products: list[Product] = parse_products(driver)

            # Check if Amazon is just repeating the same products (end of results behavior)
            current_asins = {p.asin for p in page_products if p.asin}
            if current_asins and current_asins == last_page_asins:
                logger.warning(
                    "Page %d: Found the exact same products as the previous page. "
                    "Amazon has no more unique results. Stopping.",
                    page,
                )
                break
            
            last_page_asins = current_asins

            if page_products:
                all_products.extend(page_products)
                logger.info(
                    "Page %d: Extracted %d products (total: %d)",
                    page,
                    len(page_products),
                    len(all_products),
                )
            else:
                logger.warning(
                    "Page %d: No products found. This indicates "
                    "the end of search results. Stopping.",
                    page,
                )
                break

            # Save progress after each successful page (bonus)
            save_progress(keyword, page)

        except TimeoutException:
            logger.error(
                "Page %d: Timed out waiting for results to load. "
                "Assuming end of results or blocked. Stopping.",
                page,
            )
            take_error_screenshot(driver, page)
            break

        except WebDriverException as error:
            logger.error(
                "Page %d: WebDriver error: %s",
                page,
                str(error),
            )
            take_error_screenshot(driver, page)
            break

        except Exception as error:
            logger.error(
                "Page %d: Unexpected error: %s",
                page,
                str(error),
            )
            take_error_screenshot(driver, page)
            continue

    logger.info(
        "Scraping complete. Total products extracted: %d",
        len(all_products),
    )
    return all_products
