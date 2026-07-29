"""
Retry decorator for the Amazon Product Search Scraper.

Provides a reusable decorator that automatically retries a function
when it raises an exception. Useful for network-bound operations
like page loads and element lookups that may fail transiently.

Usage:
    from utils.retry import retry

    @retry(max_attempts=3, delay=2.0)
    def load_page(driver, url):
        driver.get(url)
"""

import time
import functools
from typing import Callable, Any

from utils.logger import setup_logger

logger = setup_logger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """Decorator that retries a function on failure.

    Args:
        max_attempts: Maximum number of times to attempt the function
                      (including the initial call). Must be >= 1.
        delay: Seconds to wait between retry attempts.
        exceptions: A tuple of exception types to catch and retry on.
                    Any exception NOT in this tuple will propagate
                    immediately without retrying.

    Returns:
        A decorator that wraps the target function with retry logic.

    Example:
        @retry(max_attempts=3, delay=2.0)
        def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as error:
                    last_exception = error
                    if attempt < max_attempts:
                        logger.warning(
                            "Attempt %d/%d failed for '%s': %s. "
                            "Retrying in %.1f seconds...",
                            attempt,
                            max_attempts,
                            func.__name__,
                            str(error),
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "All %d attempts failed for '%s'. "
                            "Last error: %s",
                            max_attempts,
                            func.__name__,
                            str(error),
                        )

            # If all attempts failed, raise the last exception
            raise last_exception  # type: ignore[misc]

        return wrapper
    return decorator
