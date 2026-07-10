# Alphago Fitness Online Orders Dashboard

This README is the runbook for regenerating the online orders dashboard.

Purpose: follow these steps to regenerate the cleaned dataset, HTML dashboard, and PDF report without repeating the analysis questions. If the dashboard needs to change later, update this README first, then regenerate the report from the updated instructions.

## Current Outputs

- Cleaned dataset: `combined_orders_24-26_cleaned.csv`
- Full same-column combined dataset: `combined_orders_24-26_same_columns.csv`
- HTML dashboard: `reports/orders_payment_dashboard.html`
- PDF dashboard: `reports/orders_payment_dashboard.pdf`

## Source Files

The original Shopify order exports are:

- `alphago_fitness/online/网店 25-26 财年orders_export_1.csv`
- `alphago_fitness/online/网店24-25财年orders_export_1.csv`

The two source files do not have exactly the same columns:

- FY25-26 source columns: 73
- FY24-25 source columns: 74
- Column only in FY24-25: `Billing Company`

When combining the files, use only the 73 shared columns and add a new column:

- `financial_year`

Use values:

- `25-26` for `网店 25-26 财年orders_export_1.csv`
- `24-25` for `网店24-25财年orders_export_1.csv`

Expected combined result:

- FY25-26 rows: 2,894
- FY24-25 rows: 2,103
- Combined rows: 4,997
- Combined columns before cleaning: 74

## Data Cleaning Steps

### 1. Combine The Two Source Files

Create `combined_orders_24-26_same_columns.csv`.

Rules:

- Read both CSV files.
- Use only shared columns.
- Exclude `Billing Company`.
- Add `financial_year` as the first column.
- Preserve all rows.

Note: the FY25-26 file may contain non-UTF-8 bytes in data rows. Read with UTF-8 and replace invalid characters rather than failing the merge.

### 2. Remove Customer-Sensitive Columns

Create `combined_orders_24-26_cleaned.csv` from `combined_orders_24-26_same_columns.csv`.

Remove these columns:

- `Shipping Name`
- `Phone`
- `Billing Phone`
- `Shipping Street`
- `Shipping Address1`
- `Shipping Address2`
- `Shipping Company`
- `Shipping Phone`
- `Payment ID`
- `Name`
- `Id`

Expected result after this step:

- Rows: 4,997
- Columns: 63

### 3. Remove All-Blank Columns

From `combined_orders_24-26_cleaned.csv`, remove columns where all rows are blank.

Remove these all-blank columns:

- `Tax 1 Name`
- `Tax 1 Value`
- `Tax 2 Name`
- `Tax 2 Value`
- `Tax 3 Name`
- `Tax 3 Value`
- `Tax 4 Name`
- `Tax 4 Value`
- `Tax 5 Name`
- `Tax 5 Value`
- `Receipt Number`

Expected final cleaned dataset:

- Rows: 4,997
- Columns: 52

## Analysis Rules

### Payment Amount Columns

Use these columns for payment totals:

- `Subtotal`
- `Shipping`
- `Total`

Treat blank values as zero.

### Amount Rows

Define an amount row as a row where at least one of these fields is populated:

- `Subtotal`
- `Shipping`
- `Total`

Blank `Financial Status` rows have blank amount fields, so they do not affect payment totals.

### Year-Over-Year Difference

All difference calculations use:

```text
FY25-26 minus FY24-25
```

### Shipping Province Rule

For province reporting:

1. Use `Shipping Province`.
2. If `Shipping Province` is blank, use `Billing Province`.
3. If both are blank, label the province as `(blank)`.

### Marketing Count Rule

Because customer-identifying fields were removed, the marketing count is by amount/order rows, not unique named customers.

Use:

- `Accepts Marketing = yes`
- `Accepts Marketing = no`

Ignore blank marketing rows in the marketing section because those are continuation rows with no payment amount.

## Report Tables To Generate For Validation

These tables are the source numbers for the dashboard. They do not need to appear as detail tables in the dashboard unless requested.

### Table 1: Summary By Financial Year And Payment Status

Group by:

- `financial_year`
- `Financial Status`

Calculate:

- row count
- amount row count
- sum of `Subtotal`
- sum of `Shipping`
- sum of `Total`

Current validated result:

| financial_year | Financial Status | rows | amount rows | subtotal | shipping | total |
|---|---:|---:|---:|---:|---:|---:|
| 24-25 | (blank) | 1139 | 0 | 0.00 | 0.00 | 0.00 |
| 24-25 | paid | 927 | 927 | 889,568.25 | 80,462.00 | 970,296.67 |
| 24-25 | partially_refunded | 18 | 18 | 30,907.56 | 3,386.99 | 34,574.18 |
| 24-25 | refunded | 19 | 19 | 18,490.47 | 2,474.22 | 20,964.69 |
| 25-26 | (blank) | 1878 | 0 | 0.00 | 0.00 | 0.00 |
| 25-26 | paid | 981 | 981 | 859,534.88 | 91,456.62 | 951,678.33 |
| 25-26 | partially_refunded | 14 | 14 | 21,957.18 | 2,631.96 | 24,619.36 |
| 25-26 | pending | 1 | 1 | 565.00 | 0.00 | 565.00 |
| 25-26 | refunded | 20 | 20 | 18,631.69 | 2,926.42 | 21,558.11 |

