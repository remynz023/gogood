"""
Unleashed Software API client for Go Good.

Credentials come from UNLEASHED_API_ID / UNLEASHED_API_KEY, loaded from the
environment or from a .env file (repo root first, then GOGOOD_ENV_FILE).

Signing: Unleashed signs the RAW, unencoded query string (e.g.
"warehouseCode=HONG KONG&pageSize=1000") with HMAC-SHA256 keyed by the API key,
while the URL itself is %20-encoded. Signing the urlencoded string instead
silently 403s for any parameter containing a space.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from urllib.parse import quote, urlencode

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
if os.environ.get("GOGOOD_ENV_FILE"):
    load_dotenv(os.environ["GOGOOD_ENV_FILE"])

BASE_URL = "https://api.unleashedsoftware.com"


def _headers(raw_query):
    key = os.environ["UNLEASHED_API_KEY"]
    sig = base64.b64encode(
        hmac.new(key.encode(), raw_query.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "api-auth-id": os.environ["UNLEASHED_API_ID"],
        "api-auth-signature": sig,
        "client-type": "gogood/analytics",
    }


def api_get(endpoint, page=1, retries=5, timeout=60, **params):
    """GET /{endpoint}/{page}?{params}. Page is a PATH segment, not a query param."""
    params = {k: v for k, v in params.items() if v is not None}
    raw = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE_URL}/{endpoint}/{page}"
    if params:
        url += "?" + urlencode(params, quote_via=quote)
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=_headers(raw), timeout=timeout)
            r.raise_for_status()
            return r.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if attempt == retries or status in (401, 403, 404):
                raise
            time.sleep(5 * (attempt + 1))


def api_get_all(endpoint, **params):
    """Follow pagination and return the merged list of Items."""
    items, page = [], 1
    while True:
        result = api_get(endpoint, page=page, **params)
        items.extend(result.get("Items", []))
        if page >= (result.get("Pagination") or {}).get("NumberOfPages", 1):
            return items
        page += 1


def pull_to_dir(endpoint, out_dir, page_size=200, **params):
    """Page-by-page pull cached as p{N}.json, resumable after a failure.

    Large SalesOrders pulls time out at pageSize=1000; 200 is reliable
    (12 months of MAIN ~= 170 pages / ~25 min).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    first = api_get(endpoint, page=1, pageSize=page_size, **params)
    n = first["Pagination"]["NumberOfPages"]
    (out / "p1.json").write_text(json.dumps(first["Items"]))
    for p in range(2, n + 1):
        f = out / f"p{p}.json"
        if f.exists():
            continue
        f.write_text(json.dumps(api_get(endpoint, page=p, pageSize=page_size, **params)["Items"]))
        if p % 20 == 0:
            print(f"  page {p}/{n}", flush=True)
    return n


def load_dir(out_dir):
    """Load a pull_to_dir cache, de-duplicating on Guid (pages can shift mid-pull)."""
    seen, items = set(), []
    for f in sorted(Path(out_dir).glob("p*.json")):
        for it in json.loads(f.read_text()):
            if it["Guid"] not in seen:
                seen.add(it["Guid"])
                items.append(it)
    return items
