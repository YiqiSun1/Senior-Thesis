"""
CEO Photo Scraper for S&P 500 Companies
========================================
Scrapes CEO headshots from official company leadership/about pages.

Output:
    - ./ceo_photos/          → downloaded image files
    - ./ceo_photos/index.csv → metadata (ticker, company, ceo_name, image_path, source_url, status)

Usage:
    python ceo_photo_scraper.py                        # scrape all S&P 500
    python ceo_photo_scraper.py --tickers AAPL MSFT    # specific tickers
    python ceo_photo_scraper.py --limit 20             # first N companies
    python ceo_photo_scraper.py --output ./my_dir      # custom output dir
    python ceo_photo_scraper.py --resume               # skip already-downloaded

Requirements:
    pip install requests beautifulsoup4 pandas Pillow
"""

import os
import re
import csv
import time
import random
import logging
import argparse
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image
import pandas as pd

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── S&P 500 company registry ─────────────────────────────────────────────────
# fmt: off
SP500_COMPANIES = [
    # ticker, company,                    official website,                  leadership URL ('' = auto-discover)
    ("AAPL",  "Apple",                    "https://www.apple.com",           "https://www.apple.com/leadership/tim-cook/"),
    ("MSFT",  "Microsoft",               "https://www.microsoft.com",       "https://news.microsoft.com/source/leadership/"),
    ("NVDA",  "NVIDIA",                  "https://www.nvidia.com",           "https://nvidianews.nvidia.com/bios"),
    ("AMZN",  "Amazon",                  "https://www.amazon.com",           "https://ir.aboutamazon.com/officers-and-directors/default.aspx"),
    ("META",  "Meta",                    "https://about.meta.com",           "https://about.meta.com/company-info/"),
    ("GOOGL", "Alphabet",               "https://abc.xyz",                  "https://abc.xyz/investor/other/management-team/"),
    ("BRK.B", "Berkshire Hathaway",      "https://www.berkshirehathaway.com","https://www.berkshirehathaway.com/govern/govern.html"),
    ("LLY",   "Eli Lilly",              "https://www.lilly.com",            "https://www.lilly.com/about/leadership"),
    ("AVGO",  "Broadcom",               "https://www.broadcom.com",         "https://www.broadcom.com/company/about-us/executive-profiles"),
    ("TSLA",  "Tesla",                  "https://www.tesla.com",            "https://ir.tesla.com/corporate-governance/directors-and-leadership"),
    ("JPM",   "JPMorgan Chase",         "https://www.jpmorganchase.com",    "https://www.jpmorganchase.com/about/our-leadership"),
    ("WMT",   "Walmart",               "https://www.walmart.com",          "https://corporate.walmart.com/about/leadership"),
    ("UNH",   "UnitedHealth Group",     "https://www.unitedhealthgroup.com","https://www.unitedhealthgroup.com/who-we-are/leadership.html"),
    ("V",     "Visa",                  "https://www.visa.com",             "https://investor.visa.com/corporate-governance/board-of-directors/default.aspx"),
    ("XOM",   "ExxonMobil",            "https://corporate.exxonmobil.com", "https://corporate.exxonmobil.com/about-us/leadership"),
    ("ORCL",  "Oracle",               "https://www.oracle.com",           "https://www.oracle.com/corporate/executives.html"),
    ("MA",    "Mastercard",           "https://www.mastercard.us",        "https://investor.mastercard.com/governance/board-of-directors/default.aspx"),
    ("COST",  "Costco",              "https://www.costco.com",           "https://ir.costco.com/governance/board-of-directors/default.aspx"),
    ("HD",    "Home Depot",          "https://www.homedepot.com",        "https://ir.homedepot.com/corporate-governance/board-of-directors"),
    ("PG",    "Procter & Gamble",    "https://us.pg.com",                "https://us.pg.com/leadership/"),
    ("JNJ",   "Johnson & Johnson",   "https://www.jnj.com",              "https://www.jnj.com/latest-news/leadership"),
    ("BAC",   "Bank of America",     "https://www.bankofamerica.com",    "https://investor.bankofamerica.com/corporate-governance/board-of-directors"),
    ("ABBV",  "AbbVie",             "https://www.abbvie.com",           "https://www.abbvie.com/who-we-are/leadership.html"),
    ("CVX",   "Chevron",            "https://www.chevron.com",          "https://www.chevron.com/about/leadership"),
    ("MRK",   "Merck",             "https://www.merck.com",            "https://www.merck.com/company-overview/leadership/"),
    ("KO",    "Coca-Cola",         "https://www.coca-colacompany.com", "https://www.coca-colacompany.com/about-us/leadership"),
    ("PEP",   "PepsiCo",          "https://www.pepsico.com",          "https://www.pepsico.com/about/leadership"),
    ("AMD",   "AMD",              "https://www.amd.com",              "https://ir.amd.com/corporate-governance/directors-and-officers"),
    ("NFLX",  "Netflix",         "https://www.netflix.com",          "https://ir.netflix.net/governance/executive-officers/default.aspx"),
    ("CRM",   "Salesforce",      "https://www.salesforce.com",       "https://www.salesforce.com/company/leadership/"),
    ("INTC",  "Intel",          "https://www.intel.com",            "https://www.intel.com/content/www/us/en/corporate/biographies.html"),
    ("IBM",   "IBM",            "https://www.ibm.com",              "https://www.ibm.com/investor/governance/executive-leadership"),
    ("GE",    "GE Aerospace",  "https://www.ge.com",               "https://www.ge.com/about-us/leadership"),
    ("CAT",   "Caterpillar",   "https://www.caterpillar.com",      "https://www.caterpillar.com/en/company/leadership.html"),
    ("GS",    "Goldman Sachs", "https://www.goldmansachs.com",     "https://www.goldmansachs.com/our-firm/leadership/"),
    ("BKNG",  "Booking Holdings","https://www.bookingholdings.com","https://ir.bookingholdings.com/governance/executive-officers/default.aspx"),
    ("AXP",   "American Express","https://www.americanexpress.com","https://ir.americanexpress.com/corporate-governance/executive-officers"),
    ("T",     "AT&T",          "https://www.att.com",              "https://about.att.com/category/leadership"),
    ("CMCSA", "Comcast",       "https://corporate.comcast.com",    "https://corporate.comcast.com/company/leadership"),
    ("VZ",    "Verizon",       "https://www.verizon.com",          "https://www.verizon.com/about/investors/corporate-governance/board-directors"),
    ("WFC",   "Wells Fargo",   "https://www.wellsfargo.com",       "https://www.wellsfargo.com/about/corporate/governance/directors/"),
    ("PM",    "Philip Morris", "https://www.pmi.com",              "https://www.pmi.com/who-we-are/our-leadership"),
    ("RTX",   "RTX Corp",     "https://www.rtx.com",              "https://www.rtx.com/who-we-are/leadership"),
    ("SPGI",  "S&P Global",   "https://www.spglobal.com",         "https://investor.spglobal.com/governance/board-of-directors/default.aspx"),
    ("DE",    "Deere & Co",   "https://www.deere.com",            "https://www.deere.com/en/our-company/leadership/"),
    ("INTU",  "Intuit",       "https://www.intuit.com",           "https://www.intuit.com/company/executives/"),
    ("MS",    "Morgan Stanley","https://www.morganstanley.com",   "https://www.morganstanley.com/about-us/leadership"),
    ("HON",   "Honeywell",    "https://www.honeywell.com",        "https://www.honeywell.com/us/en/company/about/leadership"),
    ("UPS",   "UPS",          "https://www.ups.com",              "https://ir.ups.com/corporate-governance/board-of-directors/default.aspx"),
    ("ISRG",  "Intuitive Surgical","https://www.intuitive.com",   "https://www.intuitive.com/en-us/about-us/company/leadership"),
    ("SYK",   "Stryker",      "https://www.stryker.com",          "https://www.stryker.com/us/en/about/leadership.html"),
]
# fmt: on

