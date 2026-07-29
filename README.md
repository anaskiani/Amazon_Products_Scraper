# Amazon Product Search Scraper

A modular, robust Python scraper built with Selenium that searches Amazon for products by keyword, extracts detailed product information across multiple pages, and exports the data to CSV, JSON, and SQLite.

## Features

- **Multi-page Scraping**: Automatically paginates through search results to extract data.
- **Rich Data Extraction**: Extracts Title, Current Price, Original Price, Discount Percentage, Rating, Number of Reviews, Prime Eligibility, Sponsored Status, Product URL, ASIN, and Image URL.
- **Robust Error Handling**: If a field fails to parse, it skips that field without dropping the whole product. If a page fails to load, it logs the error, takes a screenshot, and moves to the next page.
- **Anti-Detection**: Uses custom Chrome options (disabling automation flags, setting custom User-Agents) to avoid being blocked by Amazon.
- **Multiple Exporters**: Saves data to `CSV` (Excel friendly), `JSON`, and `SQLite` database.
- **Location Setting (Bonus)**: Specify a US Zip Code to set your delivery location before searching, bypassing international delivery walls and seeing US-exclusive prices.
- **Filtering (Bonus)**: Filter results by Prime eligibility, minimum star rating, and organic/sponsored status.
- **Resume Capability (Bonus)**: Saves progress automatically. If the scraper is interrupted, it can resume from the last successfully scraped page.
- **Auto Driver Management**: Uses `webdriver-manager` to automatically download and configure the correct ChromeDriver version.

---

## Project Structure

```text
Amazon_Automation/
├── main.py                    # Entry point — CLI argument parsing
├── requirements.txt           # Python dependencies
├── config/
│   └── settings.py            # Centralized configuration (URLs, timeouts, paths)
├── models/
│   └── product.py             # Product dataclass
├── scraper/
│   ├── driver.py              # WebDriver setup & teardown (anti-detection)
│   ├── search.py              # Amazon navigation and pagination logic
│   └── parser.py              # HTML parsing logic and XPaths
├── exporters/
│   ├── csv_exporter.py        # Export to CSV
│   ├── json_exporter.py       # Export to JSON
│   └── sqlite_exporter.py     # Export to SQLite database
├── utils/
│   ├── logger.py              # Centralized dual-handler logging
│   ├── retry.py               # @retry decorator for flaky operations
│   └── resume.py              # Progress tracking and resume logic
├── filters/
│   └── product_filter.py      # Post-scraping filters
├── tests/
│   ├── test_parser.py         # Unit tests for the parser
│   └── test_filters.py        # Unit tests for the filters
└── output/                    # Generated at runtime (results.csv, .json, .db)
└── logs/                      # Generated at runtime (scraper.log)
└── screenshots/               # Generated on errors
```

---

## Prerequisites

- **Python 3.10+** (uses `match/case` and modern type hints)
- **Google Chrome browser** installed on your system.

---

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd Amazon_Automation
   ```

2. **(Optional but recommended) Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

Run the scraper using the `main.py` script. The `--keyword` and `--pages` arguments are required.

### Basic Usage

Scrape 3 pages of results for "laptop stand" (runs headless by default):
```bash
python main.py --keyword "laptop stand" --pages 3
```

### Watch the Browser

If you want to see the browser clicking and navigating, add `--no-headless`:
```bash
python main.py --keyword "wireless mouse" --pages 2 --no-headless
```

### Applying Filters

Filter out sponsored products and keep only products rated 4.5 stars or higher:
```bash
python main.py --keyword "headphones" --pages 2 --organic-only --min-rating 4.5
```

Filter to keep only Amazon Prime products:
```bash
python main.py --keyword "monitor" --pages 3 --prime-only
```

### Setting Delivery Location

Amazon changes product availability and prices based on delivery location. Set a specific US zip code to fetch accurate local results (this works perfectly in the default headless mode):
```bash
python main.py --keyword "Table Tennis" --pages 2 --zipcode "10001"
```

### Resuming an Interrupted Scrape

If the scraper crashes or you interrupt it (Ctrl+C), progress is saved. You can resume exactly where it left off by adding `--resume`:
```bash
python main.py --keyword "laptop stand" --pages 5 --resume
```

---

## Outputs

All outputs are saved in the `output/` directory created at runtime.

1. **`results.csv`**: UTF-8 (BOM) encoded CSV file. Opens natively in Excel without character encoding issues.
2. **`results.json`**: Pretty-printed JSON containing the full extracted dataset.
3. **`results.db`**: SQLite database with a `products` table. Uses `ASIN` as the primary key. If you scrape the same products again, they will be updated rather than duplicated.

### Logs and Debugging

- **Logs**: Saved to `logs/scraper.log`. Contains detailed `DEBUG` information useful for troubleshooting.
- **Screenshots**: If an error occurs on a page (e.g., timeout, layout change), a screenshot is automatically saved to the `screenshots/` folder.

---

## Running Tests

Unit tests are written using `pytest`. They use mocked elements, meaning they run instantly without needing a browser.

To run the tests:
```bash
pytest tests/ -v
```
