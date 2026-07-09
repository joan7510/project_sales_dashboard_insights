from __future__ import annotations

import html
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "combined_data" / "item_sales_summary.csv"
REPORT_DIR = ROOT / "reports"
REPORT_PATH = REPORT_DIR / "item_sales_report.html"
REPORT_PDF_PATH = REPORT_DIR / "item_sales_report.pdf"

LOCATION_COLORS = {
    "BNE": "#2f6f9f",
    "GC": "#d17a22",
}


def money_to_float(value: object) -> float:
    if pd.isna(value):
        return 0.0

    text = str(value).strip()
    if not text:
        return 0.0

    is_negative = text.startswith("-") or (text.startswith("(") and text.endswith(")"))
    cleaned = re.sub(r"[^0-9.]", "", text)
    if not cleaned:
        return 0.0

    amount = float(cleaned)
    return -amount if is_negative else amount


def load_data() -> pd.DataFrame:
    data = pd.read_csv(DATA_PATH)
    data["Items Sold"] = pd.to_numeric(data["Items Sold"], errors="coerce").fillna(0)
    data["Product Sales Amount"] = data["Product Sales"].apply(money_to_float)
    data["category_updated"] = data.get("category_updated", data["Category"]).fillna("Unknown")
    data["location_display"] = data["location"].replace({"goldcoast": "GC"})
    data["Product"] = data["Item Name"].fillna("Unknown")

    has_variation = data["Item Variation"].fillna("").str.strip().ne("")
    has_regular_variation = data["Item Variation"].fillna("").str.lower().eq("regular")
    data.loc[has_variation & ~has_regular_variation, "Product"] = (
        data["Product"] + " - " + data["Item Variation"]
    )

    return data


def currency(value: float) -> str:
    return f"${value:,.2f}"


def number(value: float) -> str:
    return f"{value:,.0f}"


def percent(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.1%}"


def esc(value: object) -> str:
    return html.escape("" if pd.isna(value) else str(value))


def summarize_by_category(data: pd.DataFrame) -> pd.DataFrame:
    return (
        data.groupby("category_updated", as_index=False)
        .agg(
            items_sold=("Items Sold", "sum"),
            product_sales=("Product Sales Amount", "sum"),
            products=("Product", "nunique"),
        )
        .sort_values("product_sales", ascending=False)
    )


def summarize_by_location_category(data: pd.DataFrame) -> pd.DataFrame:
    return (
        data.groupby(["location_display", "category_updated"], as_index=False)
        .agg(
            items_sold=("Items Sold", "sum"),
            product_sales=("Product Sales Amount", "sum"),
            products=("Product", "nunique"),
        )
        .sort_values("product_sales", ascending=False)
    )


def location_year_category_sales(
    data: pd.DataFrame,
    year: str,
    categories: pd.Series,
) -> pd.DataFrame:
    year_data = data[
        data["year"].eq(year)
        & data["category_updated"].isin(categories)
    ]
    pivot = year_data.pivot_table(
        index="category_updated",
        columns="location_display",
        values="Product Sales Amount",
        aggfunc="sum",
        fill_value=0,
    )

    for location in ("BNE", "GC"):
        if location not in pivot.columns:
            pivot[location] = 0

    result = pivot[["BNE", "GC"]].reset_index()
    result["Total"] = result["BNE"] + result["GC"]
    return result.sort_values("Total", ascending=False)


