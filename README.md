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

### 3. Market net profit (P&L): `scripts/market_pnl.py`

Monthly net profit for one ship-to market in NZD ex GST: revenue less product cost, courier, handling and ads.

| Line | Source | Notes |
|---|---|---|
| Revenue | Shopify net sales + shipping charged | ex GST |
| Product cost | Shopify net sales × Unleashed COGS % at time of sale | Shopify (`go-good-nz#`) orders only |
| Courier, SG | EasyParcel price per Shopify order, matched on tracking number | SGD → NZD at the monthly ECB average. 96–99% of SG orders match from June 2026. Months with fewer than 50 matches use the average matched cost (~SGD 3.67). |
| Courier, NZ | NZ Couriers `TotalCost` per consignment (GoSweetSpot), by created date | International Courier parcels excluded |
| Courier, AU | FedEx invoice export (`Net Charge Billed Currency`, NZD) by ship date, from June 2026. Before that, NZ Couriers *International Courier* consignments (GSS) | Shopify `#123456` references only; HF/EL/KN references are another channel. Months with fewer than 50 parcels use the NZ Couriers average (NZ$24.75 per parcel). |
| Handling | flat per order | SG: SGD 5 fulfilment. NZ and AU: NZ$3 pick. |
| Ads | Google + Facebook spend targeted at the country (Windsor) | NZD |

The total excludes payment fees, apps, rent and staff.

Inputs, saved in `data/`:

```sql
-- data/shopify_sg_monthly.csv  (month,orders,net_sales,shipping_charges)
FROM sales SHOW orders, net_sales, shipping_charges
WHERE shipping_country = 'Singapore' TIMESERIES month SINCE 2026-01-01 UNTIL 2026-10-17
```

- `data/ads_sg_monthly.csv` has the columns `month,google,facebook`. It comes from the Windsor `google_ads` and `facebook` connectors, with `spend` filtered on `country`.
- `data/shopify_orders.jsonl` is a Shopify bulk export. Run `bulkOperationRunQuery` on `orders { name createdAt cancelledAt shippingAddress { countryCodeV2 } fulfillments { trackingInfo { number company } } }`, then download the JSONL from the `url` that `bulkOperation(id)` returns.
- Courier data comes from `scripts/pull_couriers.py`.

```
python -m gogood.easyparcel login                      # once; tokens -> data/easyparcel_tokens.json
python scripts/pull_couriers.py easyparcel --start 2026-05-01 --end 2026-10-19
python scripts/pull_couriers.py gss --start 2025-12-15 --end 2026-10-20
python scripts/pull_sales_orders.py --warehouse SINGAPORE --start 2026-01-01
python scripts/pull_sales_orders.py --warehouse MAIN --start 2026-01-01

python scripts/market_pnl.py --market Singapore --orders data/orders_SINGAPORE_2026-01-01 \
    --shopify-monthly data/shopify_sg_monthly.csv --ads data/ads_sg_monthly.csv \
    --easyparcel data/easyparcel_shipments.json --shopify-orders data/shopify_orders.jsonl \
    --handling 5 --handling-ccy SGD --start 2026-01-01 --end 2026-10-17 --csv out/sg_pnl.csv --md reports/sg_pnl.md
python scripts/market_pnl.py --market "New Zealand" --orders data/orders_MAIN_2026-01-01 \
    --shopify-monthly data/shopify_nz_monthly.csv --ads data/ads_nz_monthly.csv \
    --gss data/gss_shipments.json --handling 3 --start 2026-01-01 --end 2026-10-17 \
    --csv out/nz_pnl.csv --md reports/nz_pnl.md
```

**Australia** (`scripts/au_pnl.py`) is a stop-gap until the Unleashed `AUS` warehouse orders are pulled. The Shopify and Windsor monthly figures are hard-coded in the script. Product cost is Shopify `cost_of_goods_sold`, scaled each month by SG's ratio of Unleashed cost-at-sale to Shopify COGS. AU ships from NZ, so handling is NZ$3 per order.

```
python scripts/au_pnl.py . "FedEx AU.csv" out/au_pnl.csv reports/au_pnl.md
```

### 4. Product net margins: `scripts/product_net_margin.py`

This gives the margin per SKU, with bundles as sold. Price and cost-at-sale come from Unleashed lines. "Cost now" is the current average cost.

**Net margin** = GM at current cost − the market's variable selling cost %, where variable selling cost = (courier + handling + ads) ÷ revenue over the same months, taken from `market_pnl.py --csv`. The variable cost is spread over products in proportion to revenue.

```
python scripts/product_net_margin.py --orders data/orders_SINGAPORE_2026-01-01 --market Singapore \
    --pnl out/sg_pnl.csv --start 2026-07-01 --end 2026-10-17 --top 25 --md reports/sg_products.md
python scripts/product_net_margin.py --orders data/orders_MAIN_2026-01-01 --market "New Zealand" \
    --pnl out/nz_pnl.csv --start 2026-07-01 --end 2026-10-17 --top 25 --md reports/nz_products.md
```

`reports/` holds the committed summary tables. They contain aggregates only, with no customer data.

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
- **Market net profit, Jan–17 Oct 2026** (`reports/sg_pnl.md`, `reports/nz_pnl.md`):
  - **Singapore:** NZ$262.6k on NZ$734.6k revenue, a **35.7%** margin. January to April (\*) predate EasyParcel, so courier cost is the matched average of SGD 3.67 per order.
  - **New Zealand:** NZ$361.9k on NZ$2.41m, a **15.0%** margin.
  - **Australia** (`reports/au_pnl.md`, estimated): NZ$46.4k on NZ$405.6k, an **11.4%** margin. Jan–Apr made 29–39% with little or no ads. Once Google and Facebook spend reached NZ$15–20k a month from May, the margin fell to around 0%, and it has been slightly negative since September. Ads are about 34% of revenue. FedEx costs about NZ$29–32 per order, against NZ$24.75 on NZ Couriers. Starred months are estimates: Jan, Feb, Apr and May courier (no parcel cost found, and May mostly went NZ Post direct) and October (FedEx invoiced to 13 Oct). Product cost is SG-calibrated Shopify COGS.
  - **What drives the gap:** product cost is 56% of sales in NZ against 42% in SG. Variable selling cost is 31% of revenue in NZ against 21% in SG.
  - **NZ, June to September:** NZ Facebook spend went from NZ$26k a month to NZ$44–45k and the margin fell from 19.8% to 11–12%. October (about NZ$1.5k a day of Facebook) is back at 17.5%.
- **Product net margins, 1 Jul–17 Oct 2026** (`reports/*_products.md`):
  - **NZ (net margin 9.3%):** the 1kg Whey Isolates make around break-even after courier, pick and ads: WPI-V01 −4.3%, WPI-U01 −1.8%, WPI-C01 +2.3%. The 2kg WPI bundle (WPI-U02) is −17.6%. Creatine (~54%) and Plant Protein (31–38%) carry the margin. NZ prices for the same SKU are about 25% below SG.
  - **SG (net margin 31.8%):** WPI 1kg 25–30%, Plant 49–55%, samples 42–58%.
- **Wholesale:** `SO-` orders in MAIN run at 23–53 a month, NZ$26–83k, with 11–34% GM. A value cut-off (e.g. ≥ NZ$1,000) misses most of them. Use the order-number prefix.
