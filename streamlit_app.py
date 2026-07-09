from __future__ import annotations

import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


DATA_PATH = Path(__file__).resolve().parent / "combined_data" / "item_sales_summary.csv"


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


@st.cache_data
def load_data(data_file_mtime: float) -> pd.DataFrame:
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


def top_products(data: pd.DataFrame, value_column: str, limit: int) -> pd.DataFrame:
    return (
        data.groupby("Product", as_index=False)[value_column]
        .sum()
        .sort_values(value_column, ascending=False)
        .head(limit)
    )


def horizontal_bar_chart(
    data: pd.DataFrame,
    label_column: str,
    value_column: str,
    title: str,
    value_format: str = ",.2f",
) -> alt.Chart:
    return (
        alt.Chart(data, title=title)
        .mark_bar()
        .encode(
            x=alt.X(value_column, title=None),
            y=alt.Y(
                label_column,
                title=None,
                sort=alt.SortField(field=value_column, order="descending"),
            ),
            tooltip=[
                alt.Tooltip(label_column, title=label_column.replace("_", " ").title()),
                alt.Tooltip(value_column, title=title, format=value_format),
            ],
        )
        .properties(height=max(360, len(data) * 24))
    )


def category_chart(data: pd.DataFrame, value_column: str, title: str) -> alt.Chart:
    return horizontal_bar_chart(
        data.sort_values(value_column, ascending=False),
        "category_updated",
        value_column,
        title,
    )


