"""
CSV exporter for the Amazon Product Search Scraper.

Exports a list of Product objects to a CSV file with UTF-8 BOM
encoding for compatibility with Microsoft Excel.

Usage:
    from exporters.csv_exporter import export_to_csv

    export_to_csv(products, "output/results.csv")
"""

import csv
from pathlib import Path

from models.product import Product
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Column headers for the CSV file — matches the Product dataclass fields
CSV_HEADERS: list[str] = [
    "title",
    "current_price",
    "original_price",
    "discount_percentage",
    "rating",
    "num_reviews",
    "is_prime",
    "is_sponsored",
    "product_url",
    "asin",
    "image_url",
]


def export_to_csv(products: list[Product], filepath: str) -> None:
    """Export product data to a CSV file.

    Creates the output directory if it doesn't exist. Uses UTF-8
    encoding with BOM (byte order mark) so that Excel opens the
    file correctly with special characters.

    Args:
        products: List of Product objects to export.
        filepath: The full path for the output CSV file.
    """
    if not products:
        logger.warning("No products to export to CSV.")
        return

    # Ensure the output directory exists
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(
            output_path,
            mode="w",
            newline="",
            encoding="utf-8-sig",  # UTF-8 with BOM for Excel
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=CSV_HEADERS,
                extrasaction="ignore",
            )

            # Write the header row
            writer.writeheader()

            # Write each product as a row
            for product in products:
                writer.writerow(product.to_dict())

        logger.info(
            "CSV export complete: %d products saved to '%s'",
            len(products),
            filepath,
        )

    except OSError as error:
        logger.error("Failed to export CSV to '%s': %s", filepath, str(error))
        raise
