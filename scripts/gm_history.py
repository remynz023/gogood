"""
Historical weekly gross margin for one ship-to country, from Unleashed sales lines.

Cost basis = AverageLandedPriceAtTimeOfSale (cost when sold, NOT today's cost).
Revenue    = BCLineTotal (ex GST, after discounts). Charge lines (shipping) dropped.
Scope      = Shopify webstore orders only (OrderNumber 'go-good-nz#...'). MAIN also
             carries manual wholesale 'SO-' orders (~$0.5M/yr at ~24% GM) that
             would distort the weekly line.

Unleashed misses a few % of Shopify orders, but Shopify-only Unleashed revenue
reconciles to Shopify net_sales within ~1%/month for NZ, so the ratio is sound.

    python scripts/pull_sales_orders.py --warehouse MAIN --start 2025-10-01
    python scripts/gm_history.py --orders data/orders_MAIN_2025-10-01 \
        --country "New Zealand" --start 2025-10-10 --end 2026-10-09 --png out/nz_gm.png
"""

import argparse
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, MultipleLocator  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gogood.costs import parse_date  # noqa: E402
from gogood.unleashed import load_dir  # noqa: E402

SHOPIFY_PREFIX = "go-good-nz#"
INK, INK2, GRID, BLUE, BLUE_DARK = "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6", "#0d4fa3"

ap = argparse.ArgumentParser()
ap.add_argument("--orders", required=True, help="pull_sales_orders.py output dir")
ap.add_argument("--country", default="New Zealand", help="DeliveryCountry to keep")
ap.add_argument("--start", required=True)
ap.add_argument("--end", required=True, help="inclusive")
ap.add_argument("--png")
ap.add_argument("--csv")
a = ap.parse_args()

rows = []
for o in load_dir(a.orders):
    if (o.get("DeliveryCountry") or "").strip() != a.country:
        continue
    if not o["OrderNumber"].startswith(SHOPIFY_PREFIX) or o["OrderStatus"] in ("Deleted", "Cancelled"):
        continue
    d = parse_date(o["OrderDate"])
    for ln in o["SalesOrderLines"]:
        if ln["LineType"] == "Charge" or not ln["Product"]["ProductCode"]:
            continue
        rows.append((d, o["OrderNumber"], ln["Product"]["ProductCode"], ln["OrderQuantity"],
                     ln["BCLineTotal"], ln["AverageLandedPriceAtTimeOfSale"] or 0.0))

df = pd.DataFrame(rows, columns=["date", "order", "sku", "qty", "rev", "unit_cost"])
df = df[(df.date >= a.start) & (df.date <= a.end)]
df["cost"] = df.qty * df.unit_cost

wk = pd.Grouper(key="date", freq="W-SUN")
w = df.groupby(wk).agg(orders=("order", "nunique"), rev=("rev", "sum"), cost=("cost", "sum"))
w["days"] = df.groupby(wk).date.apply(lambda s: s.dt.normalize().nunique())
w["full_week"] = w.days == 7
w["gm"] = 1 - w.cost / w.rev
w["gm_4wk"] = 1 - w.cost.rolling(4).sum() / w.rev.rolling(4).sum()
avg = 1 - w.cost.sum() / w.rev.sum()

m = df.groupby(df.date.dt.to_period("M")).agg(orders=("order", "nunique"), rev=("rev", "sum"), cost=("cost", "sum"))
m["gm"] = 1 - m.cost / m.rev
print(m.round(3).to_string())
print(f"\nPeriod GM {avg:.1%} on ${w.rev.sum():,.0f} net sales")
if a.csv:
    w.to_csv(a.csv)

if a.png:
    plt.rcParams.update({"font.size": 10, "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID})
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(15, 8.5), sharex=True,
                                 gridspec_kw=dict(height_ratios=[2.2, 1], hspace=0.18), facecolor="white")
    x = w.index
    a1.axhline(avg * 100, color=INK2, lw=1, ls=(0, (4, 3)))
    a1.text(x[-1], avg * 100 + 0.4, f"period avg {avg:.1%}", color=INK2, fontsize=9, va="bottom", ha="right")
    a1.plot(x, w.gm * 100, color=BLUE, lw=1.6, alpha=0.55, marker="o", ms=4.5, mec="white", mew=1, label="Weekly GM %")
    part = w[~w.full_week]
    a1.plot(part.index, part.gm * 100, "o", ms=7, mfc="white", mec=BLUE, mew=1.5, ls="none")
    a1.plot(x, w.gm_4wk * 100, color=BLUE_DARK, lw=2.4, label="4-week rolling GM %")
    full = w[w.full_week].gm
    for d, v in pd.concat([full.nsmallest(2), full.nlargest(2)]).items():
        a1.annotate(f"{v:.1%}\nwk to {d:%d %b}", (d, v * 100), xytext=(0, -30 if v < avg else 10),
                    textcoords="offset points", ha="center", fontsize=8.5, color=INK)
    lo, hi = w.gm.min() * 100, w.gm.max() * 100
    a1.set_ylim(lo - 3, hi + 3)
    a1.yaxis.set_major_locator(MultipleLocator(2))
    a1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    a1.legend(loc="upper right", frameon=False, ncol=2)
    a1.set_title("Gross margin % (weekly, Mon–Sun)", loc="left", fontsize=12, fontweight="bold", color=INK)
    a2.bar(x, w.rev, width=5, color=BLUE, alpha=0.85, lw=0)
    a2.bar(part.index, part.rev, width=5, color="white", edgecolor=BLUE, hatch="///", lw=1)
    a2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
    a2.set_title("Net sales ex GST per week, NZD", loc="left", fontsize=12, fontweight="bold", color=INK)
    for ax in (a1, a2):
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        for s in ["top", "right", "left"]:
            ax.spines[s].set_visible(False)
    a2.xaxis.set_major_locator(mdates.MonthLocator())
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    fig.suptitle(f"Go Good: {a.country} Shopify gross margin, {a.start} to {a.end}", x=0.125, ha="left", y=0.985,
                 fontsize=15, fontweight="bold", color=INK)
    fig.text(0.125, 0.925, "GM = (net sales ex GST − COGS) ÷ net sales. COGS = Unleashed avg landed cost AT TIME OF SALE. "
             "Shopify orders only (wholesale SO- excluded); ex shipping. Hollow = partial week.", fontsize=9, color=INK2)
    Path(a.png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.png, dpi=150, bbox_inches="tight", facecolor="white")
    print("saved", a.png)
