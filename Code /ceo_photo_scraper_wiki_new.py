"""
CEO Photo Scraper — Full S&P 500 Edition
==========================================
Pipeline:
  Step 1 — Fetch current S&P 500 list from Wikipedia (always up to date)
  Step 2 — Resolve each company Wikidata QID via Wikidata search API
  Step 3 — Batch-query Wikidata SPARQL for CEO name + official portrait
  Step 4 — Fallback to Wikipedia API image if Wikidata has no photo
  Step 5 — Validate each image: detectable face, minimum resolution,
            frontal pose score — flags images unsuitable for facial analysis

Output:
    ./ceo_photos/<ticker>_ceo.jpg      — downloaded portraits
    ./ceo_photos/index.csv             — full metadata + quality flags
    ./ceo_photos/qid_cache.json        — cached QID lookups (speeds up reruns)

Install:
    pip install requests pandas Pillow SPARQLWrapper opencv-python-headless
Usage:
    python ceo_photo_scraper.py                  # full S&P 500
    python ceo_photo_scraper.py --limit 20        # first N companies (test run)
    python ceo_photo_scraper.py --resume          # skip already downloaded
    python ceo_photo_scraper.py --tickers AAPL MSFT NVDA
    python ceo_photo_scraper.py --no-validate     # skip face validation step
    python ceo_photo_scraper.py --google-key KEY --google-cx CX
"""

import re
import json
import time
import random
import logging
import argparse
from pathlib import Path

import requests
import pandas as pd
from PIL import Image
from SPARQLWrapper import SPARQLWrapper, JSON as SPARQL_JSON

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_API    = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_API   = "https://en.wikipedia.org/w/api.php"
MIN_IMAGE_BYTES = 10_000
MIN_DIM         = 120
FACE_MIN_SIZE   = 60

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "CEOPhotoScraper/3.0 (academic research; python-requests)",
    "Accept": "application/json",
})


# ── Step 1: Fetch S&P 500 list from Wikipedia ─────────────────────────────────

def fetch_sp500_list() -> list:
    """Returns list of (ticker, company_name) from Wikipedia's S&P 500 article."""
    log.info("Fetching current S&P 500 list from Wikipedia...")
    resp = SESSION.get(WIKIPEDIA_API, params={
        "action": "parse",
        "page": "List of S&P 500 companies",
        "prop": "wikitext",
        "format": "json",
    }, timeout=30)
    resp.raise_for_status()
    wikitext = resp.json()["parse"]["wikitext"]["*"]

    companies = []
    seen = set()

    # Primary pattern: wikitable rows with company + ticker
    rows = re.findall(
        r"\|\s*\[\[([^\|\]]+?)(?:\|[^\]]*)?\]\].*?\|\|\s*([A-Z]{1,5})\s*\|\|",
        wikitext, re.DOTALL
    )
    for name, ticker in rows:
        name   = name.strip()
        ticker = ticker.strip()
        if ticker and ticker not in seen and len(ticker) <= 5:
            seen.add(ticker)
            companies.append((ticker, name))

    log.info("Found %d S&P 500 companies", len(companies))
    return companies


# ── Step 2: Resolve Wikidata QIDs ─────────────────────────────────────────────

def resolve_qid(company_name: str, ticker: str) -> str:
    """Search Wikidata for a company, return its QID string."""
    for query in [company_name, f"{company_name} company"]:
        try:
            resp = SESSION.get(WIKIDATA_API, params={
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "type": "item",
                "limit": 5,
                "format": "json",
            }, timeout=10)
            for r in resp.json().get("search", []):
                desc  = r.get("description", "").lower()
                label = r.get("label", "").lower()
                name_lower = company_name.lower()
                if any(kw in desc for kw in [
                    "company", "corporation", "inc", "ltd", "plc",
                    "group", "holdings", "bank", "pharmaceutical",
                    "insurance", "financial", "technology", "energy"
                ]):
                    return r["id"]
                if name_lower.split()[0] in label:
                    return r["id"]
        except Exception as e:
            log.debug("QID lookup error %s: %s", company_name, e)
        time.sleep(0.15)
    return ""


