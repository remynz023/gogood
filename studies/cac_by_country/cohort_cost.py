"""CAC vs gross profit at first sale and at 12 months, on Unleashed cost-at-sale.

Margin % comes from Unleashed (cost stamped on each line when sold, revenue ex GST).
Revenue per customer comes from Shopify (complete; Unleashed drops some orders).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

repo, scratch = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(repo))
from gogood.costs import parse_date  # noqa: E402
from gogood.unleashed import load_dir  # noqa: E402

ref = json.loads((scratch / "shopify_ref.json").read_text())

orders = {}
lines_total = lines_nocost = 0
for d in sorted((scratch / "ul").glob("orders_*")):
    for o in load_dir(d):
        if not o["OrderNumber"].startswith("go-good-nz#") or o["OrderStatus"] in ("Deleted", "Cancelled"):
            continue
        rev = cost = 0.0
        for ln in o["SalesOrderLines"]:
            if ln["LineType"] == "Charge" or not (ln.get("Product") or {}).get("ProductCode"):
                continue
            lines_total += 1
            uc = ln.get("AverageLandedPriceAtTimeOfSale")
            if not uc:
                lines_nocost += 1
                uc = 0.0
            rev += ln["BCLineTotal"] or 0.0
            cost += (ln["OrderQuantity"] or 0) * uc
        if rev <= 0:
            continue
        digits = "".join(ch for ch in o["OrderNumber"].split("#")[1] if ch.isdigit())
        num = int(digits or 0)
        orders[o["OrderNumber"]] = (parse_date(o["OrderDate"]), num, o["Customer"]["CustomerCode"], rev, cost)

first = {}
for on, (dt, num, cust, rev, cost) in orders.items():
    if cust not in first or (dt, num) < first[cust][:2]:
        first[cust] = (dt, num, on)

def mkey(dt):
    return f"{dt.year}-{dt.month:02d}"

def madd(m, k):
    y, mo = map(int, m.split("-"))
    t = y * 12 + mo - 1 + k
    return f"{t // 12}-{t % 12 + 1:02d}"

fo = defaultdict(lambda: [0, 0.0, 0.0])        # first orders by month: n, rev, cost
co = defaultdict(lambda: [0.0, 0.0])           # cohort 12m window: rev, cost
for on, (dt, num, cust, rev, cost) in orders.items():
    f_dt, f_num, f_on = first[cust]
    c = mkey(f_dt)
    if on == f_on:
        fo[c][0] += 1; fo[c][1] += rev; fo[c][2] += cost
    if mkey(dt) <= madd(c, 11):
        co[c][0] += rev; co[c][1] += cost

print(f"Unleashed webstore orders: {len(orders):,}; lines without cost at sale: {lines_nocost}/{lines_total}")
out = []
hdr = "month|shop_new|ul_first|CAC|AOV|GM_first|GP_first|GP_first_shopify|GM_12m|GP_12m|basis"
print(hdr)
for m in sorted(ref["first_orders"]):
    n_shop, net_first = ref["first_orders"][m]
    cac = ref["spend"][m] / n_shop
    aov = net_first / n_shop
    n_ul, r1, c1 = fo.get(m, [0, 0, 0])
    gm1 = 1 - c1 / r1 if r1 else None
    gp1 = aov * gm1 if gm1 is not None else None
    r12, c12 = co.get(m, [0, 0])
    gm12 = 1 - c12 / r12 if r12 else None
    if m in ref["cohort_12m_net"]:
        size, m0, rest = ref["cohort_12m_net"][m]; net12 = (m0 + rest) / size; basis = "12m"
    else:
        size, tot = ref["cohort_todate_net"][m]; net12 = tot / size
        y, mo = map(int, m.split("-")); basis = f"{(2026 - y) * 12 + 10 - mo + 1}mo"
    gp12 = net12 * gm12 if gm12 is not None else None
    row = dict(month=m, shop_new=n_shop, ul_first=n_ul, cac=cac, aov=aov, gm_first=gm1, gp_first=gp1,
               gm_12m=gm12, net_12m=net12, gp_12m=gp12, basis=basis)
    out.append(row)
    f = lambda v, p=0: "-" if v is None else f"{v:.{p}f}"
    print(f"{m}|{n_shop}|{n_ul}|{f(cac)}|{f(aov)}|{f(gm1*100 if gm1 else None,1)}%|{f(gp1)}|-|{f(gm12*100 if gm12 else None,1)}%|{f(gp12)}|{basis}")
(scratch / "cohort_cost_out.json").write_text(json.dumps(out, indent=1))
