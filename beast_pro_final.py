#!/usr/bin/env python3

"""
Beast Pro Final
Portfolio-ready async scraper for Books to Scrape.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import math
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm


BASE_URL = "https://books.toscrape.com/"
CATALOGUE_URL = urljoin(BASE_URL, "catalogue/")

TOTAL_PAGES = 50
DEFAULT_CONCURRENCY = 20
RETRIES = 3
REQUEST_TIMEOUT = 20
FALLBACK_GBP_USD = 1.25

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Beast Pro Final — async Books to Scrape scraper"
    )

    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip detail-page category lookups for maximum speed.",
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help="Maximum simultaneous requests.",
    )

    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Output folder.",
    )

    return parser.parse_args()


def clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def parse_price(value: str) -> float:
    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)",
        value.replace(",", ""),
    )

    return float(match.group(1)) if match else 0.0


def parse_rating(article: Any) -> int:
    tag = article.select_one("p.star-rating")

    if not tag:
        return 0

    for css_class in tag.get("class", []):
        if css_class in RATING_MAP:
            return RATING_MAP[css_class]

    return 0


async def fetch_text(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
) -> str:

    last_error: Exception | None = None

    for attempt in range(1, RETRIES + 1):

        try:
            async with semaphore:

                async with session.get(url) as response:

                    if (
                        response.status == 429
                        or 500 <= response.status < 600
                    ):
                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                            message=f"retryable HTTP {response.status}",
                            headers=response.headers,
                        )

                    response.raise_for_status()

                    return await response.text()

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ) as exc:

            last_error = exc

            if attempt == RETRIES:
                break

            await asyncio.sleep(
                0.75 * (2 ** (attempt - 1))
            )

    raise RuntimeError(
        f"Failed after {RETRIES} attempts: {url}"
    ) from last_error


def parse_listing_page(
    page_html: str,
    page_url: str,
) -> list[dict[str, Any]]:

    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    books = []

    for article in soup.select(
        "article.product_pod"
    ):

        title_link = article.select_one("h3 a")
        price_tag = article.select_one("p.price_color")
        stock_tag = article.select_one("p.instock")

        if not title_link or not price_tag:
            continue

        title = clean_text(
            title_link.get("title")
            or title_link.get_text(
                " ",
                strip=True,
            )
        )

        relative_url = title_link.get(
            "href",
            "",
        )

        product_url = urljoin(
            page_url,
            relative_url,
        )

        image_tag = article.select_one("img")

        image_src = (
            image_tag.get("src", "")
            if image_tag
            else ""
        )

        image_url = urljoin(
            page_url,
            image_src,
        )

        availability = clean_text(
            stock_tag.get_text(
                " ",
                strip=True,
            )
            if stock_tag
            else ""
        )

        price_gbp = parse_price(
            price_tag.get_text(
                " ",
                strip=True,
            )
        )

        books.append(
            {
                "title": title,
                "price_gbp": price_gbp,
                "url": product_url,
                "availability": availability,
                "in_stock": (
                    "in stock"
                    in availability.lower()
                ),
                "rating": parse_rating(article),
                "image": image_url,
            }
        )

    return books


def parse_category(
    detail_html: str,
) -> str:

    soup = BeautifulSoup(
        detail_html,
        "html.parser",
    )

    breadcrumb_items = soup.select(
        "ul.breadcrumb li"
    )

    for index, item in enumerate(
        breadcrumb_items
    ):

        text = clean_text(
            item.get_text(
                " ",
                strip=True,
            )
        )

        if (
            text.lower() == "books"
            and index + 1 < len(breadcrumb_items)
        ):

            candidate = clean_text(
                breadcrumb_items[
                    index + 1
                ].get_text(
                    " ",
                    strip=True,
                )
            )

            if (
                candidate
                and candidate.lower()
                not in {
                    "add a comment",
                    "unknown",
                    "books",
                }
            ):
                return candidate

    return "Unknown"
async def scrape_listing_page(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    page_number: int,
) -> list[dict[str, Any]]:

    if page_number == 1:
        url = BASE_URL
    else:
        url = urljoin(
            CATALOGUE_URL,
            f"page-{page_number}.html",
        )

    page_html = await fetch_text(
        session,
        url,
        semaphore,
    )

    return parse_listing_page(
        page_html,
        url,
    )


async def add_category(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    book: dict[str, Any],
) -> dict[str, Any]:

    try:
        detail_html = await fetch_text(
            session,
            book["url"],
            semaphore,
        )

        category = parse_category(
            detail_html
        )

    except Exception:
        category = "Unknown"

    return {
        **book,
        "category": category,
    }


async def get_gbp_usd_rate(
    session: aiohttp.ClientSession,
) -> float:

    endpoints = [
        "https://api.frankfurter.app/latest?from=GBP&to=USD",
        "https://open.er-api.com/v6/latest/GBP",
    ]

    for url in endpoints:

        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(
                    total=8
                ),
            ) as response:

                response.raise_for_status()

                data = await response.json(
                    content_type=None
                )

                if (
                    "rates" in data
                    and isinstance(
                        data["rates"],
                        dict,
                    )
                ):
                    rate = data["rates"].get(
                        "USD"
                    )

                    if rate:
                        return float(rate)

        except Exception:
            pass

    return FALLBACK_GBP_USD


def make_dataframe(
    books: list[dict[str, Any]],
    gbp_usd: float,
) -> pd.DataFrame:

    rows = []

    for book in books:

        row = dict(book)

        row.setdefault(
            "category",
            "Skipped (--fast)",
        )

        row["price_usd"] = round(
            float(row["price_gbp"])
            * gbp_usd,
            2,
        )

        rows.append(row)

    columns = [
        "title",
        "category",
        "availability",
        "in_stock",
        "rating",
        "price_gbp",
        "price_usd",
        "url",
        "image",
    ]

    df = pd.DataFrame(
        rows,
        columns=columns,
    )

    if not df.empty:

        df = df.sort_values(
            by=[
                "category",
                "title",
            ],
            key=lambda col: (
                col.astype(str)
                .str.lower()
            ),
        ).reset_index(
            drop=True
        )

    return df


def export_csv(
    df: pd.DataFrame,
    output_dir: Path,
) -> Path:

    path = (
        output_dir
        / "books.csv"
    )

    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
    )

    return path


def export_excel(
    df: pd.DataFrame,
    output_dir: Path,
) -> Path:

    path = (
        output_dir
        / "books.xlsx"
    )

    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Books",
        )

        ws = writer.book["Books"]

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        widths = {
            "A": 46,
            "B": 24,
            "C": 22,
            "D": 12,
            "E": 10,
            "F": 12,
            "G": 12,
            "H": 58,
            "I": 58,
        }

        for column, width in widths.items():
            ws.column_dimensions[
                column
            ].width = width

    return path

def build_html_catalog(
    df: pd.DataFrame,
    gbp_usd: float,
) -> str:

    categories = sorted(
        {
            str(value)
            for value in df["category"].dropna()
        },
        key=str.lower,
    )

    max_price = 0

    if not df.empty:
        max_price = int(
            math.ceil(
                float(df["price_usd"].max())
            )
        )

    category_buttons = "\n".join(
        f'<button class="chip" '
        f'data-category="{html.escape(category, quote=True)}">'
        f'{html.escape(category)}</button>'
        for category in categories
    )

    cards = []

    for _, row in df.iterrows():

        title = html.escape(
            str(row["title"])
        )

        category = html.escape(
            str(row["category"])
        )

        availability = html.escape(
            str(row["availability"])
        )

        product_url = html.escape(
            str(row["url"]),
            quote=True,
        )

        image_url = html.escape(
            str(row["image"]),
            quote=True,
        )

        price_gbp = float(
            row["price_gbp"]
        )

        price_usd = float(
            row["price_usd"]
        )

        rating = int(
            row["rating"]
        )

        in_stock = bool(
            row["in_stock"]
        )

        stars = (
            "★" * rating
            + "☆" * (5 - rating)
        )

        stock_label = (
            "IN STOCK"
            if in_stock
            else "OUT OF STOCK"
        )

        cards.append(
            f"""
