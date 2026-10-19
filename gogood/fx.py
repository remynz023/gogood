"""
Monthly average FX from the ECB via frankfurter.app (free, no key).

Unleashed's own SGD rate is fixed at ~1.19 NZD/SGD for most of 2026 and is out of
date (market was 1.31-1.39), so don't use the ExchangeRate on Unleashed orders.
"""

import json

import pandas as pd
import requests

from .unleashed import REPO_ROOT

CACHE = REPO_ROOT / "data" / "fx_cache.json"


def monthly_rate(base, quote, start, end):
    """{'2026-01': avg quote-per-base} for each month between two dates (YYYY-MM-DD)."""
    key = f"{base}{quote}_{start}_{end}"
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if key not in cache:
        r = requests.get(f"https://api.frankfurter.app/{start}..{end}", params={"from": base, "to": quote}, timeout=60)
        r.raise_for_status()
        s = pd.Series({d: v[quote] for d, v in r.json()["rates"].items()})
        s.index = pd.to_datetime(s.index).to_period("M").astype(str)
        cache[key] = s.groupby(level=0).mean().round(5).to_dict()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, indent=1))
    return cache[key]
