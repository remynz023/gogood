"""
Monthly net profit for one ship-to market, everything in NZD ex GST.

  Revenue     = Shopify net sales + shipping charged                       (Shopify)
  Product     = Shopify net sales x Unleashed COGS % at time of sale       (Unleashed)
  Courier     = SG: Shopify tracking numbers matched to EasyParcel (SGD)   (EasyParcel)
                NZ: NZ Couriers consignments by created date (NZD)         (GoSweetSpot)
  Handling    = flat per order: SG SGD 5 fulfilment, NZ NZ$3 pick
  Ads         = Google + Facebook spend targeted at the country            (Windsor)
  Net profit  = Revenue - all of the above. Excludes payment fees, apps, rent, staff.

Inputs (see README for how to export each):
  --shopify-monthly CSV  month,orders,net_sales,shipping_charges   (ShopifyQL, one market)
  --ads             CSV  month,google,facebook                     (Windsor, NZD)
  --orders          pull_sales_orders.py dir for the market's warehouse

    python scripts/market_pnl.py --market Singapore --orders data/orders_SINGAPORE_2026-01-01 \
        --shopify-monthly data/shopify_sg_monthly.csv --ads data/ads_sg_monthly.csv \
        --easyparcel data/easyparcel_shipments.json --shopify-orders data/shopify_orders.jsonl \
        --handling 5 --handling-ccy SGD --start 2026-01-01 --end 2026-10-17 --csv out/sg_pnl.csv
"""

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gogood.costs import parse_date  # noqa: E402
from gogood.fx import monthly_rate  # noqa: E402
from gogood.unleashed import load_dir  # noqa: E402

SHOPIFY_PREFIX = "go-good-nz#"
NZT = ZoneInfo("Pacific/Auckland")
ISO = {"Singapore": "SG", "New Zealand": "NZ", "Australia": "AU", "Hong Kong": "HK"}

ap = argparse.ArgumentParser()
ap.add_argument("--market", required=True, choices=list(ISO))
ap.add_argument("--orders", required=True)
ap.add_argument("--shopify-monthly", required=True)
ap.add_argument("--ads", required=True)
ap.add_argument("--easyparcel", help="pull_couriers.py easyparcel output (SG)")
ap.add_argument("--shopify-orders", help="Shopify bulk-export JSONL with fulfillments.trackingInfo (SG)")
ap.add_argument("--gss", help="pull_couriers.py gss output (NZ)")
ap.add_argument("--handling", type=float, default=0.0, help="cost per order")
ap.add_argument("--handling-ccy", default="NZD")
ap.add_argument("--start", required=True)
ap.add_argument("--end", required=True, help="inclusive")
ap.add_argument("--csv")
ap.add_argument("--md", help="write a markdown table")
a = ap.parse_args()
end = dt.date.fromisoformat(a.end)


