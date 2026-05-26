"""
CEO Photo Scraper — Scalable Edition (Wikidata + Wikipedia)
============================================================
Fetches CEO names and headshots for S&P 500 companies using:
  1. Wikidata SPARQL  → CEO name + Wikimedia image URL
  2. Wikipedia API    → fallback image if Wikidata has none
  3. Google CSE       → last-resort fallback (optional, requires API key)

Output:
    - ./ceo_photos/<ticker>_ceo.jpg
    - ./ceo_photos/index.csv   (ticker, company, ceo_name, image_path, source, status)

Install:
    pip install requests pandas Pillow SPARQLWrapper

Usage:
    python ceo_photo_scraper.py                        # all companies
    python ceo_photo_scraper.py --tickers AAPL MSFT    # specific tickers
    python ceo_photo_scraper.py --limit 20             # first N companies
    python ceo_photo_scraper.py --resume               # skip already done
    python ceo_photo_scraper.py --google-key KEY --google-cx CX  # enable Google fallback
"""

import re
import time
import random
import logging
import argparse
from pathlib import Path

import requests
import pandas as pd
from PIL import Image
from SPARQLWrapper import SPARQLWrapper, JSON

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── S&P 500 company list with Wikidata QIDs ───────────────────────────────────
# QID = Wikidata entity ID for each company (stable, never changes)
# Find any company QID at: https://www.wikidata.org/wiki/Special:Search
SP500_COMPANIES = [
    # ticker,  company name,            Wikidata QID
    ("AAPL",  "Apple",                  "Q312"),
    ("MSFT",  "Microsoft",              "Q2283"),
    ("NVDA",  "NVIDIA",                 "Q182477"),
    ("AMZN",  "Amazon",                 "Q3884"),
    ("META",  "Meta",                   "Q380"),
    ("GOOGL", "Alphabet",               "Q1326386"),
    ("BRK.B", "Berkshire Hathaway",     "Q217583"),
    ("LLY",   "Eli Lilly",              "Q206921"),
    ("AVGO",  "Broadcom",               "Q4952"),
    ("TSLA",  "Tesla",                  "Q478214"),
    ("JPM",   "JPMorgan Chase",         "Q192314"),
    ("WMT",   "Walmart",               "Q483551"),
    ("UNH",   "UnitedHealth Group",     "Q2103400"),
    ("V",     "Visa",                   "Q653600"),
    ("XOM",   "ExxonMobil",             "Q156238"),
    ("ORCL",  "Oracle",                 "Q4925"),
    ("MA",    "Mastercard",             "Q286675"),
    ("COST",  "Costco",                 "Q715583"),
    ("HD",    "Home Depot",             "Q1090484"),
    ("PG",    "Procter & Gamble",       "Q187"),
    ("JNJ",   "Johnson & Johnson",      "Q193490"),
    ("BAC",   "Bank of America",        "Q487921"),
    ("ABBV",  "AbbVie",                 "Q21084764"),
    ("CVX",   "Chevron",                "Q319642"),
    ("MRK",   "Merck",                  "Q80818"),
    ("KO",    "Coca-Cola",              "Q3295867"),
    ("PEP",   "PepsiCo",               "Q131370"),
    ("AMD",   "AMD",                    "Q165495"),
    ("NFLX",  "Netflix",               "Q907311"),
    ("CRM",   "Salesforce",            "Q811604"),
    ("INTC",  "Intel",                  "Q248"),
    ("IBM",   "IBM",                    "Q37156"),
    ("GE",    "GE Aerospace",           "Q54173"),
    ("CAT",   "Caterpillar",            "Q373723"),
    ("GS",    "Goldman Sachs",          "Q193326"),
    ("BKNG",  "Booking Holdings",       "Q2935738"),
    ("AXP",   "American Express",       "Q49813"),
    ("T",     "AT&T",                   "Q35476"),
    ("CMCSA", "Comcast",                "Q1368900"),
    ("VZ",    "Verizon",                "Q1418819"),
    ("WFC",   "Wells Fargo",            "Q744149"),
    ("PM",    "Philip Morris",          "Q503819"),
    ("RTX",   "RTX Corp",               "Q1132983"),
    ("SPGI",  "S&P Global",             "Q1961888"),
    ("DE",    "Deere & Co",             "Q726848"),
    ("INTU",  "Intuit",                 "Q1094614"),
    ("MS",    "Morgan Stanley",         "Q2626813"),
    ("HON",   "Honeywell",              "Q1067894"),
    ("UPS",   "UPS",                    "Q180938"),
    ("ISRG",  "Intuitive Surgical",     "Q1387160"),
    ("SYK",   "Stryker",                "Q2313726"),
    ("MDLZ",  "Mondelez",               "Q1424498"),
    ("TJX",   "TJX Companies",          "Q2429966"),
    ("BLK",   "BlackRock",              "Q1190547"),
    ("ADI",   "Analog Devices",         "Q429895"),
    ("REGN",  "Regeneron",              "Q1827616"),
    ("VRTX",  "Vertex Pharma",          "Q1871229"),
    ("PANW",  "Palo Alto Networks",     "Q7130903"),
    ("AMAT",  "Applied Materials",      "Q428863"),
    ("MU",    "Micron Technology",      "Q633192"),
    ("NEM",   "Newmont",                "Q913242"),
    ("FCX",   "Freeport-McMoRan",       "Q1441910"),
    ("NUE",   "Nucor",                  "Q2000970"),
    ("ALB",   "Albemarle",              "Q4712048"),
    ("LIN",   "Linde",                  "Q183428"),
    ("APD",   "Air Products",           "Q4692965"),
    ("PPG",   "PPG Industries",         "Q1055072"),
    ("SHW",   "Sherwin-Williams",       "Q756281"),
    ("ECL",   "Ecolab",                 "Q1292779"),
    ("ITW",   "Illinois Tool Works",    "Q1380813"),
    ("EMR",   "Emerson Electric",       "Q1343602"),
    ("GWW",   "W.W. Grainger",          "Q4907457"),
    ("RSG",   "Republic Services",      "Q7314175"),
    ("WM",    "Waste Management",       "Q1413221"),
    ("AWK",   "American Water Works",   "Q4745773"),
]