<article
    class="card"
    data-title="{title.lower()}"
    data-category="{category}"
    data-price="{price_usd:.2f}"
    data-stock="{str(in_stock).lower()}"
>

<div class="book-image-wrap">

<a
href="{product_url}"
target="_blank"
rel="noopener"
>
<img
src="{image_url}"
alt="{title}"
loading="lazy"
>
</a>

<span class="stock-badge {'yes' if in_stock else 'no'}">
{stock_label}
</span>

</div>

<div class="content">

<div class="category">
{category}
</div>

<h2>
{title}
</h2>

<div class="rating-row">

<span class="rating">
{stars}
</span>

<span class="rating-number">
{rating}/5
</span>

</div>

<div class="price-row">

<span class="gbp">
£{price_gbp:.2f}
</span>

<span class="usd">
${price_usd:.2f}
</span>

</div>

<p class="availability">
{availability}
</p>

<a
class="open"
href="{product_url}"
target="_blank"
rel="noopener"
>
View Book
</a>

</div>

</article>
"""
        )

    cards_html = "\n".join(cards)

    return f"""<!doctype html>

<html lang="en">

<head>

<meta charset="utf-8">

<meta
name="viewport"
content="width=device-width,initial-scale=1"
>

<title>
Beast Pro Final
</title>

