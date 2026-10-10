"""
Rolling-window gross margin by ship-to country: Shopify revenue x Unleashed cost.

Inputs (export from Shopify ShopifyQL - see README):
  --skus   CSV  shipping_country,product_variant_sku,net_items_sold,net_sales
  --daily  CSV  shipping_country,day,orders,net_sales

Revenue = Shopify net_sales (gross - discounts - returns; ex tax, ex shipping).
COGS    = net units x Unleashed CURRENT avg cost (fine for a recent window;
          use gm_history.py for anything historical).

    python scripts/margin_by_country.py --skus data/sku.csv --daily data/daily.csv \
        --label "3-9 Oct 2026" --png out/margin_by_country.png
"""

import argparse
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gogood.costs import current_costs, unit_cost  # noqa: E402

NZ_GST = 0.15
COUNTRIES = ["New Zealand", "Australia", "Singapore", "Hong Kong"]
COLORS = {"New Zealand": "#2a78d6", "Australia": "#eb6834", "Singapore": "#1baf7a", "Hong Kong": "#eda100"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

ap = argparse.ArgumentParser()
ap.add_argument("--skus", required=True)
ap.add_argument("--daily", required=True)
ap.add_argument("--label", default="")
ap.add_argument("--png")
a = ap.parse_args()

skus = pd.read_csv(a.skus, keep_default_na=False)
daily = pd.read_csv(a.daily, parse_dates=["day"])
costs = current_costs()

missing = sorted({s for s in skus.product_variant_sku if s and unit_cost(s, costs) == 0})
if missing:
    print("WARNING no Unleashed cost for:", missing)

skus["unit_cost"] = skus.product_variant_sku.map(lambda s: unit_cost(s, costs))
skus["cogs"] = skus.net_items_sold * skus.unit_cost
unattributed = skus[skus.product_variant_sku == ""].groupby("shipping_country").net_sales.sum()
if unattributed.abs().sum():
    print("Revenue with no SKU (kept, zero cost):", unattributed.round(2).to_dict())

t = skus.groupby("shipping_country").agg(units=("net_items_sold", "sum"), net=("net_sales", "sum"), cogs=("cogs", "sum"))
t["orders"] = daily.groupby("shipping_country").orders.sum()
t = t.reindex([c for c in COUNTRIES if c in t.index])
t["gst"] = 0.0
if "New Zealand" in t.index:  # exports to AU/SG/HK are zero-rated
    t.loc["New Zealand", "gst"] = t.loc["New Zealand", "net"] * NZ_GST
t["incl_gst"] = t.net + t.gst
t["gp"] = t.net - t.cogs
t["gm"] = t.gp / t.net
t["net_per_order"] = t.net / t.orders
t["gp_per_order"] = t.gp / t.orders
tot = t[["orders", "units", "net", "cogs", "gst", "incl_gst", "gp"]].sum()
tot["gm"], tot["net_per_order"], tot["gp_per_order"] = tot.gp / tot.net, tot.net / tot.orders, tot.gp / tot.orders
t.loc["Total"] = tot
pd.set_option("display.width", 200)
shown = t.round(2)
shown["gm"] = (t.gm * 100).round(1).astype(str) + "%"
print(shown.to_string())

if a.png:
    fig = plt.figure(figsize=(15, 9), facecolor="white")
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.05], hspace=0.42, wspace=0.28)
    money = FuncFormatter(lambda v, _: f"${v/1000:.1f}k".replace(".0k", "k") if v >= 1000 else f"${v:.0f}")
    order = [c for c in COUNTRIES if c in t.index]

    def tidy(ax):
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        for s in ["top", "right", "left"]:
            ax.spines[s].set_visible(False)

    for i, c in enumerate(order):
        ax = fig.add_subplot(gs[0, i])
        d = daily[daily.shipping_country == c].sort_values("day")
        y = d.net_sales.tolist()
        x = range(len(y))
        ax.fill_between(x, y, color=COLORS[c], alpha=0.12, lw=0)
        ax.plot(x, y, color=COLORS[c], lw=2, marker="o", ms=5, mec="white", mew=1.5)
        ax.set_xticks(list(x))
        ax.set_xticklabels(d.day.dt.day)
        ax.yaxis.set_major_formatter(money)
        ax.set_ylim(0, max(y) * 1.25)
        tidy(ax)
        r = t.loc[c]
        ax.set_title(f"{c}\n", loc="left", fontsize=12, fontweight="bold", color=INK, pad=2)
        ax.text(0, 1.02, f"${r.net:,.0f} net · {r.orders:.0f} orders · GM {r.gm:.1%}", transform=ax.transAxes, fontsize=9.5, color=INK2)
        j = y.index(max(y))
        ax.annotate(f"${max(y):,.0f}", (j, max(y)), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=9, color=INK)

    ax = fig.add_subplot(gs[1, :3])
    for i, c in enumerate(order):
        r = t.loc[c]
        ax.bar(i, r.net, 0.6, color=COLORS[c], alpha=0.25, lw=0)
        ax.bar(i, r.gp, 0.6, color=COLORS[c], lw=0)
        pad = t.loc[order].net.max() * 0.015
        ax.text(i, r.net + pad, f"GP ${r.gp:,.0f}", ha="center", va="bottom", fontsize=10, color=INK, fontweight="bold")
        ax.text(i, r.net + pad, f"Net ${r.net:,.0f}\n", ha="center", va="bottom", fontsize=9.5, color=INK2, linespacing=1.6)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order, fontsize=11, color=INK)
    ax.yaxis.set_major_formatter(money)
    ax.set_ylim(0, t.loc[order].net.max() * 1.15)
    tidy(ax)
    ax.set_title("Net sales ex GST (light) and gross profit (solid), NZD", loc="left", fontsize=12, fontweight="bold", color=INK)

    ax = fig.add_subplot(gs[1, 3])
    for i, c in enumerate(order):
        g = t.loc[c, "gm"] * 100
        ax.plot([0, g], [i, i], color=GRID, lw=2)
        ax.plot(g, i, "o", color=COLORS[c], ms=10, mec="white", mew=2)
        ax.text(g + 2, i, f"{g:.1f}%", va="center", fontsize=10, color=INK)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 75)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    tidy(ax)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_title("Gross margin %", loc="left", fontsize=12, fontweight="bold", color=INK)

    fig.suptitle(f"Go Good: Shopify sales by ship-to country {a.label}", x=0.125, ha="left", fontsize=15, fontweight="bold", color=INK, y=0.99)
    fig.text(0.125, 0.935, "Daily panels have independent y-scales. Net sales = Shopify gross − discounts − returns, ex GST & shipping. COGS = units × Unleashed avg landed cost.", fontsize=9, color=INK2)
    Path(a.png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.png, dpi=150, bbox_inches="tight", facecolor="white")
    print("saved", a.png)
