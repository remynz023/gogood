"""
AU market net profit, NZD ex GST, in the same layout as market_pnl.py.

    python scripts/au_pnl.py . "FedEx AU.csv" out/au_pnl.csv reports/au_pnl.md
"""
import csv, json, datetime as dt, sys
from collections import defaultdict
from zoneinfo import ZoneInfo
import pandas as pd

R, FEDEX, OUT_CSV, OUT_MD = sys.argv[1:5]
NZT = ZoneInfo("Pacific/Auckland")
months = [f"2026-{m:02d}" for m in range(1, 11)]

# Shopify, shipping_country = Australia (NZD ex GST): orders, net_sales, shipping_charges, cost_of_goods_sold
shop = {"2026-01": (142, 19955.24, 543.45, 7681.42), "2026-02": (143, 20756.28, 538.10, 7863.12),
        "2026-03": (256, 38862.61, 865.32, 16601.84), "2026-04": (231, 35044.90, 917.83, 15314.26),
        "2026-05": (299, 39622.32, 1511.63, 14550.62), "2026-06": (265, 38812.04, 1170.29, 14671.83),
        "2026-07": (408, 56840.35, 1758.54, 25461.85), "2026-08": (410, 58346.75, 1730.17, 27800.23),
        "2026-09": (375, 52629.06, 2001.58, 23018.36), "2026-10": (182, 32459.64, 1235.92, 14054.86)}
# Singapore Shopify net_sales, cost_of_goods_sold: calibrates Shopify COGS to Unleashed cost-at-sale
sg_shop = {"2026-01": (54887.82, 17812.95), "2026-02": (57817.59, 19756.72), "2026-03": (107639.05, 41639.42),
           "2026-04": (96784.93, 37716.67), "2026-05": (49080.34, 17583.15), "2026-06": (65174.71, 26307.95),
           "2026-07": (71315.70, 33333.41), "2026-08": (76379.91, 36867.35), "2026-09": (89093.92, 40468.95),
           "2026-10": (45625.04, 19537.30)}
# Windsor spend, country = Australia (NZD)
google = {"2026-05": 4967.40, "2026-06": 7739.38, "2026-07": 9129.32, "2026-08": 9119.71, "2026-09": 9720.53,
          "2026-10": 7687.87}
facebook = {"2026-03": 1084.19, "2026-04": 3289.90, "2026-05": 9517.63, "2026-06": 7537.35, "2026-07": 7970.67,
            "2026-08": 10844.35, "2026-09": 10098.56, "2026-10": 5515.67}

sg_u = pd.read_csv(f"{R}/out/sg_pnl.csv", index_col=0).cogs_pct
t = pd.DataFrame(shop, index=["orders", "net_sales", "shipping", "shopify_cogs"]).T
t["revenue"] = t.net_sales + t.shipping
t["sg_adj"] = [sg_u[m] / (sg_shop[m][1] / sg_shop[m][0]) for m in months]
t["cogs_pct"] = t.shopify_cogs / t.net_sales * t.sg_adj
t["product_cost"] = t.net_sales * t.cogs_pct

# Courier: FedEx invoice lines (NZD, by ship date), Shopify "#123456" refs only (HF/EL/KN are another channel)
fx_cost, fx_n = defaultdict(float), defaultdict(int)
last_ship = dt.date(2000, 1, 1)
for r in csv.DictReader(open(FEDEX, encoding="utf-8-sig")):
    ref = r["Reference Notes Line 1"].strip()
    if r["Recipient Country/Territory"] != "AU" or r["Pay Type"] != "Bill_Sender_Prepaid" or not ref[1:2].isdigit():
        continue
    d = dt.datetime.strptime(r["Shipment Date (dd/mm/yyyy)"], "%d/%m/%Y").date()
    last_ship = max(last_ship, d)
    fx_cost[d.strftime("%Y-%m")] += float(r["Net Charge Billed Currency"] or 0)
    fx_n[d.strftime("%Y-%m")] += 1
# NZ Couriers 'International Courier' consignments (GoSweetSpot), by NZ created date
gss_cost, gss_n = defaultdict(float), defaultdict(int)
for s in json.load(open(f"{R}/data/gss_shipments.json")):
    if s.get("IsDeleted") or s.get("Carrier") != "International Courier":
        continue
    m = dt.datetime.fromisoformat(s["CreatedUtc"][:19]).replace(tzinfo=dt.timezone.utc).astimezone(NZT).strftime("%Y-%m")
    gss_cost[m] += s.get("TotalCost") or 0
    gss_n[m] += 1
gss_avg = sum(gss_cost.values()) / sum(gss_n.values())

rows = []
for m in months:
    o, n_f, n_g = t.orders[m], fx_n[m], gss_n[m]
    if n_f >= 50 and m != last_ship.strftime("%Y-%m"):
        rows.append((fx_cost[m], n_f, n_g, "FedEx invoices"))
    elif n_f >= 50:
        rows.append((o * fx_cost[m] / n_f, n_f, n_g, f"FedEx avg per parcel x orders (invoiced to {last_ship:%d %b})"))
    else:
        c = gss_cost[m] + fx_cost[m] + max(o - n_g - n_f, 0) * gss_avg
        rows.append((c, n_f, n_g, "NZ Couriers intl + avg for unmatched" if n_g >= 50 else "estimated at NZ Couriers intl avg"))
t["courier"], t["fedex_parcels"], t["gss_parcels"], t["courier_note"] = zip(*rows)
t["handling"] = t.orders * 3.0
t["google"] = [google.get(m, 0.0) for m in months]
t["facebook"] = [facebook.get(m, 0.0) for m in months]
t["net_profit"] = t.revenue - t.product_cost - t.courier - t.handling - t.google - t.facebook
t["margin"] = t.net_profit / t.revenue
pd.set_option("display.width", 250)
print(t[["orders", "revenue", "cogs_pct", "fedex_parcels", "gss_parcels", "courier", "net_profit", "margin",
         "courier_note"]].round(3).to_string())
print(f"NZ Couriers intl avg {gss_avg:.2f}/parcel; last FedEx ship date {last_ship}")
t.to_csv(OUT_CSV)


def money(v):
    return f"−{abs(v):,.0f}" if v else "0"


lines = ["| Month | Orders | Revenue | Product cost | Courier | Handling | Google | Facebook | **Net profit** | Margin |",
         "|---|---|---|---|---|---|---|---|---|---|"]
for m, r in t.iterrows():
    label = pd.Period(m, "M").strftime("%b %Y") + (" (to 17)" if m == "2026-10" else "")
    if r.courier_note != "FedEx invoices":
        label += "*"
    lines.append(f"| {label} | {r.orders:,.0f} | {r.revenue:,.0f} | {money(r.product_cost)} ({r.cogs_pct:.1%}) | "
                 f"{money(r.courier)} | {money(r.handling)} | {money(r.google)} | {money(r.facebook)} | "
                 f"**{r.net_profit:,.0f}** | {r.margin:.1%} |")
T = t.sum(numeric_only=True)
lines.append(f"| **Total** | **{T.orders:,.0f}** | **{T.revenue:,.0f}** | **{money(T.product_cost)} "
             f"({T.product_cost / T.net_sales:.1%})** | **{money(T.courier)}** | **{money(T.handling)}** | "
             f"**{money(T.google)}** | **{money(T.facebook)}** | **{T.net_profit:,.0f}** | **{T.net_profit / T.revenue:.1%}** |")
open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
