# SECTION 1: IMPORTS
from playwright.sync_api import sync_playwright
import json
import os
import time

# SECTION 2: CONSTANTS
BASE_URL = "https://ekantipur.com"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output.json")
ENTERTAINMENT_ARTICLES_COUNT = 5


# SECTION 3: HELPER FUNCTIONS
def make_absolute_url(url: str, base: str = BASE_URL) -> str | None:
    """
    Convert relative URL to absolute URL.
    If URL already starts with http return as is.
    If URL starts with // prepend https:
    If URL starts with / prepend BASE_URL
    Return None if url is None or empty
    """
    try:
        if url is None:
            return None
        u = url.strip()
        if not u:
            return None
        if u.startswith("http://") or u.startswith("https://"):
            return u
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return base.rstrip("/") + u
        return base.rstrip("/") + "/" + u.lstrip("/")
    except Exception:
        return None


def clean_text(text: str | None) -> str | None:
    """
    Strip leading/trailing whitespace from text.
    Return None if text is None or empty after stripping.
    """
    if text is None:
        return None
    s = text.strip()
    return s if s else None


def _is_dated_entertainment_article_url(url: str) -> bool:
    """True if path looks like /entertainment/YYYY/... (any calendar year)."""
    if not url or "/entertainment/" not in url:
        return False
    try:
        after = url.split("/entertainment/", 1)[1]
        year = after.split("/", 1)[0]
        return year.isdigit() and len(year) == 4
    except Exception:
        return False


def _first_img_from_element(el) -> str | None:
    """Try src, then data-src, then srcset first URL from an element subtree."""
    try:
        if el is None:
            return None
        for img in el.query_selector_all("img"):
            for attr in ("src", "data-src", "data-lazy-src", "data-original"):
                raw = clean_text(img.get_attribute(attr))
                if raw and not raw.startswith("data:"):
                    return raw
            for attr in ("data-srcset", "srcset"):
                ss = clean_text(img.get_attribute(attr))
                if ss:
                    part = ss.split(",")[0].strip().split()[0]
                    return part
        for src in el.query_selector_all("picture source"):
            ss = clean_text(src.get_attribute("srcset") or src.get_attribute("src"))
            if ss:
                return ss.split(",")[0].strip().split()[0]
    except Exception:
        pass
    return None


def _resolve_media_url(raw: str | None) -> str | None:
    """Normalize lazy/protocol-relative image URLs to absolute http(s)."""
    u = clean_text(raw or "")
    if not u or u.startswith("data:"):
        return None
    if u.startswith("//"):
        u = "https:" + u
    return make_absolute_url(u)


def _guess_category_from_card(card) -> str | None:
    """Try common Kantipur listing labels (बलिउड, हलिउड, etc.)."""
    try:
        if card is None:
            return None
        # SELECTOR NEEDED: refine after DevTools — generic hooks
        for sel in (
            "[class*='category']",
            "[class*='tag']",
            "[class*='label']",
            "span.type",
            "a[href*='/entertainment/'] ~ span",
        ):
            try:
                node = card.query_selector(sel)
                if node:
                    t = clean_text(node.inner_text())
                    if t and len(t) < 40:
                        return t
            except Exception:
                continue
        txt = clean_text(card.inner_text())
        if txt:
            for tag in ("बलिउड", "हलिउड", "मनोरञ्जन"):
                if tag in txt:
                    return tag
    except Exception:
        pass
    return None


def _guess_author_from_card(card) -> str | None:
    try:
        if card is None:
            return None
        for sel in (
            "[class*='author']",
            "[class*='byline']",
            "[class*='writer']",
            "span.author",
            "div.author",
        ):
            try:
                node = card.query_selector(sel)
                if node:
                    t = clean_text(node.inner_text())
                    if t and 2 < len(t) < 120:
                        return t
            except Exception:
                continue
    except Exception:
        pass
    return None


def _title_from_card(card, link) -> str | None:
    try:
        for tag in ("h1", "h2", "h3", "h4"):
            try:
                h = card.query_selector(tag) if card else None
                if h:
                    t = clean_text(h.inner_text())
                    if t:
                        return t
            except Exception:
                continue
        if link:
            t = clean_text(link.inner_text())
            if t and t != "...":
                return t
    except Exception:
        pass
    return None


