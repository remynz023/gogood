"""
Pull courier shipments with their costs (no customer addresses kept).

    python scripts/pull_couriers.py easyparcel --start 2026-05-01 --end 2026-10-19   # SG, SGD
    -> data/easyparcel_shipments.json
    python scripts/pull_couriers.py gss --start 2025-12-15 --end 2026-10-20          # NZ Couriers, NZD
    -> data/gss_shipments.json   (~10 min for a year; filters on last-update, so start early)
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gogood import easyparcel, gss  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("courier", choices=["easyparcel", "gss"])
ap.add_argument("--start", required=True)
ap.add_argument("--end", required=True)
ap.add_argument("--out")
a = ap.parse_args()

if a.courier == "easyparcel":
    keep = ("shipment_number", "awb_number", "coll_date", "shipment_status", "pricing", "courier")
    rows = [{k: s.get(k) for k in keep} for s in easyparcel.shipments(a.start, a.end)]
else:
    rows = list(gss.shipments(dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)).values())

out = Path(a.out or f"data/{'easyparcel' if a.courier == 'easyparcel' else 'gss'}_shipments.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(rows))
print(f"{len(rows)} shipments -> {out}")
