# Data Amigos Pro

Powered by Beast Pro  
Three Amigos

## Project overview

Data Amigos Pro transforms an online book catalog into clean, organized data and a searchable visual catalog. Built under the Three Amigos brand, it uses the Beast Pro scraping engine to deliver practical outputs for analysis, reporting, and product browsing.

## 📸 Project Showcase

![Data Amigos Pro customer-facing catalog](images/data-amigos-hero.png)

Data Amigos Pro customer-facing catalog with 1,000 products, 50 categories, search, filters, pricing, and branding.

![Source product page from Books to Scrape](images/source-product-page.png)

Example source product page from the public Books to Scrape practice site.

## Problem it solves

Manually collecting product information across dozens of pages takes time and can produce duplicate records, inconsistent categories, and broken links. Data Amigos Pro automates collection and cleanup, providing spreadsheet-ready data and a customer-friendly HTML catalog from the same dataset.

## How Beast Pro works

1. Scrapes all 50 catalog pages using asynchronous Python requests with aiohttp.
2. Parses titles, GBP prices, ratings, availability, image URLs, and product links with Beautiful Soup.
3. In full mode, visits all individual product pages for the collected books to retrieve categories.
4. Cleans and validates categories, removes duplicate products by URL, and corrects relative product and image URLs.
5. Processes records with pandas and converts GBP prices to USD using an online exchange rate, with a fallback if rate services are unavailable.
6. Exports CSV data, an Excel workbook using openpyxl, and a searchable HTML catalog.

Beast Pro stores image URLs; it does not download images locally. The HTML catalog displays remote product images from the source site.

## Current demo results

The current full-mode demo includes:

- **1,000 books** collected across **50 catalog pages**.
- Individual product-page category lookups for all collected books.
- **50 categories** for browsing and filtering.
- CSV, Excel, and HTML outputs.

These results describe the current demo. Subsequent runs depend on source content and successful requests.

## Features

### Collection and data quality

- Asynchronous Python scraping with configurable concurrency.
- Retry logic with increasing delays for failed requests.
- Timeout handling to limit request duration.
- Duplicate removal based on product URLs.
- Category cleaning and validation.
- Relative URL correction for product links and images.
- GBP to USD conversion with a fallback rate of **1 GBP = 1.25 USD**.
- CSV and Excel export.
- Progress reporting during collection.

### Searchable HTML catalog

- Search by title or category.
- Category filters.
- Max-price slider in USD.
- In-stock-only filter and stock badges.
- Remote product images.
- Ratings.
- GBP and USD pricing.
- Direct product links.
- Responsive layout for desktop and smaller screens.

## Technologies used

| Technology | Role |
| --- | --- |
| Python and asyncio | Scraping workflow and asynchronous task coordination. |
| aiohttp | Asynchronous HTTP requests and connection management. |
| Beautiful Soup | HTML parsing and product data extraction. |
| pandas | Data processing and export preparation. |
| openpyxl | Excel workbook export. |
| tqdm | Collection progress reporting. |
| HTML, CSS, and JavaScript | Catalog presentation, search, filters, and responsive layout. |

With Python and pip installed, install the dependencies from a terminal:

```bash
pip install aiohttp beautifulsoup4 pandas openpyxl tqdm
```

## Run command

From the `beastpro` project folder, run:

```bash
python beast_pro_final.py
```

This runs full mode: all catalog pages are scraped, and all collected books receive individual detail-page category lookups. An internet connection is required. The script generates the three output files in `outputs/`, replacing existing versions when run again.

## Fast mode

```bash
python beast_pro_final.py --fast
```

Fast mode still scrapes the full catalog across all 50 catalog pages. It skips individual detail-page category lookups to reduce requests and runtime, and marks category values as `Skipped (--fast)`.

It generates the same three output formats, but does not provide the full mode's category breakdown. Use full mode when meaningful category search and filtering are required.

## Output files

| File | Purpose |
| --- | --- |
| `outputs/books.csv` | Portable dataset for analysis, imports, and reporting. |
| `outputs/books.xlsx` | Excel workbook for spreadsheet review and analysis. |
| `outputs/books_catalog.html` | Searchable visual catalog with interactive filters. |

Open `outputs/books_catalog.html` in a browser to explore the catalog. Images remain hosted remotely and require access to the source site; there is no local image download folder.

USD prices are converted values. If the fallback exchange rate is used, those values do not reflect a live rate.

## Project structure

```text
beastpro/
├── beast_pro_final.py
├── README.md
└── outputs/
    ├── books.csv
    ├── books.xlsx
    └── books_catalog.html
```

## Extra engineering work

Beast Pro pairs asynchronous collection with request limits, retries, and timeouts to handle temporary network problems. Duplicate removal, category validation, and URL correction help turn raw page content into consistent, usable records.

Exchange-rate fallback handling allows exports to proceed when rate services are unavailable. Full and fast modes let users choose whether to include detail-page category lookups, while progress indicators make longer runs easier to follow.

The three output formats serve different needs: CSV for data workflows, Excel for spreadsheet users, and a responsive HTML catalog for visual browsing. Together, they demonstrate a complete path from collection to customer-facing presentation.

## Customer-facing branding

**Data Amigos Pro**  
Powered by Beast Pro  
Three Amigos

Data Amigos Pro is the project and customer-facing experience. Beast Pro is the underlying scraping and export engine. Three Amigos is the brand behind the project.

## Responsible use

This demo uses Books to Scrape, a public practice site designed for scraping exercises. Real client work should respect site terms, rate limits, permissions, and data-use requirements. Confirm that collection and reuse are permitted, and configure request volume appropriately for each site.

---

**Data Amigos Pro**  
Powered by Beast Pro  
Three Amigos
