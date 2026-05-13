from playwright.sync_api import sync_playwright
import json
import os

BASE_URL = "https://ekantipur.com"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output.json")

def clean_text(text):
    return text.strip() if text and text.strip() else None

def make_absolute_url(url):
    if not url:
        return None
    url = url.strip()
    if url.startswith("http"):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_URL + url
    return None

def get_image_url(element):
    if not element:
        return None
    try:
        img = element.query_selector("img")
        if img:
            for attr in ("src", "data-src", "data-lazy-src"):
                url = img.get_attribute(attr)
                if url and not url.startswith("data:"):
                    return make_absolute_url(url)
    except:
        pass
    return None

def get_text(element, selector, max_len=None):
    try:
        el = element.query_selector(selector)
        text = clean_text(el.inner_text()) if el else None
        if text and max_len and len(text) > max_len:
            return None
        return text
    except:
        return None


def extract_entertainment_news(page):
    try:
        page.click("a:has-text('मनोरञ्जन')", timeout=8000)
    except:
        page.goto(f"{BASE_URL}/entertainment")
    
    page.wait_for_load_state("networkidle")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1000)
    
    articles = []
    seen = set()
    
    cards = page.query_selector_all("div.category-inner-wrapper")
    for card in cards:
        if len(articles) >= 5:
            break
        
        try:
            link = card.query_selector("a[href*='/entertainment/']")
            if not link:
                continue
            
            href = make_absolute_url(link.get_attribute("href"))
            if not href or href in seen or "/entertainment/2" not in href:
                continue
            seen.add(href)
            
            title = get_text(card, "h1, h2, h3, h4") or get_text(link, "*")
            image_url = get_image_url(card)
            category = get_text(card, "[class*='category'], [class*='tag'], span.type", max_len=40) or "मनोरञ्जन"
            author = get_text(card, "[class*='author'], [class*='byline']", max_len=100)
            
            articles.append({
                "title": title,
                "image_url": image_url,
                "category": category,
                "author": author
            })
            print(f"  Article {len(articles)}: {title[:30] if title else '?'}...")
        except:
            continue
    
    return articles[:5]


def extract_cartoon(page):
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1500)
    
    try:
        data = page.evaluate("""() => {
            const heading = [...document.querySelectorAll('h4 a, h3 a')].find(a => 
                a.innerText.trim() === 'कार्टुन' && a.href.includes('/cartoon')
            );
            const root = heading?.closest('.section-news');
            if (!root) return null;
            
            const img = root.querySelector('.cartoon-slider img[data-src], .cartoon-slider img[src]') ||
                        root.querySelector('img[data-src], img[src]');
            
            return {
                title: img?.alt?.trim() || heading?.innerText.trim() || 'कार्टुन',
                rawSrc: img?.getAttribute('src') || img?.getAttribute('data-src') || '',
                author: root.querySelector("[class*='author']")?.innerText.trim() || null
            };
        }""")
        
        return {
            "title": clean_text(data.get("title")) or "कार्टुन",
            "image_url": make_absolute_url(data.get("rawSrc")),
            "author": clean_text(data.get("author"))
        }
    except:
        return {"title": "कार्टुन", "image_url": None, "author": None}


def validate_output(data):
    ok = True
    ent = data.get("entertainment_news", [])
    
    if len(ent) == 5:
        print("  [PASS] 5 entertainment articles found")
    else:
        print(f"  [FAIL] Expected 5 entertainment articles, got {len(ent)}")
        ok = False
    
    for i, a in enumerate(ent):
        if not isinstance(a, dict) or not all(k in a for k in ["title", "image_url", "category", "author"]):
            print(f"  [FAIL] Article {i} missing required fields")
            ok = False
        elif not a.get("title") or not str(a.get("image_url", "")).startswith("http"):
            print(f"  [FAIL] Article {i} has invalid title or image_url")
            ok = False
    
    if ok and ent:
        print("  [PASS] All articles have required fields")
        print("  [PASS] All image URLs are absolute")
    
    cartoon = data.get("cartoon_of_the_day", {})
    if all(k in cartoon for k in ["title", "image_url", "author"]) and \
       str(cartoon.get("image_url", "")).startswith("http"):
        print("  [PASS] Cartoon data complete")
    else:
        print("  [FAIL] Cartoon data complete")
        ok = False
    
    if any("\u0900" <= ch <= "\u097f" for ch in json.dumps(data, ensure_ascii=False)):
        print("  [PASS] Nepali text readable")
    else:
        print("  [FAIL] Nepali text readable")
        ok = False
    
    return ok

def main():
    print("=" * 50)
    print("AUDIO BEE - EKANTIPUR SCRAPER")
    print("=" * 50)
    
    with sync_playwright() as p:
        browser = None
        try:
            print("\nLaunching browser...")
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            page = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            ).new_page()
            
            print("\nNavigating to ekantipur.com...")
            page.goto(BASE_URL)
            page.wait_for_load_state("networkidle")
            print("  [PASS] Homepage loaded")
            
            print("\nExtracting entertainment news...")
            entertainment = extract_entertainment_news(page)
            print(f"  [PASS] Extracted {len(entertainment)} articles")
            
            print("\nExtracting cartoon of the day...")
            cartoon = extract_cartoon(page)
            print(f"  [PASS] Cartoon extracted: {cartoon.get('title', '?')[:30]}...")
            
            data = {
                "entertainment_news": entertainment,
                "cartoon_of_the_day": cartoon
            }
            
            print("\nSaving output.json...")
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved to: {OUTPUT_FILE}")
            
            print("\nValidating output...")
            is_valid = validate_output(data)
            
            print("\n[PASS] ALL CHECKS PASSED - READY TO SUBMIT" if is_valid else "\n[FAIL] VALIDATION FAILED - FIX ERRORS ABOVE")
            
        except Exception as e:
            print(f"\n[FAIL] SCRAPER FAILED: {e}")
            raise
        finally:
            if browser:
                browser.close()
                print("\nBrowser closed")

if __name__ == "__main__":
    main()