### Table 2: Total By Financial Year

| financial_year | rows | amount rows | subtotal | shipping | total |
|---|---:|---:|---:|---:|---:|
| 24-25 | 2103 | 964 | 938,966.28 | 86,323.21 | 1,025,835.54 |
| 25-26 | 2894 | 1016 | 900,688.75 | 97,015.00 | 998,420.80 |

### Table 3: Difference By Payment Status

| Financial Status | row diff | amount row diff | subtotal diff | shipping diff | total diff |
|---|---:|---:|---:|---:|---:|
| (blank) | 739 | 0 | 0.00 | 0.00 | 0.00 |
| paid | 54 | 54 | -30,033.37 | 10,994.62 | -18,618.34 |
| partially_refunded | -4 | -4 | -8,950.38 | -755.03 | -9,954.82 |
| pending | 1 | 1 | 565.00 | 0.00 | 565.00 |
| refunded | 1 | 1 | 141.22 | 452.20 | 593.42 |

### Table 4: Overall Difference

| Comparison | row diff | amount row diff | subtotal diff | shipping diff | total diff |
|---|---:|---:|---:|---:|---:|
| 25-26 minus 24-25 | 791 | 52 | -38,277.53 | 10,691.79 | -27,414.74 |

### Table 5: Paid Bills By Fulfillment Status

Filter:

- `Financial Status = paid`

Group by:

- `financial_year`
- `Fulfillment Status`

Current validated result:

| financial_year | Fulfillment Status | rows | amount rows | subtotal | shipping | total |
|---|---:|---:|---:|---:|---:|---:|
| 24-25 | fulfilled | 926 | 926 | 889,568.25 | 80,462.00 | 970,296.67 |
| 24-25 | unfulfilled | 1 | 1 | 0.00 | 0.00 | 0.00 |
| 25-26 | fulfilled | 952 | 952 | 824,759.58 | 89,941.19 | 915,387.60 |
| 25-26 | partial | 6 | 6 | 8,456.90 | 392.82 | 8,849.72 |
| 25-26 | unfulfilled | 23 | 23 | 26,318.40 | 1,122.61 | 27,441.01 |

### Table 6: Marketing Option Count

Use amount rows only.

Current validated result:

| financial_year | Accepts Marketing | amount rows |
|---|---:|---:|
| 24-25 | yes | 89 |
| 24-25 | no | 875 |
| 25-26 | yes | 267 |
| 25-26 | no | 749 |

### Table 7: Sales By Shipping Province

Use the shipping province fallback rule.

Current validated result:

| Province | FY24-25 total | FY25-26 total | Difference | FY24-25 amount rows | FY25-26 amount rows |
|---|---:|---:|---:|---:|---:|
| QLD | 667,209.78 | 620,053.38 | -47,156.40 | 606 | 603 |
| NSW | 202,643.52 | 213,979.13 | 11,335.61 | 201 | 225 |
| VIC | 77,215.39 | 81,106.19 | 3,890.80 | 93 | 105 |
| SA | 38,437.51 | 38,397.50 | -40.01 | 32 | 36 |
| ACT | 20,507.37 | 13,423.42 | -7,083.95 | 14 | 15 |
| WA | 9,118.38 | 12,494.96 | 3,376.58 | 8 | 17 |
| TAS | 6,134.21 | 8,477.24 | 2,343.03 | 7 | 7 |
| NT | 4,569.38 | 6,101.98 | 1,532.60 | 2 | 5 |
| (blank) | 0.00 | 3,689.00 | 3,689.00 | 1 | 2 |
| JP-28 | 0.00 | 698.00 | 698.00 | 0 | 1 |

## HTML Dashboard Layout

Generate `reports/orders_payment_dashboard.html`.

The dashboard should be a static offline HTML report using embedded CSS only. Do not require a server to view it.

Current sections:

1. Header
2. KPI cards
   - FY24-25 Total
   - FY25-26 Total
   - Total Change
   - Shipping Change
3. Year Comparison
   - Subtotal
   - Shipping
   - Total
4. Payment Status Breakdown
   - paid
   - partially_refunded
   - refunded
   - pending
5. Paid Bills Fulfillment Status
   - fulfilled
   - partial
   - unfulfilled