def resolve_qids_bulk(companies: list, cache_path: Path) -> dict:
    """Resolve QIDs for all companies with caching."""
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text())
            log.info("Loaded %d cached QIDs", len(cache))
        except Exception:
            pass

    missing = [(t, n) for t, n in companies if t not in cache]
    log.info("Resolving QIDs: %d new, %d cached", len(missing), len(cache))

    for i, (ticker, name) in enumerate(missing, 1):
        if i % 25 == 0:
            log.info("  QID progress: %d/%d", i, len(missing))
            cache_path.write_text(json.dumps(cache, indent=2))
        cache[ticker] = resolve_qid(name, ticker)
        time.sleep(0.25)

    cache_path.write_text(json.dumps(cache, indent=2))
    found = sum(1 for v in cache.values() if v)
    log.info("QIDs resolved: %d/%d found", found, len(cache))
    return cache


# ── Step 3: Wikidata SPARQL for CEO + image ───────────────────────────────────

SPARQL_TMPL = """
SELECT ?ticker ?ceoLabel ?image WHERE {{
  VALUES (?ticker ?company) {{ {values} }}
  ?company wdt:P169 ?ceo .
  OPTIONAL {{ ?ceo wdt:P18 ?image }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
}}
"""

def fetch_wikidata_batch(batch: list) -> dict:
    """batch: list of (ticker, name, qid). Returns ticker -> {ceo_name, image_url}."""
    valid  = [(t, n, q) for t, n, q in batch if q]
    if not valid:
        return {}
    values = " ".join(f'("{t}" wd:{q})' for t, _, q in valid)
    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.addCustomHttpHeader("User-Agent", "CEOPhotoScraper/3.0")
    sparql.setQuery(SPARQL_TMPL.format(values=values))
    sparql.setReturnFormat(SPARQL_JSON)
    try:
        rows = sparql.query().convert()["results"]["bindings"]
    except Exception as e:
        log.error("SPARQL failed: %s", e)
        return {}
    out = {}
    for row in rows:
        t = row.get("ticker", {}).get("value", "")
        if t:
            out[t] = {
                "ceo_name":  row.get("ceoLabel", {}).get("value", ""),
                "image_url": row.get("image",    {}).get("value", ""),
            }
    return out


def fetch_all_wikidata(companies_with_qids: list, batch_size: int = 25) -> dict:
    results = {}
    batches = [companies_with_qids[i:i+batch_size]
               for i in range(0, len(companies_with_qids), batch_size)]
    log.info("SPARQL: %d batches of up to %d", len(batches), batch_size)
    for i, batch in enumerate(batches, 1):
        log.info("  SPARQL batch %d/%d", i, len(batches))
        results.update(fetch_wikidata_batch(batch))
        time.sleep(1.2)
    ceos = sum(1 for v in results.values() if v.get("ceo_name"))
    imgs = sum(1 for v in results.values() if v.get("image_url"))
    log.info("Wikidata done: %d CEOs, %d with images", ceos, imgs)
    return results


# ── Step 4: Image download + fallbacks ───────────────────────────────────────

def download_image(url: str, dest: Path) -> bool:
    try:
        resp = SESSION.get(url, timeout=20, stream=True)
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
            if img.format != "JPEG":
                img.convert("RGB").save(dest, "JPEG", quality=92)
        return True
    except Exception as e:
        log.debug("download_image %s: %s", url, e)
        dest.unlink(missing_ok=True)
        return False


def fetch_wikipedia_image(ceo_name: str) -> str:
    try:
        search = SESSION.get(WIKIPEDIA_API, params={
            "action": "query", "list": "search",
            "srsearch": ceo_name + " CEO executive",
            "srlimit": 1, "format": "json",
        }, timeout=10).json()
        hits = search.get("query", {}).get("search", [])
        if not hits:
            return ""
        title = hits[0]["title"]
        img = SESSION.get(WIKIPEDIA_API, params={
            "action": "query", "titles": title,
            "prop": "pageimages", "pithumbsize": 600,
            "format": "json",
        }, timeout=10).json()
        for page in img.get("query", {}).get("pages", {}).values():
            return page.get("thumbnail", {}).get("source", "")
    except Exception as e:
        log.debug("Wikipedia image failed for %s: %s", ceo_name, e)
    return ""