# SECTION 4: MAIN EXTRACTION FUNCTIONS
def extract_entertainment_news(page) -> list:
    """
    Navigate to Entertainment section and extract
    top 5 news articles.

    Returns list of dicts with keys:
    title, image_url, category, author
    """
    # 1. Find and click मनोरञ्जन nav link (fallback: direct URL)
    try:
        page.click("a:has-text('मनोरञ्जन')", timeout=8000)
        time.sleep(2)
    except Exception:
        page.goto(f"{BASE_URL}/entertainment")
        time.sleep(2)

    # 2. Wait for page load
    page.wait_for_load_state("networkidle")
    try:
        # SELECTOR NEEDED: replace after DevTools inspection — broad fallbacks
        page.wait_for_selector(
            "article, .news-card, [class*='news-card'], [class*='story-card'], main",
            timeout=10000,
        )
    except Exception:
        page.wait_for_selector("body", timeout=10000)

    # 3. Scroll page to trigger lazy loading
    page.evaluate("window.scrollTo(0, 500)")
    time.sleep(1)

    # Collect distinct article links (dated paths under /entertainment/)
    links = page.query_selector_all("a[href*='/entertainment/']")
    ordered = []
    seen = set()
    for link in links:
        try:
            href = link.get_attribute("href")
            abs_u = make_absolute_url(href or "")
            if not abs_u or abs_u in seen:
                continue
            if not _is_dated_entertainment_article_url(abs_u):
                continue
            seen.add(abs_u)
            ordered.append(link)
            if len(ordered) >= ENTERTAINMENT_ARTICLES_COUNT:
                break
        except Exception:
            continue

    # If still short, relax scroll and retry once
    if len(ordered) < ENTERTAINMENT_ARTICLES_COUNT:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        for link in page.query_selector_all("a[href*='/entertainment/']"):
            try:
                href = link.get_attribute("href")
                abs_u = make_absolute_url(href or "")
                if not abs_u or abs_u in seen:
                    continue
                if not _is_dated_entertainment_article_url(abs_u):
                    continue
                seen.add(abs_u)
                ordered.append(link)
                if len(ordered) >= ENTERTAINMENT_ARTICLES_COUNT:
                    break
            except Exception:
                continue

    # Prefer Kantipur listing rows (live site uses div.category-inner-wrapper, not <article>)
    articles_out: list = []
    card_locator = page.locator("div.category-inner-wrapper").filter(
        has=page.locator("a[href*='/entertainment/']"),
    )
    try:
        n_cards = card_locator.count()
    except Exception:
        n_cards = 0

    used_hrefs: set[str] = set()

    for i in range(min(n_cards, ENTERTAINMENT_ARTICLES_COUNT * 3)):
        if len(articles_out) >= ENTERTAINMENT_ARTICLES_COUNT:
            break
        title = None
        image_url = None
        category = None
        author = None
        try:
            card_l = card_locator.nth(i)
            link_l = card_l.locator("a[href*='/entertainment/']").first
            if link_l.count() == 0:
                continue
            href = link_l.get_attribute("href")
            abs_h = make_absolute_url(href or "")
            if not abs_h or abs_h in used_hrefs:
                continue
            if not _is_dated_entertainment_article_url(abs_h):
                continue
            used_hrefs.add(abs_h)

            card_el = card_l.element_handle()
            link_el = link_l.element_handle()

            try:
                title = _title_from_card(card_el, link_el)
            except Exception:
                title = None

            try:
                raw_img = None
                try:
                    imloc = card_l.locator(".category-image img, figure img").first
                    if imloc.count():
                        raw_img = clean_text(imloc.get_attribute("src")) or clean_text(
                            imloc.get_attribute("data-src")
                        )
                except Exception:
                    raw_img = None
                if not raw_img:
                    raw_img = _first_img_from_element(card_el)
                if not raw_img and link_el:
                    raw_img = _first_img_from_element(link_el)
                image_url = _resolve_media_url(raw_img)
            except Exception:
                image_url = None

            try:
                category = clean_text(_guess_category_from_card(card_el)) or "मनोरञ्जन"
            except Exception:
                category = "मनोरञ्जन"

            try:
                author = _guess_author_from_card(card_el)
            except Exception:
                author = None

            articles_out.append(
                {
                    "title": title,
                    "image_url": image_url,
                    "category": category,
                    "author": author,
                }
            )

            preview = (
                (title[:30] + "...")
                if title and len(title) > 30
                else (title or "?")
            )
            print(f"  Article {len(articles_out)}: {preview}")
        except Exception:
            continue

    # Fallback: link-only walk if cards did not yield enough items
    if len(articles_out) < ENTERTAINMENT_ARTICLES_COUNT:
        for link in ordered:
            if len(articles_out) >= ENTERTAINMENT_ARTICLES_COUNT:
                break
            href = link.get_attribute("href")
            abs_h = make_absolute_url(href or "")
            if not abs_h or abs_h in used_hrefs:
                continue
            if not _is_dated_entertainment_article_url(abs_h):
                continue
            used_hrefs.add(abs_h)

            idx = len(articles_out)
            title = None
            image_url = None
            category = None
            author = None
            try:
                try:
                    jh = link.evaluate_handle(
                        "el => el.closest('article') || el.closest('[class*=\"card\"]') || el.closest('div')"
                    )
                    card_el = jh.as_element()
                except Exception:
                    card_el = None

                try:
                    title = _title_from_card(card_el, link)
                except Exception:
                    title = None

                try:
                    raw_img = _first_img_from_element(card_el) or _first_img_from_element(link)
                    image_url = _resolve_media_url(raw_img)
                except Exception:
                    image_url = None

                try:
                    category = clean_text(_guess_category_from_card(card_el)) or "मनोरञ्जन"
                except Exception:
                    category = "मनोरञ्जन"

                try:
                    author = _guess_author_from_card(card_el)
                except Exception:
                    author = None

                articles_out.append(
                    {
                        "title": title,
                        "image_url": image_url,
                        "category": category,
                        "author": author,
                    }
                )

                preview = (
                    (title[:30] + "...")
                    if title and len(title) > 30
                    else (title or "?")
                )
                print(f"  Article {idx + 1}: {preview}")
            except Exception:
                articles_out.append(
                    {
                        "title": None,
                        "image_url": None,
                        "category": "मनोरञ्जन",
                        "author": None,
                    }
                )
                print(f"  Article {idx + 1}: ?")

    return articles_out[:ENTERTAINMENT_ARTICLES_COUNT]