<style>

:root {{
    --bg: #0d1117;
    --panel: #151b23;
    --panel2: #1c2530;
    --text: #f5f7fa;
    --muted: #9aa7b5;
    --gold: #f0b429;
    --gold2: #ffd66b;
    --border: rgba(255,255,255,.09);
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: "Segoe UI", Arial, sans-serif;
    color: var(--text);

    background:
        radial-gradient(
            circle at top left,
            rgba(240,180,41,.12),
            transparent 28%
        ),
        linear-gradient(
            180deg,
            #0b0f14,
            #111820
        );

    min-height: 100vh;
}}

.hero {{
    padding: 40px 20px 30px;
    background: #0b0f14;
    border-bottom: 1px solid var(--border);
}}

.hero-inner {{
    max-width: 1220px;
    margin: auto;

    display: flex;
    justify-content: space-between;
    align-items: end;
    gap: 24px;
    flex-wrap: wrap;
}}

.brand {{
    display: flex;
    align-items: center;
    gap: 14px;
}}

.beast-mark {{
    width: 58px;
    height: 58px;

    display: grid;
    place-items: center;

    border-radius: 16px;

    background:
        linear-gradient(
            145deg,
            var(--gold),
            #c98700
        );

    color: #111;
    font-size: 30px;
    font-weight: 900;
}}

.hero h1 {{
    margin: 0;
    font-size: 46px;
    line-height: 1;
}}

.hero h1 span {{
    color: var(--gold);
}}

.hero p {{
    margin: 8px 0 0;
    color: var(--muted);
}}

.stats {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}}

.stat {{
    background: rgba(255,255,255,.05);
    border: 1px solid var(--border);

    border-radius: 14px;
    padding: 10px 14px;
    min-width: 120px;
}}

.stat strong {{
    display: block;
    color: var(--gold2);
    font-size: 18px;
}}

.stat span {{
    color: var(--muted);
    font-size: 12px;
}}

.controls {{
    max-width: 1220px;
    margin: 0 auto;
    padding: 18px 20px;
}}

.search-row {{
    display: grid;

    grid-template-columns:
        minmax(0,1fr)
        auto
        auto;

    gap: 10px;
}}

input[type="search"] {{
    width: 100%;
    padding: 13px 15px;

    background: var(--panel);
    color: var(--text);

    border: 1px solid var(--border);
    border-radius: 14px;

    font-size: 16px;
}}

.filter-box {{
    background: var(--panel);

    border: 1px solid var(--border);
    border-radius: 14px;

    padding: 10px 12px;

    color: var(--muted);
}}

input[type="range"],
input[type="checkbox"] {{
    accent-color: var(--gold);
}}

.chips {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 12px;
}}

.chip {{
    background: var(--panel);
    color: var(--text);

    border: 1px solid var(--border);
    border-radius: 999px;

    padding: 8px 12px;

    cursor: pointer;
}}

.chip.active {{
    background: var(--gold);
    color: #111;
    font-weight: 800;
}}

.catalog-head {{
    max-width: 1220px;
    margin: 16px auto 0;
    padding: 0 20px;

    display: flex;
    justify-content: space-between;
}}

#count {{
    color: var(--muted);
}}

.grid {{
    max-width: 1220px;
    margin: auto;

    padding:
        16px 20px
        50px;

    display: grid;

    grid-template-columns:
        repeat(
            auto-fill,
            minmax(230px,1fr)
        );

    gap: 18px;
}}

.card {{
    overflow: hidden;

    border-radius: 20px;

    border: 1px solid var(--border);

    background:
        linear-gradient(
            180deg,
            var(--panel2),
            var(--panel)
        );

    transition: .2s ease;
}}

.card:hover {{
    transform: translateY(-5px);
    border-color: rgba(240,180,41,.5);
}}

.book-image-wrap {{
    position: relative;

    background: #0d131a;

    padding:
        18px
        18px
        0;
}}

.book-image-wrap img {{
    width: 100%;
    height: 250px;

    object-fit: contain;

    display: block;

    border-radius: 12px;
}}

.stock-badge {{
    position: absolute;
    top: 14px;
    right: 14px;

    padding: 6px 8px;

    border-radius: 999px;

    font-size: 10px;
    font-weight: 900;
}}

