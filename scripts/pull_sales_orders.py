"""
Pull Unleashed SalesOrders for one warehouse into a resumable page cache.

    python scripts/pull_sales_orders.py --warehouse MAIN --start 2025-10-01
    -> data/orders_MAIN_2025-10-01/p1.json ... pN.json

Warehouse ships-to: MAIN=NZ, AUS=Australia, SINGAPORE=SG (+ some MY),
HONG KONG=HK (+ JP/TH/AE). Re-running skips pages already on disk.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gogood.unleashed import pull_to_dir  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--warehouse", required=True)
ap.add_argument("--start", required=True, help="YYYY-MM-DD (filters on OrderDate)")
ap.add_argument("--out", help="default data/orders_<WH>_<start>")
a = ap.parse_args()

out = a.out or f"data/orders_{a.warehouse.replace(' ', '_')}_{a.start}"
n = pull_to_dir("SalesOrders", out, warehouseCode=a.warehouse, startDate=a.start)
print(f"{n} pages -> {out}")