def extract_cartoon(page) -> dict:
    """
    Find and extract Cartoon of the Day section.

    Returns dict with keys:
    title, image_url, author
    """
    cartoon: dict = {"title": None, "image_url": None, "author": None}

    # 1. Go back to homepage
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # 2. Scroll down to find cartoon section (lazy panels)
    page.evaluate("window.scrollTo(0, 1000)")
    time.sleep(1)
    page.evaluate("window.scrollTo(0, 2000)")
    time.sleep(1)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    # 3–4. कार्टुन block: section-news + swiper (lazy images use data-src)
    try:
        data = page.evaluate(
            """() => {
              const heading = [...document.querySelectorAll('h4 a, h3 a')].find((a) => {
                const t = (a.innerText || '').trim();
                return t === 'कार्टुन' && (a.href || '').includes('/cartoon');
              });
              const root = heading && heading.closest('.section-news');
              if (!root) return null;

              const slider = root.querySelector('.cartoon-slider');
              let img = null;
              if (slider) {
                const active = slider.querySelector('.swiper-slide-active img');
                img = active || slider.querySelector('img[data-src], img[src]');
              }
              img = img || root.querySelector('img[data-src], img[src]');

              const raw =
                (img && (img.getAttribute('src') || img.getAttribute('data-src') || img.getAttribute('data-lazy-src'))) || '';

              let title =
                (img && img.getAttribute('alt') && img.getAttribute('alt').trim()) ||
                (heading && heading.innerText.trim()) ||
                'कार्टुन';

              let author = null;
              const by = root.querySelector("[class*='author'],[class*='cartoonist'],[class*='byline']");
              if (by && by.innerText && by.innerText.trim()) author = by.innerText.trim();

              return { title, rawSrc: raw, author };
            }"""
        )
    except Exception:
        data = None

    try:
        if isinstance(data, dict):
            cartoon["title"] = clean_text(data.get("title")) or "कार्टुन"
            cartoon["image_url"] = _resolve_media_url(data.get("rawSrc"))
            cartoon["author"] = clean_text(data.get("author"))

        if not cartoon.get("image_url"):
            try:
                el = page.query_selector(".cartoon-slider img[data-src], .cartoon-slider img[src]")
                if el:
                    cartoon["image_url"] = _resolve_media_url(
                        clean_text(el.get_attribute("src"))
                        or clean_text(el.get_attribute("data-src"))
                    )
            except Exception:
                pass

        if not cartoon.get("title"):
            cartoon["title"] = "कार्टुन"

    except Exception:
        pass

    return cartoon


