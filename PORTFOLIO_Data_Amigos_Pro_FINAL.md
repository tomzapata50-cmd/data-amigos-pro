# 📊 Data Amigos Pro

### *Powered by Beast Pro*

**Data Amigos Pro** is a portfolio-ready product-data extraction and catalog-building system that turns website listings into clean, structured data and a searchable customer-facing catalog.

## The Problem

Businesses often need more than raw scraped data.

They need information that is cleaned, organized, easy to review, and ready to use in spreadsheets, reports, or customer-facing tools.

## The Solution

I built **Data Amigos Pro**, powered by the **Beast Pro** asynchronous Python scraping engine.

The current demo processes a public practice catalog with:

- **1,000 products**
- **50 catalog pages**
- Individual product-detail pages
- Product images
- Categories
- Ratings
- Stock status
- GBP pricing
- USD conversion
- Direct product links

## What Beast Pro Does

Beast Pro handles the collection and processing layer with:

- Asynchronous requests using `aiohttp`
- Beautiful Soup parsing
- pandas data processing
- Retry and timeout handling
- Duplicate protection
- Category cleanup and validation
- Relative URL correction
- GBP-to-USD conversion with fallback handling
- CSV, Excel, and HTML export

## Customer-Facing Output

Data Amigos Pro generates:

- `books.csv`
- `books.xlsx`
- `books_catalog.html`

The browser catalog includes:

- Title/category search
- Category filters
- Max-price slider
- In-stock-only filtering
- Product images
- Ratings
- GBP and USD pricing
- Stock badges
- Direct product links
- Responsive desktop/mobile layout

## Going the Extra Mile

This project was built beyond a basic scraping exercise. I added reliability, validation, duplicate handling, multiple output formats, customer-facing presentation, and a branded interface so the collected data is useful after the scraping step is finished.

## Result

A complete workflow that takes raw website product information and turns it into structured data plus a polished, searchable catalog.

## Technology

**Python · asyncio · aiohttp · Beautiful Soup · pandas · openpyxl · HTML · CSS · JavaScript**

## Portfolio Proof

**Source:** Individual product pages from the public Books to Scrape practice site

**Result:** A 1,000-product Data Amigos Pro catalog with structured CSV/Excel exports and interactive browser filtering.

## Branding

**Data Amigos Pro**

*Powered by Beast Pro*

**Three Amigos**