# ── HTTP session ──────────────────────────────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "CEOPhotoScraper/2.0 (educational research; python-requests)",
    "Accept": "application/json",
})

MIN_IMAGE_BYTES = 8_000
MIN_DIM = 80

# ── Wikidata SPARQL ───────────────────────────────────────────────────────────

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

SPARQL_QUERY = """
SELECT ?ticker ?ceoLabel ?image WHERE {{
  VALUES (?ticker ?company) {{ {values} }}
  ?company wdt:P169 ?ceo .
  OPTIONAL {{ ?ceo wdt:P18 ?image }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
}}
"""

def fetch_wikidata_batch(companies: list) -> dict:
    """
    Query Wikidata for CEO name + image for a batch of companies.
    Returns dict keyed by ticker: { ceo_name, image_url }
    """
    values = " ".join(
        f'("{ticker}" wd:{qid})'
        for ticker, _, qid in companies
    )
    query = SPARQL_QUERY.format(values=values)

    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.addCustomHttpHeader("User-Agent", "CEOPhotoScraper/2.0 (educational research)")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        results = sparql.query().convert()
    except Exception as e:
        log.error("Wikidata SPARQL failed: %s", e)
        return {}

    output = {}
    for row in results["results"]["bindings"]:
        ticker = row.get("ticker", {}).get("value", "")
        ceo    = row.get("ceoLabel", {}).get("value", "")
        image  = row.get("image", {}).get("value", "")
        if ticker:
            output[ticker] = {"ceo_name": ceo, "image_url": image}

    return output


# ── Wikipedia image fallback ──────────────────────────────────────────────────

WIKI_API = "https://en.wikipedia.org/w/api.php"

