"""
Unit-cost helpers.

Two cost bases:
  * current  - StockOnHand.AvgCost. A single GLOBAL average cost: identical in
               MAIN / AUS / HONG KONG / SINGAPORE (inter-warehouse freight is
               not loaded into it). Fine for a recent window only.
  * at sale  - SalesOrderLine.AverageLandedPriceAtTimeOfSale. The cost Unleashed
               stamped on the line when sold. Use this for anything historical.
"""

import datetime as dt
import re

from .unleashed import api_get_all

WAREHOUSES = ["MAIN", "AUS", "HONG KONG", "SINGAPORE"]


def parse_date(s):
    """Unleashed MS-epoch '/Date(1791417600000)/' -> date."""
    ms = int(re.search(r"Date\((\d+)", s).group(1))
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).replace(tzinfo=None)


def current_costs(warehouses=WAREHOUSES):
    """{ProductCode: AvgCost} merged across warehouses (MAIN first)."""
    costs = {}
    for wh in warehouses:
        for s in api_get_all("StockOnHand", warehouseCode=wh, pageSize=1000):
            if s.get("AvgCost"):
                costs.setdefault(s["ProductCode"], s["AvgCost"])
    return costs


def unit_cost(sku, costs):
    """Cost of a Shopify SKU, including comma-coded bundles.

    A bundle SKU like 'PLA-PINK,SAMP-PLA10,SHAK-PINK' is costed as the sum of
    its parts that exist as products. Colour tags (PLA-PINK) are not products
    and are skipped - this reconciles exactly to Unleashed's own bundle cost.
    Repeated parts count each time ('WPI-U02,WPI-U01,WPI-U01' = 2 x WPI-U01).
    """
    if not sku:
        return 0.0
    sku = sku.replace(" ", "")
    if "," not in sku and sku in costs:
        return costs[sku]
    return sum(costs[p] for p in sku.split(",") if p in costs)