def fetch_google_image(ceo_name: str, company: str, api_key: str, cx: str) -> str:
    try:
        items = SESSION.get("https://www.googleapis.com/customsearch/v1", params={
            "key": api_key, "cx": cx,
            "q": f"{ceo_name} {company} CEO official portrait",
            "searchType": "image", "num": 3,
            "imgType": "face", "safe": "active",
        }, timeout=10).json().get("items", [])
        if items:
            return items[0].get("link", "")
    except Exception as e:
        log.debug("Google CSE failed for %s: %s", ceo_name, e)
    return ""


# ── Step 5: Face validation ───────────────────────────────────────────────────

def validate_face(image_path: Path) -> dict:
    """
    Runs OpenCV Haar cascade face detection.
    Returns quality metadata useful for downstream facial analysis
    (dark circles, skin analysis, etc.)
    """
    import cv2
    result = {
        "face_detected": False, "face_count": 0,
        "face_box": None, "face_size_px": 0,
        "image_width": 0, "image_height": 0,
        "quality_flag": "no_face",
    }
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return result
        h, w = img.shape[:2]
        result["image_width"]  = w
        result["image_height"] = h
        gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5,
            minSize=(FACE_MIN_SIZE, FACE_MIN_SIZE)
        )
        if len(faces) == 0:
            result["quality_flag"] = "no_face"
        elif len(faces) > 1:
            result.update(face_detected=True, face_count=len(faces),
                          quality_flag="multiple_faces")
        else:
            x, y, fw, fh = faces[0]
            result.update(
                face_detected=True, face_count=1,
                face_box=f"{x},{y},{fw},{fh}",
                face_size_px=int(fw),
                quality_flag="good" if fw >= FACE_MIN_SIZE else "face_too_small",
            )
    except Exception as e:
        log.debug("Face validation error %s: %s", image_path, e)
    return result


# ── Main orchestrator ─────────────────────────────────────────────────────────

