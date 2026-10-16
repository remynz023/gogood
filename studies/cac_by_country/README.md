# CAC by country (work in progress, 16 Oct 2026)

How achievable the Head of Growth bonus is. The incentive letter covers the first 12 months, FY ending 31 Mar 2027. The question here: is paid acquisition still buying profitable customers, market by market?

Status: **paused, not finished**. See [Open items](#open-items).

Dashboard (Shopify live + ad spend): https://claude.ai/artifact/Uw1kfcwUszXxfdYJzNoJUL

## Bonus scorecard (from the letter)

Up to $40k, discretionary.

| Weight | Measure | Reference |
|---|---|---|
| 30% | Shopify DTC revenue | $7.8M objective / $8.4M stretch |
| 25% | Content | |
| 20% | Paid acquisition: verified new-customer CAC | ≤ $30 quarterly, ≤ $27 stretch |
| 15% | Retention / Klaviyo | targets set from a verified baseline |
| 10% | Forecasting / reporting | |

Guardrails: CAC ≤ $30, first-order contribution ≥ $8, no heavy discounting.

## Method

- **New customers, AOV, cohort revenue:** Shopify (`new_or_returning_customer`, `customer_cohort_month`, `shipping_country`). `net_sales` is already ex-GST. Snapshots are in `inputs/shopify_ref.json` and inside `country_table.py`.
- **Margin:** Unleashed cost at time of sale (`AverageLandedPriceAtTimeOfSale`) on webstore orders (`go-good-nz#…`) only. Wholesale `SO-` orders are excluded. Unleashed drops about 13% of orders, so it's used for **margin %** only. Revenue comes from Shopify. Country is `DeliveryCountry`; the customer is `CustomerCode`, which is the Shopify customer ID.
- **Ad spend:** Meta (account 2622793234649426) + Google Ads (642-297-3348) via Windsor, by `year_month`. Country is Meta `country` / Google `geo_target_country`.
- **Net** = gross profit − CAC, per new customer. "Net at 12 months" = cohort gross profit over 12 months (later cohorts to date) − CAC.
- **Not deducted yet:** shipping, pick/pack, payment fees, offshore freight. Offshore margins are overstated by freight.

## Results (per new customer, NZD ex-GST)

### New Zealand
| Quarter | Ad spend | New | AOV | CAC | Net at first sale | Net at 12 months |
|---|---|---|---|---|---|---|
| FY25 Q1 (Apr–Jun 2024) | $45,003 | 1,117 | $53 | $40 | −$10 | +$38 |
| FY25 Q2 | $61,910 | 2,290 | $56 | $27 | +$3 | +$41 |
| FY25 Q3 | $60,442 | 1,918 | $58 | $32 | −$1 | +$33 |
| FY25 Q4 | $63,727 | 2,178 | $60 | $29 | +$2 | +$37 |
| FY26 Q1 (Apr–Jun 2025) | $95,731 | 1,987 | $59 | $48 | −$18 | +$29 |
| FY26 Q2 | $141,314 | 2,507 | $63 | $56 | −$26 | +$21 |
| FY26 Q3 | $142,998 | 1,841 | $71 | $78 | −$43 | +$3 (~11 mo) |
| FY26 Q4 | $130,882 | 2,354 | $68 | $56 | −$24 | +$11 (~8 mo) |
| FY27 Q1 (Apr–Jun 2026) | $144,726 | 3,033 | $68 | $48 | −$15 | +$7 (~5 mo) |
| FY27 Q2 | $188,442 | 3,723 | $66 | $51 | −$20 | −$11 (~2 mo) |

### Australia
| Quarter | Ad spend | New | AOV | CAC | Net at first sale | Net at 12 months |
|---|---|---|---|---|---|---|
| FY25 Q1–FY26 Q2 | $0 | 131–185/qtr | $86–106 | $0 | +$55 to +$64 | +$106 to +$135 |
| FY26 Q3 | $4,731 | 160 | $115 | $30 | +$34 | +$108 (~11 mo) |
| FY26 Q4 | $1,081 | 147 | $116 | $7 | +$59 | +$108 (~8 mo) |
| FY27 Q1 | $32,877 | 429 | $120 | $77 | −$4 | +$38 (~5 mo) |
| FY27 Q2 | $56,684 | 653 | $125 | $87 | −$15 | −$1 (~2 mo) |

### Singapore
| Quarter | Ad spend | New | AOV | CAC | Net at first sale | Net at 12 months |
|---|---|---|---|---|---|---|
| FY25 | $0 | 1,409 | $84 | $0 | +$53 | +$91 |
| FY26 Q2 | $6,515 | 394 | $123 | $17 | +$59 | +$211 |
| FY26 Q3 | $31,574 | 701 | $138 | $45 | +$37 | +$155 (~11 mo) |
| FY26 Q4 | $43,945 | 673 | $122 | $65 | +$8 | +$86 (~8 mo) |
| FY27 Q1 | $31,723 | 483 | $127 | $66 | +$13 | +$55 (~5 mo) |
| FY27 Q2 | $28,958 | 575 | $138 | $50 | +$26 | +$51 (~2 mo) |

### Hong Kong
| Quarter | Ad spend | New | AOV | CAC | Net at first sale | Net at 12 months |
|---|---|---|---|---|---|---|
| FY25 | $0 | 755 | $89 | $0 | +$60 | +$107 |
| FY26 Q2 | $2,286 | 152 | $112 | $15 | +$50 | +$161 |
| FY26 Q3 | $12,312 | 234 | $113 | $53 | +$14 | +$101 (~11 mo) |
| FY26 Q4 | $22,098 | 235 | $110 | $94 | −$26 | +$51 (~8 mo) |
| FY27 Q1 | $27,454 | 271 | $116 | $101 | −$33 | +$4 (~5 mo) |
| FY27 Q2 | $26,171 | 288 | $140 | $91 | −$17 | −$1 (~2 mo) |

SG and HK had no new customers in Apr–Jun 2025 (FY26 Q1).

### All countries
| Period | Ad spend | AOV | CAC | Net at first sale | Net at 12 months |
|---|---|---|---|---|---|
| FY25 (Apr 2024–Mar 2025) | $234,300 | $66 | $22 | +$14 | +$52 |
| Apr–Sep 2025 | $247,023 | $70 | $46 | −$9 | +$48 |
| FY27 so far (Apr–Sep 2026) | $545,579 | $80 | $57 | −$13 | +$6 (to date) |

The "All" spend is total account spend, which includes spend outside the four countries (e.g. about $4.8k of Meta to the US in Sep 2026). Country rows exclude it, so they add up to about $6–7k less than the total in Jul–Sep 2026.

## Takeaways so far

- **CAC is well above the $30 guardrail everywhere except possibly SG.** Blended FY27 CAC is about $57. First orders lose money in NZ, AU and HK.
- **NZ:** spend is about 3× FY25, new customers about 1.7×. CAC has nearly doubled.
- **AU:** spend went from near zero to $57k a quarter. New customers tripled, but CAC is $87.
- **HK:** spend doubled with almost no growth in customers. It's the least efficient market.
- **SG:** spend is flat to down and the first sale is still profitable. It's the most efficient market.
- **Revenue:** FY27 YTD (1 Apr–15 Oct) total sales $3.14M (net $2.77M), about 2.2× year on year. The projection is $7.1–7.6M. $7.8M needs 2.26× on the remaining months; $8.4M needs 2.55×.
- **Discounting** has risen to 13–17% of gross, which works against the "no heavy discounting" guardrail.
- **Repeat rate:** 12-month repeat is about 33% for FY25 cohorts and about 42% for Apr–Oct 2025 cohorts, so retention is improving.

## Open items

1. **FY25 spend mismatch.** The country-level NZ FY25 sum (about $231k) disagrees with the $338,632 figure quoted earlier. The monthly account total is $234,300 (used above). Recompute before quoting.
2. Deduct per-order shipping, pick/pack, payment fees and offshore freight (the user may supply per-order costs).
3. AU FY26 Q1 and HK FY25 Q4 margins use a country-average fallback (flagged `*` by `country_table.py`).
4. Add the country/Unleashed view to the dashboard.
5. Refresh the later cohorts as they mature.

## Re-running

```
# 1. Pull Unleashed sales orders (all warehouses) from 2024-04-01 into inputs/ul/orders_<WH>/
#    (inputs/ul/ is git-ignored: it holds customer names and addresses)
python scripts/pull_sales_orders.py --warehouse MAIN --start 2024-04-01 --out studies/cac_by_country/inputs/ul/orders_MAIN
#    ...repeat for AUS, SINGAPORE, HONG_KONG

# 2. Margin by country and quarter -> inputs/country_gm.json
python studies/cac_by_country/country_gm.py . studies/cac_by_country/inputs

# 3. Country table (spend, CAC, AOV, net at first sale / 12 months)
python studies/cac_by_country/country_table.py studies/cac_by_country/inputs

# Monthly blended version -> inputs/cohort_cost_out.json
python studies/cac_by_country/cohort_cost.py . studies/cac_by_country/inputs

# FY27 revenue projection vs $7.8M / $8.4M, and monthly CAC
python studies/cac_by_country/revenue_projection.py
```

Shopify and ad-spend numbers are hard-coded snapshots taken on 16 Oct 2026, in `country_table.py`, `revenue_projection.py` and `inputs/*.json`. Re-pull them via the Shopify and Windsor MCPs to refresh.
