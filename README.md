# Go Good analytics

Sales and margin analysis for **Go Good** (gogood.co.nz): Shopify for sales, Unleashed for inventory and cost.
Kept separate from Axi work.

## Setup

```
pip install -r requirements.txt
cp .env.example .env      # fill in UNLEASHED_API_ID / UNLEASHED_API_KEY
```

`.env` and `data/` / `out/` are git-ignored: order data contains customer names and addresses.

## Margin study

### 1. Rolling-window margin by country: `scripts/margin_by_country.py`

Shopify revenue × Unleashed **current** average cost. Good for the last few weeks.

Export two CSVs from Shopify (Analytics → ShopifyQL, or the Shopify MCP `run-analytics-query`):

```sql
-- data/sku.csv  (shipping_country,product_variant_sku,net_items_sold,net_sales)
FROM sales SHOW net_items_sold, net_sales
WHERE shipping_country IN ('New Zealand','Australia','Singapore','Hong Kong')
GROUP BY shipping_country, product_variant_sku
SINCE 2026-10-03 UNTIL 2026-10-09

-- data/daily.csv  (shipping_country,day,orders,net_sales)
FROM sales SHOW orders, net_sales
WHERE shipping_country IN ('New Zealand','Australia','Singapore','Hong Kong')
GROUP BY shipping_country, day
SINCE 2026-10-03 UNTIL 2026-10-09
```

```
python scripts/margin_by_country.py --skus data/sku.csv --daily data/daily.csv \
    --label "3–9 Oct 2026" --png out/margin_by_country.png
```

### 2. Historical margin: `scripts/gm_history.py`

Uses the cost Unleashed stamped on each order line **at the time of sale**, so past periods aren't restated at today's cost.

```
python scripts/pull_sales_orders.py --warehouse MAIN --start 2025-10-01     # ~25 min for 12 months
python scripts/gm_history.py --orders data/orders_MAIN_2025-10-01 --country "New Zealand" \
    --start 2025-10-10 --end 2026-10-09 --png out/nz_gm_365d.png --csv out/nz_gm_weekly.csv
```

## Definitions

| Term | Meaning |
|---|---|
| Net sales | Shopify gross − discounts − returns; **ex GST, ex shipping**. Unleashed `BCLineTotal` is on the same basis. |
| GST | NZ only, 15%. Exports (AU/SG/HK) are zero-rated. Shopify `taxes` = 15% × (net sales + shipping). |
| COGS | units × Unleashed average landed cost (purchase/manufacture). Excludes freight to offshore warehouses, 3PL pick/pack, payment fees, marketing. |
| GM % | (net sales − COGS) ÷ net sales |

## Gotchas

- **Unleashed avg cost is global**: identical across MAIN / AUS / HONG KONG / SINGAPORE. Offshore margins are overstated by inter-warehouse freight.
- **Shopify → Unleashed sync drops orders**: about 13% store-wide in Oct 2026 (49 of 137 SG orders in one week). Use Shopify for volumes in short windows. For NZ history, Unleashed Shopify-only revenue reconciles to Shopify within about 1% per month.
- **Wholesale orders** in MAIN (`SO-000…`, not `go-good-nz#…`) run at ~24% GM. Exclude them from webstore margin.
- **Bundles** are comma-coded SKUs (`WPI-C05,SHAK-SKY`). Cost = sum of the parts that exist as products; colour tags (`PLA-PINK`) aren't products. This reconciles exactly to Unleashed's own bundle cost.
- **Signing**: Unleashed signs the *raw* unencoded query. Parameters with spaces (`HONG KONG`) 403 if you sign the URL-encoded string.
- `SalesOrders` at `pageSize=1000` times out; use 200.
- Shopify also has its own COGS (`FROM sales SHOW cost_of_goods_sold, gross_margin`) from variant unit cost. It differs from Unleashed by ±2–3 pts, which suggests Shopify product costs are stale.

## Findings log

- **3–9 Oct 2026 by country (current cost):** NZ 42.5%, AU 60.7%, HK 59.3%, SG 57.8%; blended 47.9%. NZ prices are about 30% lower than offshore (WPI-U01 ≈ $85 ex GST in NZ vs $122–130).
- **NZ, last 365 days (cost at sale):** 44.2% average. The 45–49% of Oct–Feb fell to about 40% in Mar–Apr on rising whey isolate cost. A May price rise of about 15–23% lifted it to about 50%. Cost increases since July (WPC-C01 +63% year on year, WPI-U01 +41%) took it back to about 42%.