# ── Heuristics to find CEO photos ─────────────────────────────────────────────
CEO_KEYWORDS = [
    "chief executive", "ceo", "president and ceo", "executive officer"
]

IMG_EXCLUDE_PATTERNS = re.compile(
    r"(logo|icon|sprite|banner|bg|background|footer|header|arrow|chevron"
    r"|button|social|linkedin|twitter|facebook|flag|map|placeholder"
    r"|1x1|blank|spacer|pixel|loading)",
    re.IGNORECASE,
)

IMG_INCLUDE_PATTERNS = re.compile(
    r"(headshot|portrait|photo|profile|executive|leader|bio|person|"
    r"team|people|officer|director|management)",
    re.IGNORECASE,
)

MIN_IMAGE_BYTES = 8_000    # skip tiny decorative images
MIN_DIM = 80               # minimum pixel dimension (width or height)


# ── HTTP helpers ──────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch_html(url: str, timeout: int = 15) -> BeautifulSoup | None:
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    try:
        resp = SESSION.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        log.debug("fetch_html %s → %s", url, e)
        return None


def download_image(url: str, dest: Path, timeout: int = 15) -> bool:
    """Download an image to dest. Returns True on success."""
    try:
        resp = SESSION.get(url, timeout=timeout, stream=True)
        resp.raise_for_status()
        content = resp.content
        if len(content) < MIN_IMAGE_BYTES:
            return False
        dest.write_bytes(content)
        # Validate it's a real image and meets minimum dimensions
        with Image.open(dest) as img:
            w, h = img.size
            if w < MIN_DIM or h < MIN_DIM:
                dest.unlink(missing_ok=True)
                return False
        return True
    except Exception as e:
        log.debug("download_image %s → %s", url, e)
        dest.unlink(missing_ok=True)
        return False


