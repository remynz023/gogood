"""
GoSweetSpot freight API client (NZ Couriers for the NZ warehouse).

Credentials GSS_ACCESS_KEY / GSS_SITE_ID from the environment / .env.
Docs: https://api-docs.gosweetspot.com/

Gotchas:
  * GET api/shipments filters only on LAST-UPDATE time (lastupdateminutc /
    lastupdatemaxutc), not creation. Pull a wide window and bucket by CreatedUtc.
  * TotalCost is the cost per consignment in NZD (contract rate).
  * Carrier 'International Courier' = parcels sent overseas from NZ (Mar-Apr 2026);
    exclude them from the NZ market.
"""

import datetime as dt
import os

import requests

from .unleashed import REPO_ROOT  # noqa: F401  (loads .env)

BASE = "https://api.gosweetspot.com/api"
KEEP = ("ConsignmentNo", "Carrier", "Service", "Status", "TotalCost", "CreatedUtc", "ManifestedAt",
        "Picked", "Parts", "TotalKg", "DestinationZone", "OriginZone", "IsDeleted", "CostCentre",
        "CustomerRef", "IsRuralDelivery")


def get(path, **params):
    r = requests.get(f"{BASE}/{path}", params=params, timeout=120,
                     headers={"access_key": os.environ["GSS_ACCESS_KEY"], "site_id": os.environ["GSS_SITE_ID"],
                              "Accept": "application/json", "User-Agent": "Mozilla/5.0 GoGoodAnalytics/1.0"})
    r.raise_for_status()
    return r.json()


def shipments(start, end, step_days=7):
    """{ConsignmentNo: shipment} for everything updated between two dates, without addresses."""
    rows, d = {}, start
    while d < end:
        e = min(d + dt.timedelta(days=step_days), end)
        page = 1
        while True:
            r = get("shipments", lastupdateminutc=f"{d} 00:00:00", lastupdatemaxutc=f"{e} 00:00:00",
                    page=page, pagesize=250, excludeDeletedShipments="true")
            for s in r.get("Results") or []:
                rows[s["ConsignmentNo"]] = {k: s.get(k) for k in KEEP}
            if page >= (r.get("Pages") or 1) or not r.get("Results"):
                break
            page += 1
        print(f"  {d}: {len(rows)} consignments", flush=True)
        d = e
    return rows
