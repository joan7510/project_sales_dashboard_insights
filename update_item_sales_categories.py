from __future__ import annotations

import difflib
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "combined_data" / "item_sales_summary.csv"
BACKUP_PATH = ROOT / "combined_data" / "item_sales_summary_before_category_update.csv"
REVIEW_PATH = ROOT / "combined_data" / "category_update_review_needed.csv"
MATCH_THRESHOLD = 0.60


SPECIAL_CATEGORIES = {
    "installation fee": "fee",
    "garage delivery": "fee",
    "custom amount": "other",
}


def normalize_name(value: object) -> str:
    text = str(value).lower()
    text = re.sub(r"pre[- ]?order", " ", text)
    text = re.sub(r"eta\s+[a-z]+\s*[a-z]*", " ", text)
    text = re.sub(r"regular|no description", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def best_existing_category(data: pd.DataFrame) -> dict[str, str]:
    categorized = data[data["Category"].ne("Uncategorised")]
    category_by_item = {}

    for item_name, group in categorized.groupby("Item Name"):
        category_by_item[item_name] = group["Category"].mode().iat[0]

    return category_by_item


def fuzzy_match_category(item_name: str, references: list[dict]) -> dict:
    normalized_item = normalize_name(item_name)
    best_match = {
        "category": "Uncategorised",
        "matched_item_name": "",
        "match_score": 0.0,
    }

    for reference in references:
        score = difflib.SequenceMatcher(
            None,
            normalized_item,
            reference["normalized_item_name"],
        ).ratio()

        if score > best_match["match_score"]:
            best_match = {
                "category": reference["category"],
                "matched_item_name": reference["item_name"],
                "match_score": score,
            }

    return best_match


def update_categories(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    updated = data.copy()
    updated["category_updated"] = updated["Category"]
    updated["category_update_method"] = "original"
    updated["category_match_score"] = pd.NA
    updated["category_matched_item_name"] = ""

    category_by_item = best_existing_category(updated)
    references = [
        {
            "item_name": item_name,
            "normalized_item_name": normalize_name(item_name),
            "category": category,
        }
        for item_name, category in category_by_item.items()
    ]

    review_rows = []
    uncategorised_mask = updated["Category"].eq("Uncategorised")

    for index, row in updated[uncategorised_mask].iterrows():
        item_name = row["Item Name"]
        normalized_item = normalize_name(item_name)

        if normalized_item in SPECIAL_CATEGORIES:
            updated.at[index, "category_updated"] = SPECIAL_CATEGORIES[normalized_item]
            updated.at[index, "category_update_method"] = "manual_rule"
            continue

        if item_name in category_by_item:
            updated.at[index, "category_updated"] = category_by_item[item_name]
            updated.at[index, "category_update_method"] = "exact_item_name"
            updated.at[index, "category_match_score"] = 1.0
            updated.at[index, "category_matched_item_name"] = item_name
            continue

        match = fuzzy_match_category(item_name, references)
        updated.at[index, "category_match_score"] = round(match["match_score"], 3)
        updated.at[index, "category_matched_item_name"] = match["matched_item_name"]

        if match["match_score"] >= MATCH_THRESHOLD:
            updated.at[index, "category_updated"] = match["category"]
            updated.at[index, "category_update_method"] = "fuzzy_item_name"
        else:
            updated.at[index, "category_update_method"] = "review_needed"
            review_rows.append(
                {
                    "Item Name": item_name,
                    "Item Variation": row["Item Variation"],
                    "location": row["location"],
                    "year": row["year"],
                    "suggested_category": match["category"],
                    "match_score": round(match["match_score"], 3),
                    "matched_item_name": match["matched_item_name"],
                }
            )

    review = pd.DataFrame(review_rows).drop_duplicates()
    return updated, review


def main() -> None:
    data = pd.read_csv(DATA_PATH)

    if not BACKUP_PATH.exists():
        data.to_csv(BACKUP_PATH, index=False)

    updated, review = update_categories(data)
    updated.to_csv(DATA_PATH, index=False)
    review.to_csv(REVIEW_PATH, index=False)

    print(f"Updated {DATA_PATH.relative_to(ROOT)}")
    print(f"Backup saved to {BACKUP_PATH.relative_to(ROOT)}")
    print(f"Review file saved to {REVIEW_PATH.relative_to(ROOT)}")
    print()
    print(updated["category_update_method"].value_counts().to_string())


if __name__ == "__main__":
    main()