def nz_month(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(NZT).strftime("%Y-%m")


# --- Shopify revenue and ads -------------------------------------------------------------
t = pd.read_csv(a.shopify_monthly, dtype={"month": str}).set_index("month")
t.index = t.index.str[:7]
t = t.loc[(t.index >= a.start[:7]) & (t.index <= a.end[:7])]
ads = pd.read_csv(a.ads, dtype={"month": str}).set_index("month")
ads.index = ads.index.str[:7]
t = t.join(ads)
t["revenue"] = t.net_sales + t.shipping_charges

# --- Product cost: Unleashed COGS % at time of sale, Shopify orders only ------------------
cg = defaultdict(lambda: [0.0, 0.0])
for o in load_dir(a.orders):
    if (o.get("DeliveryCountry") or "").strip() != a.market:
        continue
    if not o["OrderNumber"].startswith(SHOPIFY_PREFIX) or o["OrderStatus"] in ("Deleted", "Cancelled", "Parked"):
        continue
    d = parse_date(o["OrderDate"]).date()
    if d > end:
        continue
    for ln in o["SalesOrderLines"]:
        if ln["LineType"] == "Charge" or not ln["Product"]["ProductCode"]:
            continue
        g = cg[d.strftime("%Y-%m")]
        g[0] += ln["BCLineTotal"] or 0
        g[1] += (ln["OrderQuantity"] or 0) * (ln["AverageLandedPriceAtTimeOfSale"] or 0)
t["cogs_pct"] = [cg[m][1] / cg[m][0] if cg[m][0] else float("nan") for m in t.index]
t["product_cost"] = t.net_sales * t.cogs_pct

# --- FX ------------------------------------------------------------------------------------
fx = {m: 1.0 for m in t.index}
if a.handling_ccy != "NZD" or a.easyparcel:
    ccy = "SGD" if a.easyparcel else a.handling_ccy
    fx = monthly_rate(ccy, "NZD", a.start, a.end)
    t["nzd_per_" + ccy.lower()] = [fx[m] for m in t.index]
t["handling"] = t.orders * a.handling * pd.Series({m: fx[m] for m in t.index})

# --- Courier -------------------------------------------------------------------------------
t["courier_note"] = ""
if a.easyparcel:
    ep = {s["awb_number"].strip(): s for s in json.load(open(a.easyparcel))
          if s["shipment_status"] != "Cancelled" and s.get("awb_number")}
    orders = [json.loads(line) for line in open(a.shopify_orders, encoding="utf-8")]
    orders = [o for o in orders if "createdAt" in o and not o.get("cancelledAt")
              and (o.get("shippingAddress") or {}).get("countryCodeV2") == ISO[a.market]]
    awb_orders = defaultdict(int)
    for o in orders:
        for f in o.get("fulfillments") or []:
            for tr in f.get("trackingInfo") or []:
                if tr.get("number"):
                    awb_orders[tr["number"].strip()] += 1
    m_cost, m_n = defaultdict(float), defaultdict(int)
    for o in orders:
        hits = [tr["number"].strip() for f in o.get("fulfillments") or [] for tr in f.get("trackingInfo") or []
                if tr.get("number") and tr["number"].strip() in ep]
        if hits and dt.date.fromisoformat(o["createdAt"][:10]) <= end:
            m = nz_month(o["createdAt"])
            m_n[m] += 1
            m_cost[m] += sum(float(ep[h]["pricing"]["price"] or 0) / awb_orders[h] for h in hits)
    overall = sum(m_cost.values()) / sum(m_n.values())
    rate = {m: (m_cost[m] / m_n[m] if m_n[m] >= 50 else overall) for m in t.index}
    t["courier_per_order_sgd"] = pd.Series(rate)
    t["courier_matched_orders"] = pd.Series(m_n).reindex(t.index).fillna(0).astype(int)
    t.loc[t.courier_matched_orders < 50, "courier_note"] = "estimated at average matched cost"
    t["courier"] = t.orders * t.courier_per_order_sgd * pd.Series({m: fx[m] for m in t.index})
elif a.gss:
    c = defaultdict(float)
    for s in json.load(open(a.gss)):
        if s.get("IsDeleted") or s.get("Carrier") == "International Courier":
            continue
        ts = dt.datetime.fromisoformat(s["CreatedUtc"][:19]).replace(tzinfo=dt.timezone.utc).astimezone(NZT)
        if ts.date() <= end:
            c[ts.strftime("%Y-%m")] += s.get("TotalCost") or 0
    t["courier"] = pd.Series(c).reindex(t.index).fillna(0)
else:
    t["courier"] = 0.0

t["net_profit"] = t.revenue - t.product_cost - t.courier - t.handling - t.google - t.facebook
t["margin"] = t.net_profit / t.revenue
cols = ["orders", "revenue", "product_cost", "cogs_pct", "courier", "handling", "google", "facebook", "net_profit", "margin"]
pd.set_option("display.width", 220)
print(t[cols].round(3).to_string())
tot = t[cols].sum()
tot["cogs_pct"], tot["margin"] = tot.product_cost / t.net_sales.sum(), tot.net_profit / tot.revenue
print(f"\nTotal: revenue {tot.revenue:,.0f}  net profit {tot.net_profit:,.0f}  margin {tot.margin:.1%}")

if a.csv:
    Path(a.csv).parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(a.csv)
if a.md:
    def money(v):
        return f"−{abs(v):,.0f}" if v else "0"
    last = pd.Period(a.end, "D")
    lines = ["| Month | Orders | Revenue | Product cost | Courier | Handling | Google | Facebook | **Net profit** | Margin |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for m, r in t.iterrows():
        label = pd.Period(m, "M").strftime("%b %Y")
        if m == a.end[:7] and last.day != last.days_in_month:
            label += f" (to {last.day})"
        if r.courier_note:
            label += "*"
        lines.append(f"| {label} | {r.orders:,.0f} | {r.revenue:,.0f} | {money(r.product_cost)} ({r.cogs_pct:.1%}) | "
                     f"{money(r.courier)} | {money(r.handling)} | {money(r.google)} | {money(r.facebook)} | "
                     f"**{r.net_profit:,.0f}** | {r.margin:.1%} |")
    lines.append(f"| **Total** | **{tot.orders:,.0f}** | **{tot.revenue:,.0f}** | **{money(tot.product_cost)} ({tot.cogs_pct:.1%})** | "
                 f"**{money(tot.courier)}** | **{money(tot.handling)}** | **{money(tot.google)}** | **{money(tot.facebook)}** | "
                 f"**{tot.net_profit:,.0f}** | **{tot.margin:.1%}** |")
    Path(a.md).parent.mkdir(parents=True, exist_ok=True)
    Path(a.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("saved", a.md)