.stock-badge.yes {{
    background: #1fbe68;
}}

.stock-badge.no {{
    background: #cd4141;
}}

.content {{
    padding: 16px;
}}

.category {{
    color: var(--gold2);

    font-size: 11px;
    font-weight: 800;

    text-transform: uppercase;

    margin-bottom: 7px;
}}

h2 {{
    margin: 0 0 12px;

    font-size: 17px;
    line-height: 1.3;

    min-height: 44px;
}}

.rating-row {{
    display: flex;
    gap: 8px;

    margin-bottom: 12px;
}}

.rating {{
    color: var(--gold);
}}

.rating-number {{
    color: var(--muted);
    font-size: 12px;
}}

.price-row {{
    display: flex;
    gap: 10px;

    align-items: baseline;
}}

.gbp {{
    font-size: 20px;
    font-weight: 900;
}}

.usd {{
    color: var(--muted);
}}

.availability {{
    color: var(--muted);
    font-size: 12px;
}}

.open {{
    display: block;

    text-align: center;

    padding: 11px;

    border-radius: 12px;

    background:
        linear-gradient(
            var(--gold2),
            var(--gold)
        );

    color: #111;

    font-weight: 900;

    text-decoration: none;
}}

.hidden {{
    display: none;
}}

footer {{
    text-align: center;

    padding: 25px;

    border-top: 1px solid var(--border);

    color: var(--muted);
}}

@media (max-width: 800px) {{

    .search-row {{
        grid-template-columns: 1fr;
    }}

}}

</style>

</head>

<body>

<header class="hero">

<div class="hero-inner">

<div class="brand">

<div class="beast-mark">
B
</div>

<div>

<h1>
BEAST
<span>PRO</span>
</h1>

<p>
Three Amigos Scraping Project
</p>

</div>

</div>

<div class="stats">

<div class="stat">
<strong>{len(df)}</strong>
<span>Books</span>
</div>

<div class="stat">
<strong>{len(categories)}</strong>
<span>Categories</span>
</div>

<div class="stat">
<strong>{gbp_usd:.4f}</strong>
<span>GBP → USD</span>
</div>

</div>

</div>

</header>

<section class="controls">

<div class="search-row">

<input
id="search"
type="search"
placeholder="Search title or category..."
>

<label class="filter-box">

Max USD:

<input
id="price"
type="range"
min="0"
max="{max_price}"
value="{max_price}"
>

<strong id="priceValue">
${max_price}
</strong>

</label>

<label class="filter-box">

<input
id="stockOnly"
type="checkbox"
>

In stock only

</label>

</div>

<div class="chips">

<button
class="chip active"
data-category="ALL"
>
All
</button>

{category_buttons}

</div>

</section>

<div class="catalog-head">

<h3>
Catalog Results
</h3>

<div id="count">
</div>

</div>

<main
class="grid"
id="catalog"
>

{cards_html}

</main>

<footer>
Beast Pro Final
</footer>

<script>

(() => {{

const search =
    document.getElementById("search");

const price =
    document.getElementById("price");

const priceValue =
    document.getElementById("priceValue");

const stockOnly =
    document.getElementById("stockOnly");

const cards =
    [...document.querySelectorAll(".card")];

const chips =
    [...document.querySelectorAll(".chip")];

const count =
    document.getElementById("count");

let activeCategory = "ALL";


function applyFilters() {{

    const q =
        search.value
        .trim()
        .toLowerCase();

    const maxPrice =
        Number(price.value);

    const requireStock =
        stockOnly.checked;

    let visible = 0;

    cards.forEach(card => {{

        const title =
            card.dataset.title;

        const category =
            card.dataset.category;

        const cardPrice =
            Number(card.dataset.price);

        const inStock =
            card.dataset.stock === "true";

        const matchesText =
            !q
            ||
            title.includes(q)
            ||
            category
            .toLowerCase()
            .includes(q);

        const matchesCategory =
            activeCategory === "ALL"
            ||
            category === activeCategory;

        const matchesPrice =
            cardPrice <= maxPrice;

        const matchesStock =
            !requireStock
            ||
            inStock;

        const show =
            matchesText
            &&
            matchesCategory
            &&
            matchesPrice
            &&
            matchesStock;

        card.classList.toggle(
            "hidden",
            !show
        );

        if (show) {{
            visible++;
        }}

    }});

    priceValue.textContent =
        "$" + maxPrice;

    count.textContent =
        visible
        + " book"
        + (
            visible === 1
            ? ""
            : "s"
        )
        + " shown";
}}


search.addEventListener(
    "input",
    applyFilters
);

price.addEventListener(
    "input",
    applyFilters
);

stockOnly.addEventListener(
    "change",
    applyFilters
);


chips.forEach(chip => {{

    chip.addEventListener(
        "click",
        () => {{

            activeCategory =
                chip.dataset.category;

            chips.forEach(
                c =>
                    c.classList.remove(
                        "active"
                    )
            );

            chip.classList.add(
                "active"
            );

            applyFilters();

        }}
    );

}});


applyFilters();

}})();