def location_category_chart(data: pd.DataFrame, value_column: str, title: str) -> alt.Chart:
    category_order = (
        data.groupby("category_updated")[value_column]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    return (
        alt.Chart(data, title=title)
        .mark_bar()
        .encode(
            x=alt.X(value_column, title=None),
            y=alt.Y(
                "category_updated",
                title=None,
                sort=category_order,
            ),
            color=alt.Color("location_display", title="Location"),
            tooltip=[
                alt.Tooltip("location_display", title="Location"),
                alt.Tooltip("category_updated", title="Category"),
                alt.Tooltip(value_column, title=title, format=",.2f"),
            ],
        )
        .properties(height=max(360, data["category_updated"].nunique() * 28))
    )


def year_over_year_category(data: pd.DataFrame, years: list[str]) -> pd.DataFrame:
    if len(years) < 2:
        return pd.DataFrame()

    first_year, second_year = years[0], years[-1]
    summary = (
        data[data["year"].isin([first_year, second_year])]
        .groupby(["category_updated", "year"], as_index=False)
        .agg(
            items_sold=("Items Sold", "sum"),
            product_sales=("Product Sales Amount", "sum"),
        )
    )

    pivot = summary.pivot(index="category_updated", columns="year", values=["items_sold", "product_sales"])
    pivot = pivot.fillna(0)

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
    return result.sort_values("sales_change", ascending=True)


def top_increase_decrease(data: pd.DataFrame, value_column: str, limit: int = 10) -> pd.DataFrame:
    decreases = data[data[value_column].lt(0)].sort_values(value_column).head(limit)
    increases = data[data[value_column].gt(0)].sort_values(value_column, ascending=False).head(limit)
    return pd.concat([decreases, increases], ignore_index=True)


def year_over_year_category_location(data: pd.DataFrame, years: list[str]) -> pd.DataFrame:
    if len(years) < 2:
        return pd.DataFrame()

    first_year, second_year = years[0], years[-1]
    summary = (
        data[data["year"].isin([first_year, second_year])]
        .groupby(["category_updated", "location_display", "year"], as_index=False)
        .agg(
            items_sold=("Items Sold", "sum"),
            product_sales=("Product Sales Amount", "sum"),
        )
    )

    pivot = summary.pivot(
        index=["category_updated", "location_display"],
        columns="year",
        values=["items_sold", "product_sales"],
    ).fillna(0)

    result = pd.DataFrame(
        {
            "category_updated": pivot.index.get_level_values("category_updated"),
            "location_display": pivot.index.get_level_values("location_display"),
        }
    )
    result[f"items_sold_{first_year}"] = pivot.get(("items_sold", first_year), 0).to_numpy()
    result[f"items_sold_{second_year}"] = pivot.get(("items_sold", second_year), 0).to_numpy()
    result[f"sales_{first_year}"] = pivot.get(("product_sales", first_year), 0).to_numpy()
    result[f"sales_{second_year}"] = pivot.get(("product_sales", second_year), 0).to_numpy()
    result["items_sold_change"] = result[f"items_sold_{second_year}"] - result[f"items_sold_{first_year}"]
    result["sales_change"] = result[f"sales_{second_year}"] - result[f"sales_{first_year}"]
    return result


def category_location_change_chart(
    data: pd.DataFrame,
    category_totals: pd.DataFrame,
    value_column: str,
    title: str,
) -> alt.Chart:
    category_order = category_totals.sort_values(value_column)["category_updated"].tolist()

    return (
        alt.Chart(data, title=title)
        .mark_bar()
        .encode(
            x=alt.X(value_column, title=None),
            y=alt.Y("category_updated", title=None, sort=category_order),
            color=alt.Color("location_display", title="Location"),
            tooltip=[
                alt.Tooltip("category_updated", title="Category"),
                alt.Tooltip("location_display", title="Location"),
                alt.Tooltip(value_column, title=title, format=",.2f"),
            ],
        )
        .properties(height=max(420, len(category_order) * 28))
    )


def product_sales_change(data: pd.DataFrame, category: str, years: list[str]) -> pd.DataFrame:
    if len(years) < 2:
        return pd.DataFrame()

    first_year, second_year = years[0], years[-1]
    category_data = data[
        (data["category_updated"].eq(category))
        & data["year"].isin([first_year, second_year])
    ]
    summary = (
        category_data.groupby(["Product", "year"], as_index=False)["Product Sales Amount"]
        .sum()
    )
    pivot = summary.pivot(index="Product", columns="year", values="Product Sales Amount").fillna(0)

    result = pd.DataFrame({"Product": pivot.index})
    result[f"sales_{first_year}"] = pivot.get(first_year, 0).to_numpy()
    result[f"sales_{second_year}"] = pivot.get(second_year, 0).to_numpy()
    result["sales_change"] = result[f"sales_{second_year}"] - result[f"sales_{first_year}"]
    result["sales_change_pct"] = result["sales_change"].div(
        result[f"sales_{first_year}"].replace(0, pd.NA)
    )
    return result.sort_values("sales_change")


def change_chart(data: pd.DataFrame, label_column: str, value_column: str, title: str) -> alt.Chart:
    chart_data = data.copy()
    chart_data["direction"] = chart_data[value_column].ge(0).map({True: "Increased", False: "Dropped"})
    return (
        alt.Chart(chart_data, title=title)
        .mark_bar()
        .encode(
            x=alt.X(value_column, title=None),
            y=alt.Y(
                label_column,
                title=None,
                sort=alt.SortField(field=value_column, order="ascending"),
            ),
            color=alt.Color(
                "direction",
                scale=alt.Scale(domain=["Dropped", "Increased"], range=["#c84c4c", "#2f7d5c"]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip(label_column, title=label_column.replace("_", " ").title()),
                alt.Tooltip(value_column, title=title, format=",.2f"),
            ],
        )
        .properties(height=max(360, len(chart_data) * 24))
    )


def format_currency_columns(data: pd.DataFrame) -> pd.DataFrame:
    formatted = data.copy()
    for column in formatted.columns:
        if column.endswith("_pct"):
            formatted[column] = formatted[column].map(
                lambda value: "" if pd.isna(value) else f"{value:.1%}"
            )
        elif column.startswith("sales_") or column == "product_sales" or column == "sales_change":
            formatted[column] = formatted[column].map(lambda value: f"${value:,.2f}")
    return formatted


def main() -> None:
    st.set_page_config(
        page_title="Item Sales Summary",
        page_icon="",
        layout="wide",
    )

    st.title("Item Sales Summary")

    if not DATA_PATH.exists():
        st.error(f"Could not find data file: {DATA_PATH}")
        st.stop()

    data = load_data(DATA_PATH.stat().st_mtime)

    with st.sidebar:
        st.header("Filters")
        locations = sorted(data["location_display"].dropna().unique())
        years = sorted(data["year"].dropna().unique())

        selected_locations = st.multiselect("Location", locations, default=locations)
        selected_years = st.multiselect("Year", years, default=years)
        top_n = st.slider("Top N items", min_value=5, max_value=100, value=20, step=5)
        category_top_n = st.selectbox("Top categories", [10, 20], index=0)
        selected_years = sorted(selected_years)

    filtered = data[
        data["location_display"].isin(selected_locations)
        & data["year"].isin(selected_years)
    ]

    if filtered.empty:
        st.warning("No data matches the selected filters.")
        st.stop()

    total_items_sold = int(filtered["Items Sold"].sum())
    total_product_sales = filtered["Product Sales Amount"].sum()
    unique_products = filtered["Product"].nunique()

    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Total Items Sold", f"{total_items_sold:,}")
    metric_2.metric("Total Product Sales", f"${total_product_sales:,.2f}")
    metric_3.metric("Unique Products", f"{unique_products:,}")

    st.divider()

    category_summary = summarize_by_category(filtered)
    category_sales_summary = category_summary.head(category_top_n)
    category_items, category_sales = st.columns(2)

    with category_items:
        st.subheader(f"Top {category_top_n} Categories by Items Sold")
        st.altair_chart(
            category_chart(
                category_summary.sort_values("items_sold", ascending=False).head(category_top_n),
                "items_sold",
                "Items Sold",
            ),
            width="stretch",
        )

    with category_sales:
        st.subheader(f"Top {category_top_n} Categories by Product Sales")
        st.altair_chart(
            category_chart(category_sales_summary, "product_sales", "Product Sales"),
            width="stretch",
        )

    st.divider()

    product_tab, year_tab, location_tab, table_tab = st.tabs(
        ["Top Products", "Year Comparison", "Location Comparison", "Source Data"]
    )

    with product_tab:
        chart_1, chart_2 = st.columns(2)

        with chart_1:
            st.subheader(f"Top {top_n} Products by Items Sold")
            items_sold = top_products(filtered, "Items Sold", top_n)
            st.altair_chart(
                horizontal_bar_chart(items_sold, "Product", "Items Sold", "Items Sold", ",.0f"),
                width="stretch",
            )

        with chart_2:
            st.subheader(f"Top {top_n} Products by Product Sales")
            product_sales = top_products(filtered, "Product Sales Amount", top_n)
            st.altair_chart(
                horizontal_bar_chart(
                    product_sales,
                    "Product",
                    "Product Sales Amount",
                    "Product Sales",
                ),
                width="stretch",
            )

    with year_tab:
        if len(selected_years) < 2:
            st.info("Select two years in the sidebar to show year comparison.")
        else:
            first_year, second_year = selected_years[0], selected_years[-1]
            st.subheader(f"Category Change: {second_year} vs {first_year}")
            category_change = year_over_year_category(filtered, selected_years)
            category_change_top = top_increase_decrease(category_change, "sales_change", 10)
            category_location_change = year_over_year_category_location(filtered, selected_years)
            category_location_change = category_location_change[
                category_location_change["category_updated"].isin(
                    category_change_top["category_updated"]
                )
            ]
            st.altair_chart(
                category_location_change_chart(
                    category_location_change,
                    category_change_top,
                    "sales_change",
                    "Product Sales Change",
                ),
                width="stretch",
            )
            st.dataframe(
                format_currency_columns(
                    category_change_top.sort_values("sales_change", ascending=False)
                ),
                width="stretch",
                hide_index=True,
                height=360,
            )

            st.subheader("Product Sales Increased and Dropped by Category")
            categories = sorted(filtered["category_updated"].dropna().unique())
            selected_category = st.selectbox("Category", categories)
            product_change = product_sales_change(filtered, selected_category, selected_years)

            dropped, increased = st.columns(2)
            with dropped:
                st.markdown("**Largest Sales Drops**")
                dropped_products = product_change[product_change["sales_change"].lt(0)].head(10)
                st.dataframe(
                    format_currency_columns(dropped_products),
                    width="stretch",
                    hide_index=True,
                    height=420,
                )
            with increased:
                st.markdown("**Largest Sales Increases**")
                increased_products = (
                    product_change[product_change["sales_change"].gt(0)]
                    .sort_values("sales_change", ascending=False)
                    .head(10)
                )
                st.dataframe(
                    format_currency_columns(increased_products),
                    width="stretch",
                    hide_index=True,
                    height=420,
                )

    with location_tab:
        if filtered["location_display"].nunique() < 2:
            st.info("Select at least two locations in the sidebar to compare locations.")
        else:
            st.subheader("Location Comparison by Category")
            location_summary = summarize_by_location_category(filtered)
            top_location_categories = (
                location_summary.groupby("category_updated", as_index=False)["product_sales"]
                .sum()
                .sort_values("product_sales", ascending=False)
                .head(category_top_n)["category_updated"]
            )
            location_summary = location_summary[
                location_summary["category_updated"].isin(top_location_categories)
            ]

            location_items, location_sales = st.columns(2)
            with location_items:
                st.altair_chart(
                    location_category_chart(location_summary, "items_sold", "Items Sold"),
                    width="stretch",
                )
            with location_sales:
                st.altair_chart(
                    location_category_chart(location_summary, "product_sales", "Product Sales"),
                    width="stretch",
                )

            st.subheader("Location Summary")
            location_total = (
                filtered.groupby("location_display", as_index=False)
                .agg(
                    items_sold=("Items Sold", "sum"),
                    product_sales=("Product Sales Amount", "sum"),
                    products=("Product", "nunique"),
                )
                .sort_values("product_sales", ascending=False)
            )
            st.dataframe(
                format_currency_columns(location_total).rename(columns={"location_display": "Location"}),
                width="stretch",
                hide_index=True,
                height=220,
            )

    with table_tab:
        st.subheader("Source Data")
        table_columns = [
            "location_display",
            "year",
            "Item Name",
            "Item Variation",
            "Category",
            "category_updated",
            "Items Sold",
            "Product Sales",
            "Net Sales",
            "Gross Sales",
        ]
        table_data = filtered[table_columns].reset_index(drop=True).rename(
            columns={"location_display": "Location"}
        )
        st.dataframe(
            table_data,
            width="stretch",
            hide_index=True,
            height=620,
        )


if __name__ == "__main__":
    main()
