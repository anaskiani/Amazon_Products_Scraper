"""
WebDriver setup and teardown for the Amazon Product Search Scraper.

Handles the creation and configuration of a Chrome WebDriver instance
with anti-detection measures, and provides a clean teardown function.

Usage:
    from scraper.driver import create_driver, close_driver

    driver = create_driver(headless=True)
    # ... use the driver ...
    close_driver(driver)
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from config.settings import (
    USER_AGENT,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    PAGE_LOAD_TIMEOUT,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_driver(headless: bool = True) -> webdriver.Chrome:
    """Create and configure a Chrome WebDriver instance.

    Sets up Chrome with anti-detection options to reduce the chance
    of being identified as an automated browser. Uses webdriver-manager
    to automatically download and manage the correct ChromeDriver version.

    Args:
        headless: If True, the browser runs without a visible window.
                  If False, you can watch the browser interact with pages.

    Returns:
        A fully configured Chrome WebDriver instance ready for use.
    """
    logger.info("Initializing Chrome WebDriver (headless=%s)...", headless)

    # ── Configure Chrome Options ──────────────────────────────
    chrome_options = Options()

    if headless:
        chrome_options.add_argument("--headless=new")

    # Anti-detection: Remove the "Chrome is being controlled by
    # automated software" infobar and automation flags
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Set a realistic user-agent string
    chrome_options.add_argument(f"--user-agent={USER_AGENT}")

    # Performance and stability options
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-popup-blocking")

    # Set a consistent window size for predictable element positions
    chrome_options.add_argument(f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}")

    # Disable images to speed up loading (optional — comment out if
    # you need to verify image URLs visually)
    # chrome_options.add_argument("--blink-settings=imagesEnabled=false")

    # ── Create the WebDriver ──────────────────────────────────
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Set page load timeout — raises TimeoutException if page
        # takes longer than this to load
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

        # Remove the navigator.webdriver flag that sites use to
        # detect Selenium
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            },
        )

        logger.info("Chrome WebDriver initialized successfully.")
        return driver

    except Exception as error:
        logger.error("Failed to initialize Chrome WebDriver: %s", str(error))
        raise


def close_driver(driver: webdriver.Chrome) -> None:
    """Safely close and quit the WebDriver instance.

    Handles any exceptions during cleanup so the main program
    doesn't crash during teardown.

    Args:
        driver: The Chrome WebDriver instance to close.
    """
    try:
        if driver:
            driver.quit()
            logger.info("Chrome WebDriver closed successfully.")
    except Exception as error:
        logger.warning("Error while closing WebDriver: %s", str(error))
