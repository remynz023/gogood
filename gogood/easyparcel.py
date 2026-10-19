"""
EasyParcel Open API client (Go Good Limited, live Singapore account).

OAuth2 authorisation-code flow. Credentials EP_CLIENT_ID / EP_CLIENT_SECRET come
from the environment / .env (see unleashed.py for how .env is found). Tokens are
cached in data/easyparcel_tokens.json (git-ignored) and refreshed automatically
(access tokens last 10 hours).

    python -m gogood.easyparcel login     # one-time browser sign-in (choose the Live account)

Gotchas:
  * Cloudflare in front of the API rejects Python's default User-Agent (error 1010).
  * Prices are SGD. coll_date is UTC; add 8h for the Singapore date.
  * shipment/list returns up to 250 shipments per call, with prices.
  * The account's records start on 11 May 2026.
"""

import base64
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser

import requests

from .unleashed import REPO_ROOT  # noqa: F401  (loads .env)

API = "https://api.easyparcel.com/open_api/2026-09"
AUTH_URL = "https://api.easyparcel.com/oauth/login"
TOKEN_URL = "https://api.easyparcel.com/oauth/token"
REDIRECT_URI = "http://localhost:8765/callback"
TOKEN_FILE = REPO_ROOT / "data" / "easyparcel_tokens.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GoGoodAnalytics/1.0"


def _creds():
    return os.environ["EP_CLIENT_ID"], os.environ["EP_CLIENT_SECRET"]


def _token_request(params):
    cid, secret = _creds()
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(TOKEN_URL, data=params, timeout=60,
                      headers={"Authorization": f"Basic {basic}", "User-Agent": UA, "Accept": "application/json"})
    r.raise_for_status()
    tok = r.json()
    tok["_obtained"] = time.time()
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tok, indent=2))
    return tok


def login():
    """Browser sign-in; the callback lands on a one-shot local server."""
    cid, _ = _creds()
    state, result = secrets.token_urlsafe(16), {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>EasyParcel connected. You can close this tab.</h2>")

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("localhost", 8765), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()
    webbrowser.open(AUTH_URL + "?" + urllib.parse.urlencode(
        {"client_id": cid, "redirect_uri": REDIRECT_URI, "state": state}))
    while "code" not in result and "error" not in result:
        time.sleep(0.5)
    server.server_close()
    if result.get("state") != state or "code" not in result:
        sys.exit(f"Login failed: {result.get('error', 'state mismatch')}")
    _token_request({"grant_type": "authorization_code", "code": result["code"],
                    "redirect_uri": REDIRECT_URI, "state": state})
    print(f"Signed in; tokens saved to {TOKEN_FILE}")


def access_token():
    if not TOKEN_FILE.exists():
        sys.exit("Not signed in to EasyParcel. Run: python -m gogood.easyparcel login")
    tok = json.loads(TOKEN_FILE.read_text())
    if time.time() > tok["_obtained"] + tok.get("expires_in", 0) - 300:
        tok = _token_request({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
                              "redirect_uri": REDIRECT_URI})
    return tok["access_token"]


def post(endpoint, body):
    r = requests.post(f"{API}/{endpoint}", json=body, timeout=60,
                      headers={"Authorization": f"Bearer {access_token()}", "User-Agent": UA,
                               "Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def shipments(date_from, date_to):
    """All shipments collected between two dates (YYYY-MM-DD), 250 per call, with prices."""
    base = {"limit": 250, "date_from": date_from, "date_to": date_to}
    rows, seen, body = [], set(), dict(base)
    while True:
        r = post("shipment/list", body)
        data = r.get("data") or []
        new = [s for s in data if s["shipment_number"] not in seen]
        for s in new:
            seen.add(s["shipment_number"])
            rows.append(s)
        if not data or not new or len(data) < 250:
            return rows
        body = dict(base)
        tok = (r.get("pagination") or {}).get("next_page_token")
        if tok:
            body["next_page_token"] = tok
        body["before_shipment_number"] = data[-1]["shipment_number"]


if __name__ == "__main__":
    if sys.argv[1:] == ["login"]:
        login()
    else:
        sys.exit(__doc__)