# ── CEO detection ─────────────────────────────────────────────────────────────

def score_element_as_ceo(element) -> int:
    """Heuristic score: higher = more likely this is the CEO's element."""
    text = element.get_text(" ", strip=True).lower()
    score = 0
    for kw in CEO_KEYWORDS:
        if kw in text:
            score += 10
    # Prefer shorter blocks (bio cards, not full pages)
    if len(text) < 500:
        score += 3
    return score


def find_ceo_images(soup: BeautifulSoup, base_url: str) -> list[str]:
    """
    Strategy:
    1. Look for elements whose text contains CEO keywords, then grab nearby <img>.
    2. Fallback: score all images by URL heuristics.
    Returns a ranked list of absolute image URLs.
    """
    candidates: list[tuple[int, str]] = []

    # -- Strategy 1: text proximity ----------------------------------------
    for tag in soup.find_all(["section", "div", "article", "li", "figure"]):
        score = score_element_as_ceo(tag)
        if score == 0:
            continue
        for img in tag.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if not src:
                continue
            abs_src = urljoin(base_url, src)
            if IMG_EXCLUDE_PATTERNS.search(abs_src):
                continue
            alt = (img.get("alt") or "").lower()
            img_score = score
            if any(kw in alt for kw in CEO_KEYWORDS):
                img_score += 15
            if IMG_INCLUDE_PATTERNS.search(abs_src) or IMG_INCLUDE_PATTERNS.search(alt):
                img_score += 5
            candidates.append((img_score, abs_src))

    # -- Strategy 2: fallback — all images scored by URL --------------------
    if not candidates:
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if not src:
                continue
            abs_src = urljoin(base_url, src)
            if IMG_EXCLUDE_PATTERNS.search(abs_src):
                continue
            alt = (img.get("alt") or "").lower()
            img_score = 0
            if any(kw in alt for kw in CEO_KEYWORDS):
                img_score += 20
            if IMG_INCLUDE_PATTERNS.search(abs_src):
                img_score += 5
            if img_score > 0:
                candidates.append((img_score, abs_src))

    # De-duplicate while preserving rank order
    seen = set()
    result = []
    for score, url in sorted(candidates, reverse=True):
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def auto_discover_leadership_url(base_url: str) -> str | None:
    """Try common URL patterns when no leadership URL is provided."""
    patterns = [
        "/about/leadership", "/about-us/leadership", "/leadership",
        "/company/leadership", "/who-we-are/leadership",
        "/investor-relations/governance", "/corporate/leadership",
    ]
    soup = fetch_html(base_url)
    if soup:
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            text = a.get_text().lower()
            if any(kw in href or kw in text for kw in ["leadership", "executives", "management", "our-team"]):
                return urljoin(base_url, a["href"])
    for p in patterns:
        url = base_url.rstrip("/") + p
        try:
            r = SESSION.head(url, timeout=8, allow_redirects=True)
            if r.status_code == 200:
                return url
        except Exception:
            pass
    return None


# ── Per-company scrape ────────────────────────────────────────────────────────

