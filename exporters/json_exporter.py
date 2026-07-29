"""
JSON exporter for the Amazon Product Search Scraper.

Exports a list of Product objects to a formatted JSON file
with proper indentation and full Unicode support.

Usage:
    from exporters.json_exporter import export_to_json

    export_to_json(products, "output/results.json")
"""

import json
from pathlib import Path

from models.product import Product
from utils.logger import setup_logger

logger = setup_logger(__name__)


def export_to_json(products: list[Product], filepath: str) -> None:
    """Export product data to a JSON file.

    Creates the output directory if it doesn't exist. The output
    is formatted with 2-space indentation for readability.

    Args:
        products: List of Product objects to export.
        filepath: The full path for the output JSON file.
    """
    if not products:
        logger.warning("No products to export to JSON.")
        return

    # Ensure the output directory exists
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Convert each Product to a dictionary
        products_data: list[dict] = [
            product.to_dict() for product in products
        ]

        with open(
            output_path,
            mode="w",
            encoding="utf-8",
        ) as json_file:
            json.dump(
                products_data,
                json_file,
                indent=2,
                ensure_ascii=False,  # Preserve Unicode characters (PKR, etc.)
            )

        logger.info(
            "JSON export complete: %d products saved to '%s'",
            len(products),
            filepath,
        )

    except OSError as error:
        logger.error("Failed to export JSON to '%s': %s", filepath, str(error))
        raise
