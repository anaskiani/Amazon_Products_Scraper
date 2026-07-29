"""
SQLite exporter for the Amazon Product Search Scraper (Bonus Feature).

Exports a list of Product objects to a SQLite database. Uses
INSERT OR REPLACE keyed on ASIN to avoid duplicate entries
when re-running the scraper for the same products.

Usage:
    from exporters.sqlite_exporter import export_to_sqlite

    export_to_sqlite(products, "output/results.db")
"""

import sqlite3
from pathlib import Path

from models.product import Product
from utils.logger import setup_logger

logger = setup_logger(__name__)

# SQL statement to create the products table
CREATE_TABLE_SQL: str = """
    CREATE TABLE IF NOT EXISTS products (
        asin            TEXT PRIMARY KEY,
        title           TEXT NOT NULL,
        current_price   TEXT,
        original_price  TEXT,
        discount_percentage TEXT,
        rating          TEXT,
        num_reviews     TEXT,
        is_prime        INTEGER,
        is_sponsored    INTEGER,
        product_url     TEXT,
        image_url       TEXT
    )
"""

# SQL statement to insert or update a product
INSERT_SQL: str = """
    INSERT OR REPLACE INTO products (
        asin, title, current_price, original_price,
        discount_percentage, rating, num_reviews,
        is_prime, is_sponsored, product_url, image_url
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def export_to_sqlite(products: list[Product], db_path: str) -> None:
    """Export product data to a SQLite database.

    Creates the database file and products table if they don't exist.
    Uses INSERT OR REPLACE to update existing products (keyed on ASIN)
    instead of creating duplicates.

    Args:
        products: List of Product objects to export.
        db_path: The full path for the SQLite database file.
    """
    if not products:
        logger.warning("No products to export to SQLite.")
        return

    # Ensure the output directory exists
    output_path = Path(db_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    connection: sqlite3.Connection | None = None

    try:
        connection = sqlite3.connect(str(output_path))
        cursor: sqlite3.Cursor = connection.cursor()

        # Create the table if it doesn't exist
        cursor.execute(CREATE_TABLE_SQL)

        # Insert each product
        inserted_count: int = 0
        skipped_count: int = 0

        for product in products:
            # Skip products without an ASIN (can't use as primary key)
            if not product.asin:
                skipped_count += 1
                logger.debug(
                    "Skipping product without ASIN: %s",
                    product.title[:50],
                )
                continue

            cursor.execute(INSERT_SQL, (
                product.asin,
                product.title,
                product.current_price,
                product.original_price,
                product.discount_percentage,
                product.rating,
                product.num_reviews,
                int(product.is_prime),       # SQLite stores booleans as 0/1
                int(product.is_sponsored),   # SQLite stores booleans as 0/1
                product.product_url,
                product.image_url,
            ))
            inserted_count += 1

        # Commit all changes at once (faster than committing per row)
        connection.commit()

        logger.info(
            "SQLite export complete: %d products saved to '%s'"
            " (%d skipped — no ASIN)",
            inserted_count,
            db_path,
            skipped_count,
        )

    except sqlite3.Error as error:
        logger.error(
            "Failed to export to SQLite '%s': %s",
            db_path,
            str(error),
        )
        raise

    finally:
        if connection:
            connection.close()
