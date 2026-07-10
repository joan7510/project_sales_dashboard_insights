# Unpaid Deal Dashboard

This folder contains the code and instructions to regenerate the unpaid/unfulfilled sales dashboard without committing source data or generated dashboard files.

## Purpose

Generate insights for line items that may need operational follow-up:

- unpaid, refunded, partially refunded, or pending sales
- unfulfilled or partially fulfilled sales
- rows that are both non-paid and unfulfilled

The dashboard term is:

```text
Unsuccessful Sales
```

Do not use the older label `Attention Sales`.

## Required Input

The script expects the cleaned order dataset:

```text
combined_orders_24-26_cleaned.csv
```

This file is intentionally ignored by Git and should not be uploaded to GitHub.

## Calculation Rules

Line-item sales amount:

```text
Lineitem quantity * Lineitem price
```

Unsuccessful sales:

```text
Financial Status != paid
OR
Fulfillment Status != fulfilled
```

Unsuccessful rate:

```text
unsuccessful line-item sales / total line-item sales
```

Before filtering, the script forward-fills order-level fields onto continuation line-item rows:

- `financial_year`
- `Financial Status`
- `Fulfillment Status`
- `Created at`
- `Accepts Marketing`
- `Shipping Province`
- `Billing Province`

## Generate The Dashboard

From the project root:

```bash
python3 unpaid_deal_dashboard/generate_unpaid_deal_dashboard.py
```

Default input:

```text
combined_orders_24-26_cleaned.csv
```

Default output:

```text
reports/unpaid_unfulfilled_sales_dashboard.html
```

Custom paths:

```bash
python3 unpaid_deal_dashboard/generate_unpaid_deal_dashboard.py \
  --input combined_orders_24-26_cleaned.csv \
  --output reports/unpaid_unfulfilled_sales_dashboard.html
```

## Current Expected Sections

The generated HTML dashboard includes:

1. Header
2. KPI cards
   - `Unsuccessful Sales`
   - `Unsuccessful Rate`
   - `Non-Paid Sales`
   - `Unfulfilled Sales`
   - `Both Non-Paid And Unfulfilled`
3. Year Comparison
4. Non-Paid Sales By Payment Status
5. Unfulfilled Sales By Fulfillment Status
6. Top Unsuccessful Products
7. Insight Summary

## Current Validated KPI Values

Using the current cleaned dataset:

```text
Unsuccessful Sales: $137,285.29
Unsuccessful Rate: 6.6%
Non-Paid Sales: $102,231.01
Unfulfilled Sales: $77,420.54
Both Non-Paid And Unfulfilled: $42,366.26
```

Year-over-year KPI changes:

```text
Unsuccessful Sales: +45.6%
Non-Paid Sales: -16.5%
Unfulfilled Sales: +177.9%
Both Non-Paid And Unfulfilled: +8.5%
```

## GitHub Safety

This folder should upload only code and documentation.

Do not upload:

- source CSV files
- cleaned CSV files
- generated HTML dashboards
- generated PDF dashboards
- pickle files