# SECTION 5: OUTPUT FUNCTION
def save_output(data: dict) -> None:
    """
    Save extracted data to output.json.
    Uses ensure_ascii=False for Nepali text.
    """
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to: {OUTPUT_FILE}")


# SECTION 6: VALIDATION FUNCTION
def validate_output(data: dict) -> bool:
    """
    Validate extracted data meets all requirements.
    Returns True if valid, False if not.
    """
    ok = True

    ent = data.get("entertainment_news") or []
    if len(ent) == ENTERTAINMENT_ARTICLES_COUNT:
        print("  [PASS] 5 entertainment articles found")
    else:
        print(f"  [FAIL] Expected {ENTERTAINMENT_ARTICLES_COUNT} entertainment articles, got {len(ent)}")
        ok = False

    req_keys = {"title", "image_url", "category", "author"}
    fields_ok = True
    urls_ok = True
    for idx, a in enumerate(ent):
        if not isinstance(a, dict) or req_keys - set(a.keys()):
            fields_ok = False
            ok = False
            continue
        t = a.get("title")
        iu = a.get("image_url")
        if not t or not clean_text(str(t)):
            fields_ok = False
            ok = False
        if not iu or not str(iu).startswith("http"):
            urls_ok = False
            ok = False

    if fields_ok:
        print("  [PASS] All articles have required fields")
    else:
        print("  [FAIL] All articles have required fields")

    if urls_ok:
        print("  [PASS] All image URLs are absolute")
    else:
        print("  [FAIL] All image URLs are absolute")

    cartoon = data.get("cartoon_of_the_day") or {}
    ckeys = {"title", "image_url", "author"}
    cartoon_ok = isinstance(cartoon, dict) and ckeys <= set(cartoon.keys())
    ci = cartoon.get("image_url")
    cartoon_http = bool(ci and str(ci).startswith("http"))

    if cartoon_ok and cartoon_http:
        print("  [PASS] Cartoon data complete")
    else:
        print("  [FAIL] Cartoon data complete")
        ok = False

    # Readable Nepali: ensure_ascii=False keeps Devanagari in JSON (no \\uXXXX for those chars)
    try:
        raw = json.dumps(data, ensure_ascii=False)
        nepali_ok = any("\u0900" <= ch <= "\u097f" for ch in raw)
        if nepali_ok:
            print("  [PASS] Nepali text readable")
        else:
            print("  [FAIL] Nepali text readable")
            ok = False
    except Exception:
        print("  [FAIL] Nepali text readable")
        ok = False

    return ok


# SECTION 7: MAIN FUNCTION
def main():
    """
    Main entry point. Launches browser, runs extraction,
    saves and validates output.
    """
    print("=" * 50)
    print("AUDIO BEE - EKANTIPUR SCRAPER")
    print("=" * 50)

    with sync_playwright() as p:
        browser = None
        try:
            print("\nLaunching browser...")
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )

            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            )

            page = context.new_page()

            print("\nNavigating to ekantipur.com...")
            page.goto(BASE_URL)
            page.wait_for_load_state("networkidle")
            print("  [PASS] Homepage loaded")

            print("\nExtracting entertainment news...")
            entertainment = extract_entertainment_news(page)
            print(f"  [PASS] Extracted {len(entertainment)} articles")

            print("\nExtracting cartoon of the day...")
            cartoon = extract_cartoon(page)
            ct = cartoon.get("title") or "No title"
            preview = ct[:30] + ("..." if len(ct) > 30 else "")
            print(f"  [PASS] Cartoon extracted: {preview}")

            data = {
                "entertainment_news": entertainment,
                "cartoon_of_the_day": cartoon,
            }

            print("\nSaving output.json...")
            save_output(data)

            print("\nValidating output...")
            is_valid = validate_output(data)

            if is_valid:
                print("\n[PASS] ALL CHECKS PASSED - READY TO SUBMIT")
            else:
                print("\n[FAIL] VALIDATION FAILED - FIX ERRORS ABOVE")

            return data

        except Exception as e:
            print(f"\n[FAIL] SCRAPER FAILED: {e}")
            raise

        finally:
            if browser:
                browser.close()
                print("\nBrowser closed")


if __name__ == "__main__":
    main()