def run(
    tickers=None, limit=None, output_dir="./ceo_photos",
    resume=False, validate=True,
    google_key="", google_cx="",
    batch_size=25, delay_range=(0.5, 1.5),
):
    """
    Full pipeline: S&P 500 list → QIDs → CEO data → images → face validation.

    Parameters
    ----------
    tickers      : list of tickers to filter, or None for all S&P 500
    limit        : max companies to process
    output_dir   : folder for images + CSVs
    resume       : skip already-downloaded tickers
    validate     : run OpenCV face detection on each image
    google_key   : Google CSE API key (optional 3rd fallback)
    google_cx    : Google CSE engine ID (optional 3rd fallback)
    batch_size   : companies per Wikidata SPARQL request
    delay_range  : (min, max) seconds between HTTP requests

    Returns
    -------
    pd.DataFrame with columns:
        ticker, company, qid, ceo_name, image_path, source, status,
        face_detected, face_count, face_size_px,
        image_width, image_height, quality_flag
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache_path = out / "qid_cache.json"

    # 1. S&P 500 list
    sp500 = fetch_sp500_list()
    if not sp500:
        log.error("Failed to fetch S&P 500 list.")
        return pd.DataFrame()
    if tickers:
        up = {t.upper() for t in tickers}
        sp500 = [(t, n) for t, n in sp500 if t.upper() in up]
    if limit:
        sp500 = sp500[:limit]
    log.info("Targeting %d companies", len(sp500))

    # 2. QIDs
    qid_map = resolve_qids_bulk(sp500, cache_path)
    cwq     = [(t, n, qid_map.get(t, "")) for t, n in sp500]

    # 3. Wikidata CEO + image data
    wikidata = fetch_all_wikidata(cwq, batch_size)

    # 4+5. Download + validate
    results = []
    for idx, (ticker, company, qid) in enumerate(cwq, 1):
        log.info("[%d/%d] %s — %s", idx, len(cwq), ticker, company)

        safe = re.sub(r"[^\w]", "_", ticker.lower())
        dest = out / f"{safe}_ceo.jpg"

        row = {
            "ticker": ticker, "company": company, "qid": qid,
            "ceo_name": "", "image_path": "", "source": "", "status": "pending",
            "face_detected": None, "face_count": None, "face_size_px": None,
            "image_width": None, "image_height": None, "quality_flag": None,
        }

        # Resume
        if resume and dest.exists():
            wd = wikidata.get(ticker, {})
            row.update(ceo_name=wd.get("ceo_name",""), image_path=str(dest),
                       source="cached", status="cached")
            if validate:
                row.update(validate_face(dest))
            results.append(row)
            log.info("  [SKIP]")
            continue

        wd        = wikidata.get(ticker, {})
        ceo_name  = wd.get("ceo_name", "")
        image_url = wd.get("image_url", "")
        row["ceo_name"] = ceo_name
        downloaded = False

        # Source 1: Wikidata portrait
        if image_url and download_image(image_url, dest):
            row.update(source="wikidata", status="ok")
            downloaded = True
            log.info("  [WD] OK — %s", ceo_name)

        # Source 2: Wikipedia
        if not downloaded and ceo_name:
            wp = fetch_wikipedia_image(ceo_name)
            if wp and download_image(wp, dest):
                row.update(source="wikipedia", status="ok")
                downloaded = True
                log.info("  [WP] OK — %s", ceo_name)
            time.sleep(random.uniform(*delay_range))

        # Source 3: Google CSE
        if not downloaded and ceo_name and google_key and google_cx:
            g = fetch_google_image(ceo_name, company, google_key, google_cx)
            if g and download_image(g, dest):
                row.update(source="google", status="ok")
                downloaded = True
                log.info("  [GG] OK — %s", ceo_name)

        if downloaded:
            row["image_path"] = str(dest)
            if validate:
                face_info = validate_face(dest)
                row.update(face_info)
                log.info("  [QA] %s", face_info.get("quality_flag", "?"))
        else:
            row["status"] = "no_ceo_found" if not ceo_name else "no_image"
            log.warning("  [FAIL] %s", row["status"])

        results.append(row)
        pd.DataFrame(results).to_csv(out / "index.csv", index=False)
        time.sleep(random.uniform(*delay_range))

    # Summary
    df = pd.DataFrame(results)
    df.to_csv(out / "index.csv", index=False)
    ok     = (df.status == "ok").sum()
    cached = (df.status == "cached").sum()
    failed = len(df) - ok - cached
    log.info("=" * 55)
    log.info("DONE  ✓ %d downloaded  ◎ %d cached  ✗ %d failed", ok, cached, failed)
    if validate and ok + cached > 0:
        good = (df.quality_flag == "good").sum()
        log.info("Face quality: %d / %d good for analysis", good, ok + cached)
        log.info("\n%s", df.quality_flag.value_counts(dropna=False).to_string())
    log.info("=" * 55)
    return df


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="S&P 500 CEO photo scraper with face validation."
    )
    p.add_argument("--tickers",     nargs="+", metavar="T")
    p.add_argument("--limit",       type=int,  default=None)
    p.add_argument("--output",      default="./ceo_photos")
    p.add_argument("--resume",      action="store_true")
    p.add_argument("--no-validate", action="store_true")
    p.add_argument("--google-key",  default="")
    p.add_argument("--google-cx",   default="")
    p.add_argument("--batch-size",  type=int, default=25)
    args = p.parse_args()

    df = run(
        tickers=args.tickers, limit=args.limit,
        output_dir=args.output, resume=args.resume,
        validate=not args.no_validate,
        google_key=args.google_key, google_cx=args.google_cx,
        batch_size=args.batch_size,
    )
    if not df.empty:
        print("\n── Results ──────────────────────────────────────────────")
        cols = ["ticker","company","ceo_name","source","status","quality_flag"]
        print(df[cols].to_string(index=False))
        print(f"\nSaved to: {Path(args.output).resolve()}/")
        print("  index.csv       — full metadata + quality flags")
        print("  qid_cache.json  — reused on next run to skip QID lookups")


if __name__ == "__main__":
    main()