def location_category_sales_change_pct(
    data: pd.DataFrame,
    years: list[str],
    categories: pd.Series,
) -> pd.DataFrame:
    first_year, second_year = years[0], years[-1]
    scoped = data[
        data["year"].isin([first_year, second_year])
        & data["category_updated"].isin(categories)
    ]
    pivot = scoped.pivot_table(
        index="category_updated",
        columns=["location_display", "year"],
        values="Product Sales Amount",
        aggfunc="sum",
        fill_value=0,
    )

    result = pd.DataFrame({"category_updated": pivot.index})
    for location in ("BNE", "GC"):
        first_sales = pivot.get((location, first_year), pd.Series(0, index=pivot.index))
        second_sales = pivot.get((location, second_year), pd.Series(0, index=pivot.index))
        result[f"{location}_change_pct"] = (second_sales - first_sales).div(
            first_sales.replace(0, pd.NA)
        ).to_numpy()

    total_first = scoped[scoped["year"].eq(first_year)].groupby("category_updated")["Product Sales Amount"].sum()
    total_second = scoped[scoped["year"].eq(second_year)].groupby("category_updated")["Product Sales Amount"].sum()
    total_first = total_first.reindex(pivot.index, fill_value=0)
    total_second = total_second.reindex(pivot.index, fill_value=0)
    result["Total_change_pct"] = (total_second - total_first).div(
        total_first.replace(0, pd.NA)
    ).to_numpy()
    return result.sort_values("Total_change_pct", ascending=False, na_position="last")


def top_products(data: pd.DataFrame, value_column: str, limit: int = 20) -> pd.DataFrame:
    return (
        data.groupby("Product", as_index=False)[value_column]
        .sum()
        .sort_values(value_column, ascending=False)
        .head(limit)
    )


def year_over_year_category(data: pd.DataFrame, years: list[str]) -> pd.DataFrame:
    first_year, second_year = years[0], years[-1]
    summary = (
        data[data["year"].isin([first_year, second_year])]
        .groupby(["category_updated", "year"], as_index=False)
        .agg(
            items_sold=("Items Sold", "sum"),
            product_sales=("Product Sales Amount", "sum"),
        )
    )

    pivot = summary.pivot(index="category_updated", columns="year", values=["items_sold", "product_sales"]).fillna(0)
    result = pd.DataFrame({"category_updated": pivot.index})
    result[f"items_sold_{first_year}"] = pivot.get(("items_sold", first_year), 0).to_numpy()
    result[f"items_sold_{second_year}"] = pivot.get(("items_sold", second_year), 0).to_numpy()
    result[f"sales_{first_year}"] = pivot.get(("product_sales", first_year), 0).to_numpy()
    result[f"sales_{second_year}"] = pivot.get(("product_sales", second_year), 0).to_numpy()
    result["items_sold_change"] = result[f"items_sold_{second_year}"] - result[f"items_sold_{first_year}"]
    result["sales_change"] = result[f"sales_{second_year}"] - result[f"sales_{first_year}"]
    result["sales_change_pct"] = result["sales_change"].div(
        result[f"sales_{first_year}"].replace(0, pd.NA)
    )
    return result.sort_values("sales_change")


def year_over_year_category_location(data: pd.DataFrame, years: list[str]) -> pd.DataFrame:
    first_year, second_year = years[0], years[-1]
    summary = (
        data[data["year"].isin([first_year, second_year])]
        .groupby(["category_updated", "location_display", "year"], as_index=False)
        .agg(product_sales=("Product Sales Amount", "sum"))
    )

    pivot = summary.pivot(
        index=["category_updated", "location_display"],
        columns="year",
        values="product_sales",
    ).fillna(0)

    result = pd.DataFrame(
        {
            "category_updated": pivot.index.get_level_values("category_updated"),
            "location_display": pivot.index.get_level_values("location_display"),
        }
    )
    result[f"sales_{first_year}"] = pivot.get(first_year, 0).to_numpy()
    result[f"sales_{second_year}"] = pivot.get(second_year, 0).to_numpy()
    result["sales_change"] = result[f"sales_{second_year}"] - result[f"sales_{first_year}"]
    return result


def product_sales_change(data: pd.DataFrame, category: str, years: list[str]) -> pd.DataFrame:
    first_year, second_year = years[0], years[-1]
    category_data = data[
        (data["category_updated"].eq(category))
        & data["year"].isin([first_year, second_year])
    ]
    summary = category_data.groupby(["Product", "year"], as_index=False)["Product Sales Amount"].sum()
    pivot = summary.pivot(index="Product", columns="year", values="Product Sales Amount").fillna(0)

    result = pd.DataFrame({"Product": pivot.index})
    result[f"sales_{first_year}"] = pivot.get(first_year, 0).to_numpy()
    result[f"sales_{second_year}"] = pivot.get(second_year, 0).to_numpy()
    result["sales_change"] = result[f"sales_{second_year}"] - result[f"sales_{first_year}"]
    result["sales_change_pct"] = result["sales_change"].div(
        result[f"sales_{first_year}"].replace(0, pd.NA)
    )
    return result.sort_values("sales_change")