6. Marketing Option Count
   - accepts marketing: yes
   - accepts marketing: no
7. Sales By Shipping Province
   - use shipping province, fallback to billing province
8. Insight Summary

Do not include these removed sections unless requested again:

- `Where The Total Changed`
- detail table for total by financial year
- detail table for summary by financial year and payment status
- detail table for difference by payment status

## Dashboard Insights To Include

The current dashboard insight summary should include:

- Total payment decreased by $27,414.74 year over year, even though FY25-26 has 52 more amount rows.
- The decrease is mainly from paid orders, down $18,618.34, with paid fulfilled totals down $54,909.07.
- QLD remains the largest province but declined by $47,156.40, more than the overall total decline.
- NSW grew by $11,335.61, partly offsetting the QLD decline.
- FY25-26 has more paid orders that are partial or unfulfilled, representing $36,290.73 in paid total.
- Shipping increased by $10,691.79 while subtotal decreased by $38,277.53.
- Marketing opt-in amount rows increased from 89 to 267, while opt-out amount rows decreased from 875 to 749.
- Blank `Financial Status` rows have no payment amount and are excluded from payment-change interpretation.

## PDF Generation

Generate `reports/orders_payment_dashboard.pdf` from the HTML dashboard after every HTML update.

Current method:

- Use Playwright Chromium.
- Render the HTML file directly.
- Enable print backgrounds so colors are preserved.
- Use screen media to match the HTML styling.

The PDF should match the HTML dashboard format and colours as closely as possible.

If Playwright is missing, install it:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

Then regenerate the PDF from `reports/orders_payment_dashboard.html`.

## Unsuccessful Sales Dashboard

Generate this dashboard as a separate report:

- HTML dashboard: `reports/unpaid_unfulfilled_sales_dashboard.html`

This dashboard focuses on sales that may need operational follow-up because they are unpaid, refunded/partially refunded/pending, unfulfilled, partially fulfilled, or both non-paid and unfulfilled.

### Definition: Unsuccessful Sales

Use the term `Unsuccessful Sales`, not `Attention Sales`.

Define unsuccessful rows as:

```text
Financial Status != paid
OR
Fulfillment Status != fulfilled
```

This means the unsuccessful-sales total includes:

- non-paid sales
- unfulfilled or partially fulfilled sales
- the overlap where a row is both non-paid and unfulfilled

Do not double-count the overlap in the total unsuccessful-sales KPI.

### Line-Item Sales Amount

For this dashboard, calculate sales at line-item level:

```text
Lineitem quantity * Lineitem price
```

Use this formula for:

- unsuccessful sales
- non-paid sales
- unfulfilled sales
- both non-paid and unfulfilled sales
- total line-item sales
- unsuccessful sales rate
- top unsuccessful products

### Status Forward-Fill Rule

The cleaned Shopify export contains continuation line-item rows where order-level fields are blank.

Before filtering, forward-fill these order-level fields from the previous populated order row:

- `financial_year`
- `Financial Status`
- `Fulfillment Status`
- `Created at`
- `Accepts Marketing`
- `Shipping Province`
- `Billing Province`

This keeps each line item attached to the correct order status.

### KPI Cards

The current KPI cards are:

1. `Unsuccessful Sales`
   - value: `$137,285.29`
   - year-over-year change: `+45.6% YoY`
2. `Unsuccessful Rate`
   - value: `6.6%`
   - note: `5.4% to 7.7% by year`
3. `Non-Paid Sales`
   - value: `$102,231.01`
   - year-over-year change: `-16.5% YoY`
4. `Unfulfilled Sales`
   - value: `$77,420.54`
   - year-over-year change: `+177.9% YoY`
5. `Both Non-Paid And Unfulfilled`
   - value: `$42,366.26`
   - year-over-year change: `+8.5% YoY`

### Unsuccessful Sales Rate

Calculate the unsuccessful sales rate as:

```text
unsuccessful line-item sales / total line-item sales
```

Current validated result:

| financial_year | unsuccessful sales | total line-item sales | unsuccessful rate |
|---|---:|---:|---:|
| 24-25 | 55,886.82 | 1,028,186.37 | 5.4% |
| 25-26 | 81,398.47 | 1,063,666.22 | 7.7% |
| combined | 137,285.29 | 2,091,852.59 | 6.6% |

### Year Comparison Values

Current validated result:

| Metric | FY24-25 | FY25-26 | Difference | YoY change |
|---|---:|---:|---:|---:|
| Unsuccessful sales | 55,886.82 | 81,398.47 | 25,511.65 | 45.6% |
| Non-paid sales | 55,717.82 | 46,513.19 | -9,204.63 | -16.5% |
| Unfulfilled sales | 20,489.37 | 56,931.17 | 36,441.80 | 177.9% |
| Both non-paid and unfulfilled | 20,320.37 | 22,045.89 | 1,725.52 | 8.5% |

