# Ekantipur Scraper

Python scraper for [Kantipur / ekantipur.com](https://ekantipur.com) that collects the top five मनोरञ्जन (entertainment) article summaries and the homepage **कार्टुन** (cartoon) slot, then writes structured JSON for assessment or downstream use.

## Requirements

- **Python** 3.11 or newer
- **[uv](https://docs.astral.sh/uv/)** package manager
- **Playwright** with **Chromium** (installed via Playwright CLI)

Optional (for demo video only):

- **imageio-ffmpeg** (declared in `pyproject.toml`) — bundled ffmpeg used to encode `recording.mp4`

## Project layout

| File | Purpose |
|------|---------|
| `scraper.py` | Main Playwright scraper: navigation, extraction, `output.json`, inline validation |
| `output.json` | Generated output (UTF-8, Nepali preserved; not committed if listed in `.gitignore`) |
| `pyproject.toml` | Project metadata and dependencies (`playwright`, `imageio-ffmpeg`) |
| `prompts.txt` | Prompt log template for the practical test (fill in candidate name and date) |
| `recording.mp4` | Optional screen recording of the scrape flow (generate with `record_scrape_demo.py`) |
| `check.py` | Local validator: required files, JSON shape, and basic `scraper.py` policy checks |
| `record_scrape_demo.py` | Records a short MP4 of the same route the scraper uses |

## Initial setup

Install uv (once per machine):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create the environment and install dependencies:

```bash
cd scrapper
uv sync
uv run playwright install chromium
```

Sanity check:

```bash
uv run python --version
uv run python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

## Run the scraper

```bash
uv run python scraper.py
```

The script:

1. Launches Chromium in **headless** mode with a fixed viewport and a desktop user agent.
2. Opens the homepage, then enters मनोरञ्जन (entertainment) via the nav link (with a direct URL fallback).
3. Collects **five** distinct dated article URLs under `/entertainment/YYYY/...`, reading titles, thumbnail URLs (including lazy `data-src`), category (defaults to `मनोरञ्जन`), and author when visible in the listing card.
4. Returns to the homepage, scrolls to load lazy sections, and reads the **कार्टुन** swiper (`.section-news` / `.cartoon-slider`).
5. Writes `output.json` next to `scraper.py` using `ensure_ascii=False` so Devanagari is not JSON-escaped.
6. Runs `validate_output()` and prints `[PASS]` / `[FAIL]` lines for each check.

## Output format (`output.json`)

```json
{
  "entertainment_news": [
    {
      "title": "string",
      "image_url": "https://...",
      "category": "string",
      "author": "string or null"
    }
  ],
  "cartoon_of_the_day": {
    "title": "string",
    "image_url": "https://...",
    "author": "string or null"
  }
}
```

- `entertainment_news` must contain exactly **five** items.
- Each `image_url` must be an absolute `http` or `https` URL.
- `author` may be `null` when the listing does not expose a byline.

## Run the submission checker

```bash
uv run python check.py
```

On success it prints: `ALL CHECKS PASSED - READY TO SUBMIT`. It verifies presence of the expected files, JSON validity, field keys, absolute image URLs, Devanagari content, and simple static rules on `scraper.py` (e.g. `headless=True`, no `page.pause()`, paths via `os.path`).

## Optional: generate `recording.mp4`

```bash
uv run python record_scrape_demo.py
```

This records the viewport (entertainment page, then homepage with scroll) and writes `recording.mp4` in the project root. It does not replace manual DevTools inspection; it is a short demo clip for reviewers.

## Debugging in a visible browser

For local debugging only, you may temporarily change the launch call in `scraper.py` from `headless=True` to `headless=False`, run the scraper, then **restore** `headless=True` before submission. Do not commit or submit with headed mode unless the assessor asks for it.

## DOM notes (maintenance)

The live site uses listing rows such as `div.category-inner-wrapper` with images under `.category-image` (often `thumb.php?src=...` URLs). Thumbnails may use lazy attributes (`data-src`). The cartoon block is tied to a heading link to `/cartoon` and a `.cartoon-slider` carousel. If the layout changes, update selectors in `scraper.py` and re-run `check.py`.

## Packaging for submission

Follow the instructions from the assessment (zip contents and exclusions). Typical Linux/macOS example (adjust excludes to match the brief):

```bash
cd ..
zip -r ekantipur-scraper.zip ekantipur-scraper/ \
  --exclude "ekantipur-scraper/.venv/*" \
  --exclude "ekantipur-scraper/__pycache__/*"
```

Replace `[YOUR NAME]` and the date in `prompts.txt` before zipping.

## License / ethics

This tool is for educational or assigned evaluation use. Respect ekantipur.com terms of service, rate limits, and robots policy; do not overload their servers or redistribute full article body text without permission.
# scrapper
# scrapper
