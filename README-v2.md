# Beast Pro v2 — Job Ticket BP-V2-001

Built on Beast Pro Final (`beast_pro_final.py`). That file is **not changed
and not deleted**. v2 is a new file, `beast_pro_v2.py`, so you can compare
v1 and v2 side by side.

## What v2 adds

1. **`--pages N` and `--limit N`**
   - `--pages 2` scrapes only the first 2 catalog pages (1–50).
   - `--limit 20` limits exported output to 20 books. The checkpoint keeps
     the complete, de-duplicated listing so a later unrestricted resume does
     not lose books.
   - Example: `python beast_pro_v2.py --pages 2 --limit 20 --fast`

2. **Checkpoint saving and `--resume`**
   - After the listing pages, and again after the detail pages, v2 writes
     `outputs/checkpoint.json` with `pages_done` and the complete, un-truncated
     book list collected so far.
   - Run again with `--resume` and already-scraped pages are skipped.
   - Duplicates are prevented in two places: pages are skipped on resume,
     and books are still de-duplicated by URL, exactly as in v1.
   - The program prints clearly:
     - `Starting fresh - no checkpoint will be loaded.`
     - `Resuming: 1 pages, 20 books already saved. Already-scraped pages will be skipped.`
     - `Resuming requested, but no checkpoint found - starting fresh.`
   - Add `--no-checkpoint` if you do not want a checkpoint file.

3. **Professional Excel Summary sheet + better Books formatting**
   - New second sheet, **Summary**, with:
     total books, categories, average price (GBP and USD),
     cheapest and most expensive (USD), in-stock / out-of-stock totals,
     bad / Unknown category count, GBP→USD rate used,
     and a per-category table (books + average USD price).
   - Books sheet: bold headers, frozen header row (A2), auto-filter,
     readable column widths (kept from v1), price columns formatted as
     `$#,##0.00`, and coloured stock status — column D, `in_stock`:
     green for True, light red for False.
   - CSV, Excel, and HTML catalog output all still work, with the same
     data columns as v1. No output data was changed except the new
     Summary sheet and the formatting.

4. **One small fix found while testing**
   - `trust_env=True` was added to the `aiohttp.ClientSession`.
     This makes the scraper honour `HTTP(S)_PROXY` in proxied / work
     networks. It is harmless on a normal home PC, and it is why the
     first test in this workspace failed with an SSL error before the fix
     — the site itself was up, curl worked, aiohttp was not using the proxy.
   - Also added `scrape_listing_page_numbered()`, a tiny wrapper that
     returns the page number with the books. This is needed so the
     checkpoint knows which pages finished. The original
     `scrape_listing_page()` is unchanged.

## Files added / changed

| File | Change |
|---|---|
| `beast_pro_v2.py` | **NEW.** Complete v2 program, 1,975 lines. All v1 features preserved. |
| `beast_pro_final.py` | **NOT CHANGED.** Kept in the folder for comparison only. |
| `requirements.txt` | **NEW.** `aiohttp`, `beautifulsoup4`, `pandas`, `openpyxl`, `tqdm`, `lxml`. |
| `README-v2.md` | **NEW.** This file — install and test instructions. |
| `outputs/checkpoint.json` | Created at run time by v2. Not in GitHub yet — do not commit test outputs. |

Nothing was uploaded to GitHub. Inspect and test first, as requested.

## Install (Windows, VS Code)

```powershell
# In VS Code, open the project folder, then in the terminal:
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `pip install` says the environment is externally managed on Linux,
use a virtual environment as above — do not use `--break-system-packages`.

## Test — the exact run from the ticket

```powershell
# Fast test, 2 pages, 20 books
python beast_pro_v2.py --pages 2 --limit 20 --fast --output-dir outputs-v2-test
```

Expected result (numbers for the exchange rate will vary):
```
Pages: 2 (of 50)
Limit: 20 books
Starting fresh - no checkpoint will be loaded.
Checkpoint saved: outputs-v2-test/checkpoint.json
DONE
Books scraped: 20
```
Check the outputs:
- `outputs-v2-test/books.csv` — 20 rows
- `outputs-v2-test/books.xlsx` — sheets `Books` and `Summary`
- `outputs-v2-test/books_catalog.html` — opens in a browser
- `outputs-v2-test/checkpoint.json` — `pages_done: [1, 2]`, all 40 books preserved before the output limit

## Test resume — no duplicates

```powershell
python beast_pro_v2.py --pages 1 --fast --output-dir outputs-resume-test
python beast_pro_v2.py --pages 2 --resume --fast --output-dir outputs-resume-test
```

Expected: first run 20 books, second run prints
`Resuming: 1 pages, 20 books already saved…`, final total **40 books,
40 unique URLs, 0 duplicates**, checkpoint `pages_done: [1, 2]`.

## Full run (v1 behaviour)

```powershell
python beast_pro_v2.py
# or, with all v1 options still working:
python beast_pro_v2.py --fast --concurrency 20 --output-dir outputs
```

## How to put it on GitHub (when you are ready)

Do not do this until you have inspected and tested v2 locally.

In VS Code terminal, in the `data-amigos-pro` repo folder:
```powershell
git status
git add beast_pro_v2.py requirements.txt README-v2.md
git commit -m "Add Beast Pro v2 (BP-V2-001): --pages/--limit, checkpoint/resume, Excel Summary"
git push
```

Do **not** commit `outputs/`, `checkpoint.json`, or `.venv/`. Those are
local test files. If the repo does not already ignore them, add them to
`.gitignore` first.

## v2 fix — 2026-11-11, after Argon's test (BP-V2-001)

- Console banner changed from `BEAST PRO FINAL` to `BEAST PRO V2`.
- Checkpoint / `--limit` fix: the checkpoint now always stores the
  complete listing data before `--limit` is applied, with
  `limit_applied` / `limit_value` / `total_books_saved` recorded.
  `--limit` is an output filter only.
  Test: `--pages 2 --limit 20 --fast` outputs 20 books but the
  checkpoint holds 40. Then `--pages 2 --resume` with no limit
  outputs 40 books, 40 unique URLs, 0 duplicates.
- Dollar-sign price formatting in Excel was left exactly as it was,
  as requested.
