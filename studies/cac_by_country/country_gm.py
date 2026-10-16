import json, sys
from collections import defaultdict
from pathlib import Path
repo, S = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(repo))
from gogood.costs import parse_date
from gogood.unleashed import load_dir
C = {"New Zealand":"NZ","Australia":"AU","Singapore":"SG","Hong Kong":"HK"}
orders = {}
for d in sorted((S/"ul").glob("orders_*")):
    for o in load_dir(d):
        if not o["OrderNumber"].startswith("go-good-nz#") or o["OrderStatus"] in ("Deleted","Cancelled"):
            continue
        rev = cost = 0.0
        for ln in o["SalesOrderLines"]:
            if ln["LineType"] == "Charge" or not (ln.get("Product") or {}).get("ProductCode"):
                continue
            rev += ln["BCLineTotal"] or 0.0
            cost += (ln["OrderQuantity"] or 0) * (ln.get("AverageLandedPriceAtTimeOfSale") or 0.0)
        if rev <= 0: continue
        num = int("".join(ch for ch in o["OrderNumber"].split("#")[1] if ch.isdigit()) or 0)
        orders[o["OrderNumber"]] = (parse_date(o["OrderDate"]), num, o["Customer"]["CustomerCode"], (o.get("DeliveryCountry") or "").strip(), rev, cost)
first = {}
for on, (dt, num, cu, ctry, r, c) in orders.items():
    if cu not in first or (dt, num) < first[cu][:2]:
        first[cu] = (dt, num, on, ctry)
def q(dt):
    fy = dt.year + (1 if dt.month >= 4 else 0)
    return f"FY{str(fy)[2:]} Q{(dt.month + 8) % 12 // 3 + 1}", dt.year*12 + (dt.month-1) - ((dt.month - 4) % 3)
fo = defaultdict(lambda: [0.0, 0.0]); co = defaultdict(lambda: [0.0, 0.0])
for on, (dt, num, cu, ctry, r, c) in orders.items():
    fdt, _, fon, fctry = first[cu]
    if fctry not in C: continue
    lab, qstart = q(fdt)
    k = (lab, C[fctry])
    if on == fon:
        fo[k][0] += r; fo[k][1] += c
    if dt.year*12 + dt.month - 1 < qstart + 13:
        co[k][0] += r; co[k][1] += c
res = {f"{a}|{b}": {"gm_first": (1 - v[1]/v[0]) if v[0] else None,
                    "gm_12m": (1 - co[(a,b)][1]/co[(a,b)][0]) if co[(a,b)][0] else None}
       for (a,b), v in fo.items()}
(S/"country_gm.json").write_text(json.dumps(res, indent=0))
for k in sorted(res): print(k, {x: round(y*100,1) if y else None for x,y in res[k].items()})
