"""
Net margin per product (SKU, bundles as sold) for one ship-to market.

  Price        = Unleashed BCLineTotal / units  (ex GST, after discounts), Shopify orders only
  Cost at sale = AverageLandedPriceAtTimeOfSale (what the units sold actually cost)
  Cost now     = current StockOnHand AvgCost (bundles = sum of parts, gogood.costs.unit_cost)
  GM           = (price - cost) / price
  Net margin   = GM at current cost - variable selling cost %, where variable selling cost
                 = (courier + handling + ads) / revenue for the market over the same months,
                 taken from market_pnl.py --csv. Allocated by revenue: every dollar of sales
                 carries the same share.

    python scripts/product_net_margin.py --orders data/orders_SINGAPORE_2026-01-01 --market Singapore \
        --pnl out/sg_pnl.csv --start 2026-07-01 --end 2026-10-17 --top 25 --md out/sg_products.md
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gogood.costs import current_costs, parse_date, unit_cost  # noqa: E402
from gogood.unleashed import load_dir  # noqa: E402

SHOPIFY_PREFIX = "go-good-nz#"

ap = argparse.ArgumentParser()
ap.add_argument("--orders", required=True)
ap.add_argument("--market", required=True)
ap.add_argument("--pnl", required=True, help="market_pnl.py --csv output")
ap.add_argument("--start", required=True)
ap.add_argument("--end", required=True, help="inclusive")
ap.add_argument("--top", type=int, default=25)
ap.add_argument("--csv")
ap.add_argument("--md")
a = ap.parse_args()

rows = []
for o in load_dir(a.orders):
    if (o.get("DeliveryCountry") or "").strip() != a.market:
        continue
    if not o["OrderNumber"].startswith(SHOPIFY_PREFIX) or o["OrderStatus"] in ("Deleted", "Cancelled", "Parked"):
        continue
    d = parse_date(o["OrderDate"])
    for ln in o["SalesOrderLines"]:
        if ln["LineType"] == "Charge" or not ln["Product"]["ProductCode"]:
            continue
        rows.append((d, ln["Product"]["ProductCode"].replace(" ", ""), ln["Product"].get("ProductDescription") or "",
                     ln["OrderQuantity"] or 0, ln["BCLineTotal"] or 0, ln["AverageLandedPriceAtTimeOfSale"] or 0))
df = pd.DataFrame(rows, columns=["date", "sku", "desc", "qty", "rev", "unit_cost"])
df = df[(df.date >= a.start) & (df.date <= pd.Timestamp(a.end) + pd.Timedelta(days=1))]
df["cost"] = df.qty * df.unit_cost

pnl = pd.read_csv(a.pnl, dtype={"month": str}).set_index("month")
pnl = pnl.loc[(pnl.index >= a.start[:7]) & (pnl.index <= a.end[:7])]
var = pnl[["courier", "handling", "google", "facebook"]].sum()
var_pct = var.sum() / pnl.revenue.sum()
print(f"Variable selling cost {var_pct:.1%} of revenue "
      f"(courier {var.courier / pnl.revenue.sum():.1%}, handling {var.handling / pnl.revenue.sum():.1%}, "
      f"ads {(var.google + var.facebook) / pnl.revenue.sum():.1%})")

costs = current_costs()
p = df.groupby("sku").agg(desc=("desc", "last"), units=("qty", "sum"), rev=("rev", "sum"), cost=("cost", "sum"))
p = p[p.units > 0]
p["price"] = p.rev / p.units
p["cost_at_sale"] = p.cost / p.units
p["cost_now"] = [unit_cost(s, costs) for s in p.index]
p["gm_at_sale"] = 1 - p.cost_at_sale / p.price
p["gm_now"] = 1 - p.cost_now / p.price
p["net_margin_now"] = p.gm_now - var_pct
p["net_profit_per_unit"] = p.price * p.net_margin_now
p["share_rev"] = p.rev / p.rev.sum()
p = p.sort_values("rev", ascending=False)
tot_gm_sale = 1 - p.cost.sum() / p.rev.sum()
tot_gm_now = 1 - (p.cost_now * p.units).sum() / p.rev.sum()
print(f"All products: GM at sale {tot_gm_sale:.1%}, GM at current cost {tot_gm_now:.1%}, "
      f"net margin at current cost {tot_gm_now - var_pct:.1%}")
pd.set_option("display.width", 220)
print(p.head(a.top).drop(columns=["cost"]).round(3).to_string())

if a.csv:
    Path(a.csv).parent.mkdir(parents=True, exist_ok=True)
    p.to_csv(a.csv)
if a.md:
    lines = [f"Variable selling cost: **{var_pct:.1%}** of revenue. All products: GM at sale {tot_gm_sale:.1%}, "
             f"at current cost {tot_gm_now:.1%}, **net margin {tot_gm_now - var_pct:.1%}**.", "",
             "| SKU | Product | Units | Revenue | Price | Cost at sale | Cost now | GM now | **Net margin** | Net $/unit |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for s, r in p.head(a.top).iterrows():
        lines.append(f"| {s} | {r.desc[:48]} | {r.units:,.0f} | {r.rev:,.0f} | {r.price:.2f} | {r.cost_at_sale:.2f} | "
                     f"{r.cost_now:.2f} | {r.gm_now:.1%} | **{r.net_margin_now:.1%}** | {r.net_profit_per_unit:.2f} |")
    Path(a.md).parent.mkdir(parents=True, exist_ok=True)
    Path(a.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("saved", a.md)