def scrape_company(
    ticker: str,
    company: str,
    website: str,
    leadership_url: str,
    output_dir: Path,
    resume: bool,
) -> dict:
    """Scrape one company. Returns a metadata dict."""
    result = {
        "ticker": ticker,
        "company": company,
        "ceo_name": "",
        "image_path": "",
        "source_url": leadership_url or website,
        "status": "pending",
    }

    # Derive safe filename prefix
    safe = re.sub(r"[^\w]", "_", ticker.lower())
    dest_path = output_dir / f"{safe}_ceo.jpg"

    if resume and dest_path.exists():
        log.info("  [SKIP] %s — already downloaded", ticker)
        result.update(status="cached", image_path=str(dest_path))
        return result

    # Resolve leadership URL
    url = leadership_url or auto_discover_leadership_url(website)
    if not url:
        log.warning("  [FAIL] %s — could not find leadership URL", ticker)
        result["status"] = "no_url"
        return result

    result["source_url"] = url
    soup = fetch_html(url)
    if soup is None:
        log.warning("  [FAIL] %s — fetch failed: %s", ticker, url)
        result["status"] = "fetch_error"
        return result

    # Try to extract CEO name from page text
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "span", "div"]):
        text = tag.get_text(" ", strip=True)
        if any(kw in text.lower() for kw in CEO_KEYWORDS):
            # Grab the nearest heading-like sibling or parent text
            name_tag = tag.find_previous(["h1", "h2", "h3", "h4"])
            if name_tag and len(name_tag.get_text(strip=True)) < 60:
                result["ceo_name"] = name_tag.get_text(" ", strip=True)
                break

    # Find candidate image URLs
    img_urls = find_ceo_images(soup, url)

    for img_url in img_urls[:5]:   # try up to 5 candidates
        if download_image(img_url, dest_path):
            log.info("  [OK]   %s → %s", ticker, dest_path.name)
            result.update(status="ok", image_path=str(dest_path))
            return result

    log.warning("  [FAIL] %s — no suitable image found", ticker)
    result["status"] = "no_image"
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def run(
    tickers: list[str] | None = None,
    limit: int | None = None,
    output_dir: str = "./ceo_photos",
    resume: bool = False,
    delay_range: tuple[float, float] = (1.5, 3.5),
) -> pd.DataFrame:
    """
    Run the scraper.

    Parameters
    ----------
    tickers      : list of ticker symbols to scrape (None = all S&P 500)
    limit        : cap on number of companies to process
    output_dir   : folder for images + CSV index
    resume       : skip tickers whose image already exists
    delay_range  : (min, max) seconds to sleep between requests

    Returns
    -------
    pd.DataFrame with columns:
        ticker, company, ceo_name, image_path, source_url, status
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Filter company list
    companies = SP500_COMPANIES
    if tickers:
        tickers_up = {t.upper() for t in tickers}
        companies = [c for c in companies if c[0].upper() in tickers_up]
    if limit:
        companies = companies[:limit]

    log.info("Scraping %d companies → %s", len(companies), out.resolve())

    results = []
    for i, (ticker, company, website, leadership_url) in enumerate(companies, 1):
        log.info("[%d/%d] %s — %s", i, len(companies), ticker, company)
        row = scrape_company(ticker, company, website, leadership_url, out, resume)
        results.append(row)

        # Write incremental CSV after each company
        df = pd.DataFrame(results)
        df.to_csv(out / "index.csv", index=False)

        # Polite delay
        if i < len(companies):
            time.sleep(random.uniform(*delay_range))

    df = pd.DataFrame(results)
    df.to_csv(out / "index.csv", index=False)

    ok = (df["status"] == "ok").sum()
    cached = (df["status"] == "cached").sum()
    log.info("Done. %d downloaded, %d cached, %d failed", ok, cached, len(df) - ok - cached)
    return df


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape CEO headshots from S&P 500 official websites."
    )
    parser.add_argument(
        "--tickers", nargs="+", metavar="TICKER",
        help="Specific ticker symbols (e.g. AAPL MSFT). Default: all 50 seeded companies.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Process only the first N companies.",
    )
    parser.add_argument(
        "--output", default="./ceo_photos",
        help="Output directory (default: ./ceo_photos).",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip companies whose image file already exists.",
    )
    parser.add_argument(
        "--delay", type=float, nargs=2, default=[1.5, 3.5], metavar=("MIN", "MAX"),
        help="Random sleep range between requests (default: 1.5 3.5).",
    )
    args = parser.parse_args()

    df = run(
        tickers=args.tickers,
        limit=args.limit,
        output_dir=args.output,
        resume=args.resume,
        delay_range=tuple(args.delay),
    )

    print("\n── Results ──────────────────────────────────────────────")
    print(df[["ticker", "company", "ceo_name", "status", "image_path"]].to_string(index=False))
    print(f"\nIndex CSV: {Path(args.output) / 'index.csv'}")


if __name__ == "__main__":
    main()