def top_increase_decrease(data: pd.DataFrame, value_column: str, limit: int = 10) -> pd.DataFrame:
    decreases = data[data[value_column].lt(0)].sort_values(value_column).head(limit)
    increases = data[data[value_column].gt(0)].sort_values(value_column, ascending=False).head(limit)
    return pd.concat([decreases, increases], ignore_index=True)


def bar_chart(
    rows: pd.DataFrame,
    label_column: str,
    value_column: str,
    value_formatter,
    color: str = "#2f6f9f",
) -> str:
    if rows.empty:
        return "<p class=\"empty\">No data available.</p>"

    chart_rows = rows.copy()
    max_value = chart_rows[value_column].abs().max()
    max_value = max_value if max_value else 1
    parts = ["<div class=\"bar-chart\">"]

    for _, row in chart_rows.iterrows():
        value = float(row[value_column])
        width = max(1.5, abs(value) / max_value * 100)
        parts.append(
            f"""
            <div class="bar-row">
              <div class="bar-label" title="{esc(row[label_column])}">{esc(row[label_column])}</div>
              <div class="bar-track">
                <div class="bar-fill" style="width:{width:.2f}%; background:{color};"></div>
              </div>
              <div class="bar-value">{esc(value_formatter(value))}</div>
            </div>
            """
        )

    parts.append("</div>")
    return "\n".join(parts)


def change_by_location_chart(location_rows: pd.DataFrame, category_totals: pd.DataFrame) -> str:
    if location_rows.empty:
        return "<p class=\"empty\">No year comparison data available.</p>"

    categories = category_totals.sort_values("sales_change")["category_updated"].tolist()
    max_abs = location_rows["sales_change"].abs().max()
    max_abs = max_abs if max_abs else 1
    parts = ["<div class=\"change-chart\">"]

    for category in categories:
        total = category_totals.loc[
            category_totals["category_updated"].eq(category),
            "sales_change",
        ].iat[0]
        parts.append(
            f"""
            <div class="change-row">
              <div class="change-label" title="{esc(category)}">{esc(category)}</div>
              <div class="change-bars">
            """
        )
        for _, row in location_rows[location_rows["category_updated"].eq(category)].iterrows():
            value = float(row["sales_change"])
            width = max(1.5, abs(value) / max_abs * 50)
            side_class = "positive" if value >= 0 else "negative"
            location = row["location_display"]
            color = LOCATION_COLORS.get(location, "#6f6f6f")
            parts.append(
                f"""
                <div class="split-bar {side_class}" title="{esc(location)}: {esc(currency(value))}">
                  <span style="width:{width:.2f}%; background:{color};"></span>
                </div>
                """
            )
        parts.append(
            f"""
              </div>
              <div class="change-total">{esc(currency(total))}</div>
            </div>
            """
        )

    parts.append("</div>")
    return "\n".join(parts)


def table_html(rows: pd.DataFrame, columns: list[tuple[str, str, object]]) -> str:
    parts = ["<div class=\"table-wrap\"><table><thead><tr>"]
    for header, _, _ in columns:
        parts.append(f"<th>{esc(header)}</th>")
    parts.append("</tr></thead><tbody>")

    for _, row in rows.iterrows():
        parts.append("<tr>")
        for _, column, formatter in columns:
            value = row[column]
            if formatter:
                value = formatter(value)
            parts.append(f"<td>{esc(value)}</td>")
        parts.append("</tr>")

    parts.append("</tbody></table></div>")
    return "\n".join(parts)


def metric_card(label: str, value: str) -> str:
    return f"<div class=\"metric\"><span>{esc(label)}</span><strong>{esc(value)}</strong></div>"


