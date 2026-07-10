from __future__ import annotations

import argparse
import csv
import html
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


ORDER_LEVEL_COLUMNS = [
    "financial_year",
    "Financial Status",
    "Fulfillment Status",
    "Created at",
    "Accepts Marketing",
    "Shipping Province",
    "Billing Province",
]


def decimal_value(value: object) -> Decimal:
    text = ("" if value is None else str(value)).strip().replace(",", "")
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def lineitem_sales(row: dict[str, str]) -> Decimal:
    return decimal_value(row.get("Lineitem quantity")) * decimal_value(row.get("Lineitem price"))


def money(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if rounded < 0 else ""
    return f"{sign}${abs(rounded):,.2f}"


def number(value: int | Decimal) -> str:
    return f"{value:,.0f}"


def percent(value: Decimal, denominator: Decimal) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{(value / denominator * Decimal('100')).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"


def bar_width(value: Decimal, maximum: Decimal) -> str:
    if maximum == 0:
        return "0%"
    width = value / maximum * Decimal("100")
    width = max(Decimal("0"), min(Decimal("100"), width))
    return f"{width.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}%"


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def load_rows(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    last_values = {column: "" for column in ORDER_LEVEL_COLUMNS}

    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            for column in ORDER_LEVEL_COLUMNS:
                if (row.get(column) or "").strip():
                    last_values[column] = row[column]
                else:
                    row[column] = last_values[column]
            row["lineitem_sales"] = lineitem_sales(row)  # type: ignore[assignment]
            rows.append(row)

    return rows


def is_non_paid(row: dict[str, str]) -> bool:
    return (row.get("Financial Status") or "").strip() != "paid"


def is_unfulfilled(row: dict[str, str]) -> bool:
    return (row.get("Fulfillment Status") or "").strip() != "fulfilled"


def sales_sum(rows: list[dict[str, str]]) -> Decimal:
    return sum((row["lineitem_sales"] for row in rows), Decimal("0"))  # type: ignore[return-value]


def by_year(rows: list[dict[str, str]]) -> dict[str, dict[str, Decimal | int]]:
    result: dict[str, dict[str, Decimal | int]] = {
        "24-25": {"rows": 0, "sales": Decimal("0")},
        "25-26": {"rows": 0, "sales": Decimal("0")},
    }
    for row in rows:
        year = row.get("financial_year")
        if year not in result:
            continue
        result[year]["rows"] = int(result[year]["rows"]) + 1
        result[year]["sales"] = result[year]["sales"] + row["lineitem_sales"]  # type: ignore[operator]
    return result


def grouped_by_year(rows: list[dict[str, str]], column: str) -> dict[str, dict[str, dict[str, Decimal | int]]]:
    result: dict[str, dict[str, dict[str, Decimal | int]]] = defaultdict(
        lambda: {
            "24-25": {"rows": 0, "sales": Decimal("0")},
            "25-26": {"rows": 0, "sales": Decimal("0")},
        }
    )
    for row in rows:
        year = row.get("financial_year")
        if year not in ("24-25", "25-26"):
            continue
        label = (row.get(column) or "(blank)").strip() or "(blank)"
        result[label][year]["rows"] = int(result[label][year]["rows"]) + 1
        result[label][year]["sales"] = result[label][year]["sales"] + row["lineitem_sales"]  # type: ignore[operator]

    return dict(
        sorted(
            result.items(),
            key=lambda item: item[1]["24-25"]["sales"] + item[1]["25-26"]["sales"],  # type: ignore[operator]
            reverse=True,
        )
    )


def top_products(rows: list[dict[str, str]], limit: int = 10) -> list[tuple[str, dict[str, Decimal | int]]]:
    result: dict[str, dict[str, Decimal | int]] = defaultdict(
        lambda: {"quantity": Decimal("0"), "sales": Decimal("0"), "rows": 0}
    )
    for row in rows:
        product = (row.get("Lineitem name") or "(blank)").strip() or "(blank)"
        result[product]["quantity"] = result[product]["quantity"] + decimal_value(row.get("Lineitem quantity"))  # type: ignore[operator]
        result[product]["sales"] = result[product]["sales"] + row["lineitem_sales"]  # type: ignore[operator]
        result[product]["rows"] = int(result[product]["rows"]) + 1
    return sorted(result.items(), key=lambda item: item[1]["sales"], reverse=True)[:limit]  # type: ignore[arg-type]


def yoy_change(current: Decimal, previous: Decimal) -> str:
    if previous == 0:
        return "n/a"
    value = (current - previous) / previous * Decimal("100")
    return f"{value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"


def signed_money(value: Decimal) -> str:
    if value > 0:
        return money(value)
    return money(value)


def make_status_rows(groups: dict[str, dict[str, dict[str, Decimal | int]]], maximum: Decimal) -> str:
    output: list[str] = []
    for label, values in groups.items():
        previous = values["24-25"]["sales"]
        current = values["25-26"]["sales"]
        diff = current - previous  # type: ignore[operator]
        output.append(
            f"""
      <div class="status-row">
        <div class="status-label">{esc(label)}</div>
        <div class="small-track"><div class="small-fill" style="width:{bar_width(previous, maximum)}; background:var(--blue);"></div></div>
        <div class="small-track"><div class="small-fill" style="width:{bar_width(current, maximum)}; background:var(--orange);"></div></div>
        <div class="change-value {'positive' if diff >= 0 else 'negative'}">{signed_money(diff)}</div>
      </div>"""
        )
    return "".join(output)


def make_product_rows(products: list[tuple[str, dict[str, Decimal | int]]]) -> str:
    maximum = max((values["sales"] for _, values in products), default=Decimal("1"))  # type: ignore[type-var]
    output: list[str] = []
    for product, values in products:
        sales = values["sales"]
        output.append(
            f"""
      <div class="product-row">
        <div class="product-label" title="{esc(product)}">{esc(product)}</div>
        <div class="small-track"><div class="small-fill" style="width:{bar_width(sales, maximum)}; background:var(--gold);"></div></div>
        <div class="change-value">{money(sales)}</div>
      </div>"""
        )
    return "".join(output)


def render_dashboard(input_path: Path, output_path: Path) -> None:
    rows = load_rows(input_path)
    total_rows = rows
    unsuccessful_rows = [row for row in rows if is_non_paid(row) or is_unfulfilled(row)]
    non_paid_rows = [row for row in rows if is_non_paid(row)]
    unfulfilled_rows = [row for row in rows if is_unfulfilled(row)]
    both_rows = [row for row in rows if is_non_paid(row) and is_unfulfilled(row)]

    total_sales = sales_sum(total_rows)
    unsuccessful_sales = sales_sum(unsuccessful_rows)
    non_paid_sales = sales_sum(non_paid_rows)
    unfulfilled_sales = sales_sum(unfulfilled_rows)
    both_sales = sales_sum(both_rows)

    unsuccessful_year = by_year(unsuccessful_rows)
    non_paid_year = by_year(non_paid_rows)
    unfulfilled_year = by_year(unfulfilled_rows)
    both_year = by_year(both_rows)
    total_year = by_year(total_rows)

    max_year = max(
        unsuccessful_year["24-25"]["sales"],
        unsuccessful_year["25-26"]["sales"],
        non_paid_year["24-25"]["sales"],
        non_paid_year["25-26"]["sales"],
        unfulfilled_year["24-25"]["sales"],
        unfulfilled_year["25-26"]["sales"],
        both_year["24-25"]["sales"],
        both_year["25-26"]["sales"],
    )

    non_paid_groups = grouped_by_year(non_paid_rows, "Financial Status")
    fulfillment_groups = grouped_by_year(unfulfilled_rows, "Fulfillment Status")
    max_status = max(
        [
            values[year]["sales"]
            for groups in (non_paid_groups, fulfillment_groups)
            for values in groups.values()
            for year in ("24-25", "25-26")
        ],
        default=Decimal("1"),
    )

    products = top_products(unsuccessful_rows)

    unsuccessful_diff = unsuccessful_year["25-26"]["sales"] - unsuccessful_year["24-25"]["sales"]
    non_paid_diff = non_paid_year["25-26"]["sales"] - non_paid_year["24-25"]["sales"]
    unfulfilled_diff = unfulfilled_year["25-26"]["sales"] - unfulfilled_year["24-25"]["sales"]
    both_diff = both_year["25-26"]["sales"] - both_year["24-25"]["sales"]

    html_document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Unpaid And Unfulfilled Sales Dashboard</title>
  <style>
    :root {{
      --ink: #1f2933;
      --muted: #657280;
      --line: #d9e0e7;
      --panel: #ffffff;
      --page: #f5f7f9;
      --blue: #2f6f9f;
      --orange: #d17a22;
      --green: #2f7d5c;
      --red: #bd4b4b;
      --gold: #a67915;
    }}
    * {{ box-sizing: border-box; }}
    html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--page); color: var(--ink); line-height: 1.45; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }}
    header {{ margin-bottom: 22px; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 22px; }}
    p {{ margin: 0; color: var(--muted); }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 18px; margin: 18px 0; }}
    .grid {{ display: grid; gap: 16px; }}
    .metrics {{ grid-template-columns: repeat(5, minmax(0, 1fr)); }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; min-height: 108px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 8px; font-size: 24px; font-variant-numeric: tabular-nums; }}
    .metric .delta {{ margin-top: 8px; font-size: 13px; color: var(--muted); }}
    .metric .positive, .positive {{ color: var(--green); }}
    .metric .negative, .negative {{ color: var(--red); }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 14px; margin: 4px 0 14px; color: var(--muted); font-size: 13px; }}
    .swatch {{ display: inline-block; width: 10px; height: 10px; margin-right: 5px; border-radius: 2px; }}
    .bar-chart, .status-grid {{ display: grid; gap: 12px; }}
    .bar-row {{ display: grid; grid-template-columns: 160px 1fr 1fr minmax(112px, max-content); gap: 10px; align-items: center; }}
    .status-row {{ display: grid; grid-template-columns: minmax(150px, 220px) 1fr 1fr minmax(112px, max-content); gap: 10px; align-items: center; }}
    .product-row {{ display: grid; grid-template-columns: minmax(260px, 420px) 1fr minmax(112px, max-content); gap: 10px; align-items: center; }}
    .bar-label, .status-label, .product-label {{ color: #33404c; font-size: 13px; font-weight: 650; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .bar-track {{ height: 30px; background: #e8edf2; border-radius: 4px; overflow: hidden; }}
    .bar-fill {{ height: 100%; min-width: 2px; display: flex; align-items: center; justify-content: flex-end; padding-right: 7px; color: #fff; font-size: 12px; font-variant-numeric: tabular-nums; white-space: nowrap; }}
    .small-track {{ height: 18px; background: #e8edf2; border-radius: 4px; overflow: hidden; }}
    .small-fill {{ height: 100%; min-width: 1px; }}
    .change-value {{ text-align: right; font-size: 13px; font-variant-numeric: tabular-nums; }}
    .note {{ font-size: 13px; color: var(--muted); margin-top: 10px; }}
    .notes {{ display: grid; gap: 7px; color: var(--muted); font-size: 13px; margin: 0; padding-left: 18px; }}
    @media (max-width: 900px) {{
      main {{ padding: 22px 12px 36px; }}
      .metrics {{ grid-template-columns: 1fr; }}
      .bar-row, .status-row, .product-row {{ grid-template-columns: 1fr; }}
      .change-value {{ text-align: left; }}
      .bar-label, .status-label, .product-label {{ white-space: normal; }}
      h1 {{ font-size: 28px; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Unpaid And Unfulfilled Sales</h1>
    <p>FY24-25 vs FY25-26 line-item risk view. Sales amount is calculated as <code>Lineitem quantity * Lineitem price</code>.</p>
  </header>

  <div class="grid metrics">
    <div class="metric"><span>Unsuccessful Sales</span><strong>{money(unsuccessful_sales)}</strong><div class="delta positive">+{yoy_change(unsuccessful_year['25-26']['sales'], unsuccessful_year['24-25']['sales'])} YoY</div></div>
    <div class="metric"><span>Unsuccessful Rate</span><strong>{percent(unsuccessful_sales, total_sales)}</strong><div class="delta">{percent(unsuccessful_year['24-25']['sales'], total_year['24-25']['sales'])} to {percent(unsuccessful_year['25-26']['sales'], total_year['25-26']['sales'])} by year</div></div>
    <div class="metric"><span>Non-Paid Sales</span><strong>{money(non_paid_sales)}</strong><div class="delta negative">{yoy_change(non_paid_year['25-26']['sales'], non_paid_year['24-25']['sales'])} YoY</div></div>
    <div class="metric"><span>Unfulfilled Sales</span><strong>{money(unfulfilled_sales)}</strong><div class="delta positive">+{yoy_change(unfulfilled_year['25-26']['sales'], unfulfilled_year['24-25']['sales'])} YoY</div></div>
    <div class="metric"><span>Both Non-Paid And Unfulfilled</span><strong>{money(both_sales)}</strong><div class="delta positive">+{yoy_change(both_year['25-26']['sales'], both_year['24-25']['sales'])} YoY</div></div>
  </div>

  <section>
    <h2>Year Comparison</h2>
    <div class="legend"><span><i class="swatch" style="background:var(--blue);"></i>FY24-25</span><span><i class="swatch" style="background:var(--orange);"></i>FY25-26</span></div>
    <div class="bar-chart">
      <div class="bar-row"><div class="bar-label">Unsuccessful sales</div><div class="bar-track"><div class="bar-fill" style="width:{bar_width(unsuccessful_year['24-25']['sales'], max_year)}; background:var(--blue);">{money(unsuccessful_year['24-25']['sales'])}</div></div><div class="bar-track"><div class="bar-fill" style="width:{bar_width(unsuccessful_year['25-26']['sales'], max_year)}; background:var(--orange);">{money(unsuccessful_year['25-26']['sales'])}</div></div><div class="change-value positive">{money(unsuccessful_diff)}</div></div>
      <div class="bar-row"><div class="bar-label">Non-paid sales</div><div class="bar-track"><div class="bar-fill" style="width:{bar_width(non_paid_year['24-25']['sales'], max_year)}; background:var(--blue);">{money(non_paid_year['24-25']['sales'])}</div></div><div class="bar-track"><div class="bar-fill" style="width:{bar_width(non_paid_year['25-26']['sales'], max_year)}; background:var(--orange);">{money(non_paid_year['25-26']['sales'])}</div></div><div class="change-value negative">{money(non_paid_diff)}</div></div>
      <div class="bar-row"><div class="bar-label">Unfulfilled sales</div><div class="bar-track"><div class="bar-fill" style="width:{bar_width(unfulfilled_year['24-25']['sales'], max_year)}; background:var(--blue);">{money(unfulfilled_year['24-25']['sales'])}</div></div><div class="bar-track"><div class="bar-fill" style="width:{bar_width(unfulfilled_year['25-26']['sales'], max_year)}; background:var(--orange);">{money(unfulfilled_year['25-26']['sales'])}</div></div><div class="change-value positive">{money(unfulfilled_diff)}</div></div>
      <div class="bar-row"><div class="bar-label">Both issues</div><div class="bar-track"><div class="bar-fill" style="width:{bar_width(both_year['24-25']['sales'], max_year)}; background:var(--blue);">{money(both_year['24-25']['sales'])}</div></div><div class="bar-track"><div class="bar-fill" style="width:{bar_width(both_year['25-26']['sales'], max_year)}; background:var(--orange);">{money(both_year['25-26']['sales'])}</div></div><div class="change-value positive">{money(both_diff)}</div></div>
    </div>
    <p class="note">Statuses are forward-filled from order header rows to continuation line-item rows before filtering.</p>
  </section>

  <section>
    <h2>Non-Paid Sales By Payment Status</h2>
    <div class="legend"><span><i class="swatch" style="background:var(--blue);"></i>FY24-25</span><span><i class="swatch" style="background:var(--orange);"></i>FY25-26</span></div>
    <div class="status-grid">{make_status_rows(non_paid_groups, max_status)}
    </div>
  </section>

  <section>
    <h2>Unfulfilled Sales By Fulfillment Status</h2>
    <div class="legend"><span><i class="swatch" style="background:var(--blue);"></i>FY24-25</span><span><i class="swatch" style="background:var(--orange);"></i>FY25-26</span></div>
    <div class="status-grid">{make_status_rows(fulfillment_groups, max_status)}
    </div>
  </section>

  <section>
    <h2>Top Unsuccessful Products</h2>
    <div class="status-grid">{make_product_rows(products)}
    </div>
  </section>

  <section>
    <h2>Insight Summary</h2>
    <ul class="notes">
      <li>Unsuccessful sales increased by {money(unsuccessful_diff)}, from {money(unsuccessful_year['24-25']['sales'])} in FY24-25 to {money(unsuccessful_year['25-26']['sales'])} in FY25-26, a {yoy_change(unsuccessful_year['25-26']['sales'], unsuccessful_year['24-25']['sales'])} increase.</li>
      <li>Unsuccessful sales represent {percent(unsuccessful_sales, total_sales)} of total line-item sales across both years, rising from {percent(unsuccessful_year['24-25']['sales'], total_year['24-25']['sales'])} in FY24-25 to {percent(unsuccessful_year['25-26']['sales'], total_year['25-26']['sales'])} in FY25-26.</li>
      <li>Non-paid line-item sales decreased by {money(abs(non_paid_diff))}, or {yoy_change(non_paid_year['25-26']['sales'], non_paid_year['24-25']['sales'])}, but unfulfilled line-item sales increased by {money(unfulfilled_diff)}, or {yoy_change(unfulfilled_year['25-26']['sales'], unfulfilled_year['24-25']['sales'])}.</li>
      <li>FY25-26 has {number(unfulfilled_year['25-26']['rows'])} unfulfilled or partially fulfilled line rows, compared with {number(unfulfilled_year['24-25']['rows'])} in FY24-25.</li>
      <li>The overlap of non-paid and unfulfilled sales is {money(both_sales)}, with FY25-26 slightly higher by {money(both_diff)}.</li>
      <li>The highest-value unsuccessful product is {esc(products[0][0])}, contributing {money(products[0][1]['sales'])}.</li>
    </ul>
  </section>
</main>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_document, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the unpaid/unfulfilled sales dashboard.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("combined_orders_24-26_cleaned.csv"),
        help="Path to the cleaned orders CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/unpaid_unfulfilled_sales_dashboard.html"),
        help="Path for the generated dashboard HTML.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    render_dashboard(args.input, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