def fetch_wikipedia_image(ceo_name: str) -> str:
    """Search Wikipedia for the CEO and return their main image URL."""
    try:
        # Step 1: find their Wikipedia page title
        search_resp = SESSION.get(WIKI_API, params={
            "action": "query",
            "list": "search",
            "srsearch": ceo_name + " CEO",
            "srlimit": 1,
            "format": "json",
        }, timeout=10)
        results = search_resp.json().get("query", {}).get("search", [])
        if not results:
            return ""
        title = results[0]["title"]

        # Step 2: get the page thumbnail
        img_resp = SESSION.get(WIKI_API, params={
            "action": "query",
            "titles": title,
            "prop": "pageimages",
            "pithumbsize": 500,
            "format": "json",
        }, timeout=10)
        pages = img_resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = page.get("thumbnail", {}).get("source", "")
            if thumb:
                return thumb
    except Exception as e:
        log.debug("Wikipedia fallback failed for %s: %s", ceo_name, e)
    return ""


# ── Google CSE fallback (optional) ───────────────────────────────────────────

def fetch_google_image(ceo_name: str, company: str, api_key: str, cx: str) -> str:
    """Use Google Custom Search API to find a CEO headshot."""
    try:
        resp = SESSION.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": api_key,
                "cx": cx,
                "q": f"{ceo_name} {company} CEO headshot",
                "searchType": "image",
                "num": 3,
                "imgType": "face",
                "safe": "active",
            },
            timeout=10,
        )
        items = resp.json().get("items", [])
        if items:
            return items[0].get("link", "")
    except Exception as e:
        log.debug("Google CSE failed for %s: %s", ceo_name, e)
    return ""


# ── Image download ────────────────────────────────────────────────────────────

def download_image(url: str, dest: Path) -> bool:
    """Download and validate an image. Returns True on success."""
    try:
        resp = SESSION.get(url, timeout=15, stream=True)
        resp.raise_for_status()
        content = resp.content
        if len(content) < MIN_IMAGE_BYTES:
            return False
        dest.write_bytes(content)
        with Image.open(dest) as img:
            w, h = img.size
            if w < MIN_DIM or h < MIN_DIM:
                dest.unlink(missing_ok=True)
                return False
            # Normalize to JPEG
            if img.format != "JPEG":
                rgb = img.convert("RGB")
                rgb.save(dest, "JPEG", quality=92)
        return True
    except Exception as e:
        log.debug("download_image %s: %s", url, e)
        dest.unlink(missing_ok=True)
        return False


# ── Main scrape loop ──────────────────────────────────────────────────────────