def pdf_value(value: object, formatter) -> str:
    if formatter:
        return formatter(value)
    return "" if pd.isna(value) else str(value)


def pdf_table(rows: pd.DataFrame, columns: list[tuple[str, str, object]], styles) -> object:
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle

    data = [[Paragraph(f"<b>{esc(header)}</b>", styles["TableHeader"]) for header, _, _ in columns]]

    for _, row in rows.iterrows():
        data.append(
            [
                Paragraph(esc(pdf_value(row[column], formatter)), styles["TableCell"])
                for _, column, formatter in columns
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#33404c")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e0e7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def add_pdf_section(story: list, title: str, rows: pd.DataFrame, columns: list[tuple[str, str, object]], styles) -> None:
    from reportlab.platypus import KeepTogether, Paragraph, Spacer

    story.append(
        KeepTogether(
            [
                Paragraph(title, styles["Heading2"]),
                Spacer(1, 6),
                pdf_table(rows, columns, styles),
                Spacer(1, 14),
            ]
        )
    )


def build_pdf_report() -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    data = load_data()
    years = sorted(data["year"].dropna().unique())
    first_year, second_year = years[0], years[-1]

    category_summary = summarize_by_category(data)
    location_summary = summarize_by_location_category(data)
    category_change = year_over_year_category(data, years)
    category_change_top = top_increase_decrease(category_change, "sales_change", 10)
    top_category_sales = category_summary.head(10)
    top_category_items = category_summary.sort_values("items_sold", ascending=False).head(10)
    top_sales_products = top_products(data, "Product Sales Amount", 20)
    top_item_products = top_products(data, "Items Sold", 20)

    location_top_categories = (
        location_summary.groupby("category_updated", as_index=False)["product_sales"]
        .sum()
        .sort_values("product_sales", ascending=False)
        .head(10)["category_updated"]
    )
    location_sales_first_year = location_year_category_sales(data, first_year, location_top_categories)
    location_sales_second_year = location_year_category_sales(data, second_year, location_top_categories)
    location_sales_change_pct = location_category_sales_change_pct(data, years, location_top_categories)

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["Normal"],
            fontSize=7,
            leading=8,
            textColor=colors.HexColor("#33404c"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontSize=7,
            leading=8,
        )
    )

    doc = SimpleDocTemplate(
        str(REPORT_PDF_PATH),
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Item Sales Summary Report",
    )

    story = [
        Paragraph("Item Sales Summary Report", styles["Title"]),
        Paragraph(
            f"Static offline report for {esc(first_year)} and {esc(second_year)}. "
            "Generated from local CSV data only.",
            styles["BodyText"],
        ),
        Spacer(1, 10),
    ]

    metrics = pd.DataFrame(
        [
            {"Metric": "Total Items Sold", "Value": number(data["Items Sold"].sum())},
            {"Metric": "Product Sales", "Value": currency(data["Product Sales Amount"].sum())},
            {"Metric": "Unique Products", "Value": number(data["Product"].nunique())},
            {"Metric": "Rows Reviewed", "Value": number(len(data))},
        ]
    )
    add_pdf_section(story, "Summary", metrics, [("Metric", "Metric", None), ("Value", "Value", None)], styles)

    add_pdf_section(
        story,
        "Top 10 Categories by Product Sales",
        top_category_sales,
        [
            ("Category", "category_updated", None),
            ("Product Sales", "product_sales", currency),
            ("Items Sold", "items_sold", number),
            ("Products", "products", number),
        ],
        styles,
    )
    add_pdf_section(
        story,
        "Top 10 Categories by Items Sold",
        top_category_items,
        [
            ("Category", "category_updated", None),
            ("Items Sold", "items_sold", number),
            ("Product Sales", "product_sales", currency),
            ("Products", "products", number),
        ],
        styles,
    )

    story.append(PageBreak())
    add_pdf_section(
        story,
        "Top 20 Products by Product Sales",
        top_sales_products,
        [("Product", "Product", None), ("Product Sales", "Product Sales Amount", currency)],
        styles,
    )
    add_pdf_section(
        story,
        "Top 20 Products by Items Sold",
        top_item_products,
        [("Product", "Product", None), ("Items Sold", "Items Sold", number)],
        styles,
    )

    story.append(PageBreak())
    add_pdf_section(
        story,
        f"Category Change: {second_year} vs {first_year}",
        category_change_top.sort_values("sales_change", ascending=False),
        [
            ("Category", "category_updated", None),
            (first_year, f"sales_{first_year}", currency),
            (second_year, f"sales_{second_year}", currency),
            ("Sales Change", "sales_change", currency),
            ("% Change", "sales_change_pct", percent),
        ],
        styles,
    )

    story.append(PageBreak())
    add_pdf_section(
        story,
        f"Location Product Sales by Category: {first_year}",
        location_sales_first_year,
        [
            ("Category", "category_updated", None),
            ("BNE", "BNE", currency),
            ("GC", "GC", currency),
            ("Total", "Total", currency),
        ],
        styles,
    )
    add_pdf_section(
        story,
        f"Location Product Sales by Category: {second_year}",
        location_sales_second_year,
        [
            ("Category", "category_updated", None),
            ("BNE", "BNE", currency),
            ("GC", "GC", currency),
            ("Total", "Total", currency),
        ],
        styles,
    )
    add_pdf_section(
        story,
        "Product Sales Change % by Location",
        location_sales_change_pct,
        [
            ("Category", "category_updated", None),
            ("BNE Change %", "BNE_change_pct", percent),
            ("GC Change %", "GC_change_pct", percent),
            ("Total Change %", "Total_change_pct", percent),
        ],
        styles,
    )

    doc.build(story)


def build_report() -> str:
    data = load_data()
    years = sorted(data["year"].dropna().unique())
    first_year, second_year = years[0], years[-1]

    category_summary = summarize_by_category(data)
    location_summary = summarize_by_location_category(data)
    category_change = year_over_year_category(data, years)
    category_change_top = top_increase_decrease(category_change, "sales_change", 10)
    category_location_change = year_over_year_category_location(data, years)
    category_location_change = category_location_change[
        category_location_change["category_updated"].isin(category_change_top["category_updated"])
    ]

    top_category_sales = category_summary.head(10)
    top_category_items = category_summary.sort_values("items_sold", ascending=False).head(10)
    top_sales_products = top_products(data, "Product Sales Amount", 20)
    top_item_products = top_products(data, "Items Sold", 20)

    locations = sorted(data["location_display"].dropna().unique())
    review_needed = int(data.get("category_update_method", pd.Series()).eq("review_needed").sum())

    top_changed_category = category_change_top.sort_values("sales_change", ascending=False).head(1)
    bottom_changed_category = category_change_top.sort_values("sales_change").head(1)

    selected_categories = []
    if not top_changed_category.empty:
        selected_categories.append(top_changed_category["category_updated"].iat[0])
    if not bottom_changed_category.empty:
        selected_categories.append(bottom_changed_category["category_updated"].iat[0])
    selected_categories = list(dict.fromkeys(selected_categories))

    product_change_sections = []
    for category in selected_categories:
        product_change = product_sales_change(data, category, years)
        increased = product_change[product_change["sales_change"].gt(0)].sort_values("sales_change", ascending=False).head(10)
        dropped = product_change[product_change["sales_change"].lt(0)].head(10)
        product_change_sections.append(
            f"""
            <section>
              <h3>{esc(category)} Product Movement</h3>
              <div class="grid two">
                <div>
                  <h4>Top 10 Increased</h4>
                  {table_html(increased, [
                      ("Product", "Product", None),
                      (second_year, f"sales_{second_year}", currency),
                      ("Change", "sales_change", currency),
                      ("% Change", "sales_change_pct", percent),
                  ])}
                </div>
                <div>
                  <h4>Top 10 Dropped</h4>
                  {table_html(dropped, [
                      ("Product", "Product", None),
                      (second_year, f"sales_{second_year}", currency),
                      ("Change", "sales_change", currency),
                      ("% Change", "sales_change_pct", percent),
                  ])}
                </div>
              </div>
            </section>
            """
        )

    location_top_categories = (
        location_summary.groupby("category_updated", as_index=False)["product_sales"]
        .sum()
        .sort_values("product_sales", ascending=False)
        .head(10)["category_updated"]
    )
    location_sales_first_year = location_year_category_sales(
        data,
        first_year,
        location_top_categories,
    )
    location_sales_second_year = location_year_category_sales(
        data,
        second_year,
        location_top_categories,
    )
    location_sales_change_pct = location_category_sales_change_pct(
        data,
        years,
        location_top_categories,
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Item Sales Summary Report</title>
  <style>
    :root {{
      --ink: #1f2933;
      --muted: #657280;
      --line: #d9e0e7;
      --panel: #ffffff;
      --page: #f5f7f9;
      --accent: #2f6f9f;
      --accent-2: #d17a22;
      --good: #2f7d5c;
      --bad: #bd4b4b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--page);
      color: var(--ink);
      line-height: 1.45;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }}
    header {{ margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 16px; font-size: 22px; }}
    h3 {{ margin: 0 0 14px; font-size: 18px; }}
    h4 {{ margin: 0 0 10px; font-size: 15px; }}
    p {{ color: var(--muted); margin: 0; }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin: 18px 0;
    }}
    .grid {{ display: grid; gap: 18px; }}
    .two {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .metrics {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .metric span {{ display: block; color: var(--muted); font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    .bar-chart {{ display: grid; gap: 9px; }}
    .bar-row {{
      display: grid;
      grid-template-columns: minmax(160px, 270px) 1fr minmax(92px, max-content);
      gap: 10px;
      align-items: center;
      min-height: 24px;
    }}
    .bar-label, .change-label {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #27313b;
      font-size: 13px;
    }}
    .bar-track {{ height: 13px; background: #e8edf2; border-radius: 3px; overflow: hidden; }}
    .bar-fill {{ height: 100%; }}
    .bar-value, .change-total {{ text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; color: #394652; }}
    .change-chart {{ display: grid; gap: 10px; }}
    .change-row {{
      display: grid;
      grid-template-columns: minmax(160px, 270px) 1fr 110px;
      gap: 10px;
      align-items: center;
    }}
    .change-bars {{
      position: relative;
      height: 22px;
      background: linear-gradient(to right, transparent 0 49.7%, #b8c2cc 49.7% 50.3%, transparent 50.3%);
    }}
    .split-bar {{ position: absolute; top: 2px; width: 50%; height: 8px; }}
    .split-bar:nth-child(2) {{ top: 12px; }}
    .split-bar.negative {{ left: 0; display: flex; justify-content: flex-end; }}
    .split-bar.positive {{ left: 50%; }}
    .split-bar span {{ display: block; height: 8px; border-radius: 3px; }}
    .legend {{ display: flex; gap: 14px; margin: 6px 0 14px; color: var(--muted); font-size: 13px; }}
    .swatch {{ display: inline-block; width: 10px; height: 10px; margin-right: 5px; border-radius: 2px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }}
    table {{ border-collapse: collapse; width: 100%; min-width: 650px; background: #fff; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; font-size: 13px; }}
    th {{ background: #eef2f5; color: #33404c; font-weight: 650; }}
    tr:last-child td {{ border-bottom: 0; }}
    td:not(:first-child), th:not(:first-child) {{ text-align: right; }}
    .note {{ font-size: 13px; color: var(--muted); margin-top: 10px; }}
    .empty {{ color: var(--muted); }}
    @media (max-width: 850px) {{
      main {{ padding: 20px 12px 36px; }}
      .two, .metrics {{ grid-template-columns: 1fr; }}
      .bar-row, .change-row {{ grid-template-columns: 1fr; gap: 5px; }}
      .bar-value, .change-total {{ text-align: left; }}
      .bar-label, .change-label {{ white-space: normal; }}
    }}
    @media print {{
      body {{ background: #fff; }}
      main {{ max-width: none; padding: 0; }}
      section, .metric {{ break-inside: avoid; }}
      .grid.two {{ grid-template-columns: 1fr 1fr; }}
      .table-wrap {{ overflow: visible; }}
      table {{ min-width: 0; }}
      th, td {{ font-size: 10px; padding: 5px 6px; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Item Sales Summary Report</h1>
    <p>Static offline report for {esc(first_year)} and {esc(second_year)}. Locations: {esc(", ".join(locations))}. Generated from local CSV data only.</p>
  </header>

  <div class="grid metrics">
    {metric_card("Total Items Sold", number(data["Items Sold"].sum()))}
    {metric_card("Product Sales", currency(data["Product Sales Amount"].sum()))}
    {metric_card("Unique Products", number(data["Product"].nunique()))}
    {metric_card("Rows Reviewed", number(len(data)))}
  </div>

  <section>
    <h2>Top Categories</h2>
    <div class="grid two">
      <div>
        <h3>Top 10 by Product Sales</h3>
        {bar_chart(top_category_sales, "category_updated", "product_sales", currency, "#2f6f9f")}
      </div>
      <div>
        <h3>Top 10 by Items Sold</h3>
        {bar_chart(top_category_items, "category_updated", "items_sold", number, "#d17a22")}
      </div>
    </div>
  </section>

  <section>
    <h2>Top Products</h2>
    <div class="grid two">
      <div>
        <h3>Top 20 by Product Sales</h3>
        {bar_chart(top_sales_products, "Product", "Product Sales Amount", currency, "#2f6f9f")}
      </div>
      <div>
        <h3>Top 20 by Items Sold</h3>
        {bar_chart(top_item_products, "Product", "Items Sold", number, "#d17a22")}
      </div>
    </div>
  </section>

  <section>
    <h2>Category Change: {esc(second_year)} vs {esc(first_year)}</h2>
    <div class="legend">
      <span><span class="swatch" style="background:{LOCATION_COLORS["BNE"]};"></span>BNE</span>
      <span><span class="swatch" style="background:{LOCATION_COLORS["GC"]};"></span>GC</span>
    </div>
    {change_by_location_chart(category_location_change, category_change_top)}
    <p class="note">Only the top 10 increased and top 10 decreased categories are shown.</p>
    {table_html(category_change_top.sort_values("sales_change", ascending=False), [
        ("Category", "category_updated", None),
        (first_year, f"sales_{first_year}", currency),
        (second_year, f"sales_{second_year}", currency),
        ("Sales Change", "sales_change", currency),
        ("% Change", "sales_change_pct", percent),
    ])}
  </section>

  {"".join(product_change_sections)}

  <section>
    <h2>Location Comparison</h2>
    <div class="grid two">
      <div>
        <h3>{esc(first_year)} Product Sales by Category</h3>
        {table_html(location_sales_first_year, [
            ("Category", "category_updated", None),
            ("BNE", "BNE", currency),
            ("GC", "GC", currency),
            ("Total", "Total", currency),
        ])}
      </div>
      <div>
        <h3>{esc(second_year)} Product Sales by Category</h3>
        {table_html(location_sales_second_year, [
            ("Category", "category_updated", None),
            ("BNE", "BNE", currency),
            ("GC", "GC", currency),
            ("Total", "Total", currency),
        ])}
      </div>
    </div>
    <h3>Product Sales Change % by Location</h3>
    {table_html(location_sales_change_pct, [
        ("Category", "category_updated", None),
        ("BNE Change %", "BNE_change_pct", percent),
        ("GC Change %", "GC_change_pct", percent),
        ("Total Change %", "Total_change_pct", percent),
    ])}
  </section>

  <section>
    <h2>Notes</h2>
    <p>This is a self-contained HTML file. It does not upload data, call online services, or require account registration. The report contains summarized sales information, not the full transaction-level source data.</p>
    <p class="note">Rows still marked for category review: {esc(number(review_needed))}.</p>
  </section>
</main>
</body>
</html>
"""


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(), encoding="utf-8")
    print(f"Report saved to {REPORT_PATH.relative_to(ROOT)}")
    build_pdf_report()
    print(f"PDF saved to {REPORT_PDF_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