</script>

</body>

</html>
"""


def export_html(
    df: pd.DataFrame,
    output_dir: Path,
    gbp_usd: float,
) -> Path:

    path = (
        output_dir
        / "books_catalog.html"
    )

    path.write_text(
        build_html_catalog(
            df,
            gbp_usd,
        ),
        encoding="utf-8",
    )

    return path

async def run(
    args: argparse.Namespace,
) -> int:

    if args.concurrency < 1:
        print(
            "ERROR: --concurrency must be at least 1"
        )
        return 2

    output_dir = Path(
        args.output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; BeastProFinal/1.0)"
        )
    }

    semaphore = asyncio.Semaphore(
        args.concurrency
    )

    connector = aiohttp.TCPConnector(
        limit=max(
            args.concurrency,
            1,
        )
    )

    async with aiohttp.ClientSession(
        timeout=timeout,
        headers=headers,
        connector=connector,
    ) as session:

        print()
        print("BEAST PRO FINAL")
        print(f"Target: {BASE_URL}")
        print(f"Pages: {TOTAL_PAGES}")
        print(
            f"Concurrency: "
            f"{args.concurrency}"
        )

        print(
            "Mode:",
            "FAST"
            if args.fast
            else "FULL",
        )

        print()

        rate_task = asyncio.create_task(
            get_gbp_usd_rate(
                session
            )
        )

        listing_tasks = [
            asyncio.create_task(
                scrape_listing_page(
                    session,
                    semaphore,
                    page,
                )
            )
            for page
            in range(
                1,
                TOTAL_PAGES + 1,
            )
        ]

        books = []

        for task in tqdm(
            asyncio.as_completed(
                listing_tasks
            ),
            total=len(
                listing_tasks
            ),
            desc="Catalog pages",
            unit="page",
        ):

            try:
                page_books = await task
                books.extend(
                    page_books
                )

            except Exception as exc:
                print(
                    "\nWarning: "
                    "one catalog page failed:",
                    exc,
                    file=sys.stderr,
                )

        unique = {}

        for book in books:
            unique[
                book["url"]
            ] = book

        books = list(
            unique.values()
        )

        if (
            not args.fast
            and books
        ):

            detail_tasks = [
                asyncio.create_task(
                    add_category(
                        session,
                        semaphore,
                        book,
                    )
                )
                for book
                in books
            ]

            detailed = []

            for task in tqdm(
                asyncio.as_completed(
                    detail_tasks
                ),
                total=len(
                    detail_tasks
                ),
                desc="Book details",
                unit="book",
            ):

                detailed.append(
                    await task
                )

            books = detailed

        else:

            for book in books:
                book["category"] = (
                    "Skipped (--fast)"
                )

        gbp_usd = await rate_task


    df = make_dataframe(
        books,
        gbp_usd,
    )

    csv_path = export_csv(
        df,
        output_dir,
    )

    excel_path = export_excel(
        df,
        output_dir,
    )

    html_path = export_html(
        df,
        output_dir,
        gbp_usd,
    )

    print()
    print("DONE")

    print(
        f"Books scraped: "
        f"{len(df)}"
    )

    print(
        f"GBP→USD rate: "
        f"{gbp_usd:.4f}"
    )

    print(
        f"CSV:   "
        f"{csv_path.resolve()}"
    )

    print(
        f"Excel: "
        f"{excel_path.resolve()}"
    )

    print(
        f"HTML:  "
        f"{html_path.resolve()}"
    )

    bad_categories = {
        "add a comment",
        "unknown",
    }

    bad_count = (
        df["category"]
        .astype(str)
        .str.lower()
        .isin(
            bad_categories
        )
        .sum()
    )

    print(
        f"Bad category labels: "
        f"{bad_count}"
    )

    return (
        0
        if not df.empty
        else 1
    )


def main() -> None:

    args = parse_args()

    raise SystemExit(
        asyncio.run(
            run(args)
        )
    )


if __name__ == "__main__":
    main()