### Non-Paid Sales By Payment Status

Filter:

```text
Financial Status != paid
```

Group by:

- `financial_year`
- `Financial Status`

Current validated result:

| Financial Status | FY24-25 sales | FY25-26 sales | Difference |
|---|---:|---:|---:|
| partially_refunded | 36,621.35 | 23,915.50 | -12,705.85 |
| refunded | 19,096.47 | 22,032.69 | 2,936.22 |
| pending | 0.00 | 565.00 | 565.00 |

### Unfulfilled Sales By Fulfillment Status

Filter:

```text
Fulfillment Status != fulfilled
```

Group by:

- `financial_year`
- `Fulfillment Status`

Current validated result:

| Fulfillment Status | FY24-25 sales | FY25-26 sales | Difference |
|---|---:|---:|---:|
| unfulfilled | 20,489.37 | 48,454.27 | 27,964.90 |
| partial | 0.00 | 8,476.90 | 8,476.90 |

### Top Unsuccessful Products

Filter:

```text
Financial Status != paid
OR
Fulfillment Status != fulfilled
```

Group by:

- `Lineitem name`

Calculate:

- sum of `Lineitem quantity`
- sum of line-item sales

Current top products by unsuccessful sales:

| Product | quantity | unsuccessful sales |
|---|---:|---:|
| Multi-Functional Smith Machine JL006 | 6 | 10,979.07 |
| Alphago 5-In-1 Multi-Functional Smith Machine US586 | 2 | 7,897.44 |
| Ultimate Counterbalanced Smith Machine BL181 | 2 | 6,560.49 |
| Smith Machine JL006 + 2.2m Bar + Weights + Bench - 150kg Bumper Plates + Incline Bench TB-44 | 2 | 5,856.00 |
| Smith Machine BL181 All-in-One Premium Gym Set | 1 | 4,732.00 |

### Dashboard Sections

The unsuccessful-sales dashboard should include:

1. Header
2. KPI cards
3. Year Comparison
4. Non-Paid Sales By Payment Status
5. Unfulfilled Sales By Fulfillment Status
6. Top Unsuccessful Products
7. Insight Summary

### Insight Summary To Include

Current insights:

- Unsuccessful sales increased by `$25,511.65`, from `$55,886.82` in FY24-25 to `$81,398.47` in FY25-26, a `45.6%` increase.
- Unsuccessful sales represent `6.6%` of total line-item sales across both years, rising from `5.4%` in FY24-25 to `7.7%` in FY25-26.
- Non-paid line-item sales decreased by `$9,204.63`, or `16.5%`, but unfulfilled line-item sales increased by `$36,441.80`, or `177.9%`.
- FY25-26 has `185` unfulfilled or partially fulfilled line rows, compared with `40` in FY24-25.
- The overlap of non-paid and unfulfilled sales is `$42,366.26`, with FY25-26 slightly higher by `$1,725.52`.
- The highest-value unsuccessful product is `Multi-Functional Smith Machine JL006`, contributing `$10,979.07`.

## Regeneration Checklist

Follow this checklist whenever regenerating the report:

1. Confirm the two source CSV files exist in `alphago_fitness/online`.
2. Compare headers and confirm the only non-shared column is `Billing Company`.
3. Regenerate `combined_orders_24-26_same_columns.csv`.
4. Regenerate `combined_orders_24-26_cleaned.csv`.
5. Confirm final cleaned dataset has 4,997 rows and 52 columns.
6. Recalculate all validation tables listed in this README.
7. Update `reports/orders_payment_dashboard.html` using the current dashboard layout.
8. Regenerate `reports/orders_payment_dashboard.pdf` from the HTML.
9. Verify the HTML and PDF both exist.
10. Verify the removed sections are not present unless intentionally re-added.

For the unsuccessful-sales dashboard:

1. Start from `combined_orders_24-26_cleaned.csv`.
2. Forward-fill the order-level fields listed above.
3. Calculate line-item sales as `Lineitem quantity * Lineitem price`.
4. Recalculate unsuccessful, non-paid, unfulfilled, and overlap metrics.
5. Recalculate unsuccessful rate as unsuccessful sales divided by total line-item sales.
6. Update `reports/unpaid_unfulfilled_sales_dashboard.html`.
7. Verify the dashboard contains no `Attention Sales` wording.
8. Verify the dashboard includes `Unsuccessful Sales`, `Unsuccessful Rate`, YoY KPI changes, and the insight summary.

## Notes For Future Changes

When changing the dashboard, update this README first with:

- the new section name
- the grouping/filter logic
- the metrics to calculate
- whether the section should appear in HTML, PDF, or only validation notes
- any sections to remove
- any insight wording to add or replace

Then regenerate the dashboard from the updated README.