def run(
    tickers=None,
    limit=None,
    output_dir="./ceo_photos",
    resume=False,
    google_key="",
    google_cx="",
    batch_size=20,
    delay_range=(0.5, 1.5),
):
    """
    Run the CEO photo scraper.

    Parameters
    ----------
    tickers      : list of ticker strings, or None for all
    limit        : max number of companies to process
    output_dir   : folder where images + index.csv are saved
    resume       : if True, skip tickers already downloaded
    google_key   : Google Custom Search API key (optional)
    google_cx    : Google Custom Search engine ID (optional)
    batch_size   : how many companies per Wikidata SPARQL request
    delay_range  : (min, max) seconds to sleep between requests

    Returns
    -------
    pd.DataFrame  columns: ticker, company, ceo_name, image_path, source, status
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    companies = SP500_COMPANIES
    if tickers:
        tickers_up = {t.upper() for t in tickers}
        companies = [c for c in companies if c[0].upper() in tickers_up]
    if limit:
        companies = companies[:limit]

    log.info("Processing %d companies → %s", len(companies), out.resolve())

    # ── Step 1: batch-fetch from Wikidata ─────────────────────────────────────
    log.info("Querying Wikidata (batches of %d)...", batch_size)
    wikidata = {}
    for i in range(0, len(companies), batch_size):
        batch = companies[i : i + batch_size]
        log.info("  Wikidata batch %d/%d", i // batch_size + 1,
                 -(-len(companies) // batch_size))
        wikidata.update(fetch_wikidata_batch(batch))
        time.sleep(1.0)

    # ── Step 2: download images with fallback chain ───────────────────────────
    results = []
    for idx, (ticker, company, qid) in enumerate(companies, 1):
        log.info("[%d/%d] %s — %s", idx, len(companies), ticker, company)

        safe = re.sub(r"[^\w]", "_", ticker.lower())
        dest = out / f"{safe}_ceo.jpg"

        row = dict(ticker=ticker, company=company, ceo_name="",
                   image_path="", source="", status="pending")

        if resume and dest.exists():
            log.info("  [SKIP] already downloaded")
            wd = wikidata.get(ticker, {})
            row.update(ceo_name=wd.get("ceo_name", ""),
                       image_path=str(dest), source="cached", status="cached")
            results.append(row)
            continue

        wd        = wikidata.get(ticker, {})
        ceo_name  = wd.get("ceo_name", "")
        image_url = wd.get("image_url", "")
        row["ceo_name"] = ceo_name

        # 1) Wikidata image
        if image_url and download_image(image_url, dest):
            log.info("  [OK-WD]  %s", ceo_name)
            row.update(image_path=str(dest), source="wikidata", status="ok")
            results.append(row)
            pd.DataFrame(results).to_csv(out / "index.csv", index=False)
            time.sleep(random.uniform(*delay_range))
            continue

        # 2) Wikipedia image
        if ceo_name:
            log.info("  [WP]    Wikipedia fallback for '%s'...", ceo_name)
            wp_url = fetch_wikipedia_image(ceo_name)
            if wp_url and download_image(wp_url, dest):
                log.info("  [OK-WP]  %s", ceo_name)
                row.update(image_path=str(dest), source="wikipedia", status="ok")
                results.append(row)
                pd.DataFrame(results).to_csv(out / "index.csv", index=False)
                time.sleep(random.uniform(*delay_range))
                continue

        # 3) Google CSE image (optional)
        if google_key and google_cx and ceo_name:
            log.info("  [GG]    Google CSE fallback for '%s'...", ceo_name)
            g_url = fetch_google_image(ceo_name, company, google_key, google_cx)
            if g_url and download_image(g_url, dest):
                log.info("  [OK-GG]  %s", ceo_name)
                row.update(image_path=str(dest), source="google", status="ok")
                results.append(row)
                pd.DataFrame(results).to_csv(out / "index.csv", index=False)
                time.sleep(random.uniform(*delay_range))
                continue

        status = "no_ceo_found" if not ceo_name else "no_image"
        log.warning("  [FAIL]  %s", status)
        row["status"] = status
        results.append(row)
        pd.DataFrame(results).to_csv(out / "index.csv", index=False)

    df = pd.DataFrame(results)
    df.to_csv(out / "index.csv", index=False)

    ok     = (df["status"] == "ok").sum()
    cached = (df["status"] == "cached").sum()
    failed = len(df) - ok - cached
    log.info("Done — %d downloaded, %d cached, %d failed", ok, cached, failed)
    if ok:
        log.info("Sources: %s", df[df.status=="ok"]["source"].value_counts().to_dict())

    return df


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape S&P 500 CEO headshots via Wikidata + Wikipedia."
    )
    parser.add_argument("--tickers", nargs="+", metavar="T",
                        help="Specific tickers (default: all).")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N companies.")
    parser.add_argument("--output", default="./ceo_photos",
                        help="Output directory (default: ./ceo_photos).")
    parser.add_argument("--resume", action="store_true",
                        help="Skip already-downloaded images.")
    parser.add_argument("--google-key", default="",
                        help="Google Custom Search API key (optional).")
    parser.add_argument("--google-cx", default="",
                        help="Google Custom Search engine ID (optional).")
    parser.add_argument("--batch-size", type=int, default=20,
                        help="Companies per Wikidata batch (default: 20).")
    args = parser.parse_args()

    df = run(
        tickers=args.tickers,
        limit=args.limit,
        output_dir=args.output,
        resume=args.resume,
        google_key=args.google_key,
        google_cx=args.google_cx,
        batch_size=args.batch_size,
    )

    print("\n── Results ───────────────────────────────────────────────────────")
    print(df[["ticker", "company", "ceo_name", "source", "status"]].to_string(index=False))
    print(f"\nImages + CSV → {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
