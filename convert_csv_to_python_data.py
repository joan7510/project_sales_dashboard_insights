from __future__ import annotations

import csv
import json
import pickle
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "alphago_fitness"
OUTPUT_DIR = ROOT / "python_data"
COMBINED_OUTPUT_DIR = ROOT / "combined_data"
CSV_EXTENSIONS = {".csv", ".cvs"}


def read_csv_file(path: Path) -> dict:
    """Read one CSV/CVS file into a plain Python data object."""
    encodings = ("utf-8-sig", "utf-8", "gb18030", "latin-1")
    last_error: UnicodeDecodeError | None = None

    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as file:
                sample = file.read(4096)
                file.seek(0)

                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel

                reader = csv.DictReader(file, dialect=dialect)
                rows = []
                for row in reader:
                    row.pop(None, None)
                    rows.append(row)

            return {
                "source_csv": str(path.relative_to(ROOT)),
                "encoding": encoding,
                "columns": reader.fieldnames or [],
                "row_count": len(rows),
                "rows": rows,
            }
        except UnicodeDecodeError as error:
            last_error = error

    raise UnicodeDecodeError(
        last_error.encoding if last_error else "unknown",
        last_error.object if last_error else b"",
        last_error.start if last_error else 0,
        last_error.end if last_error else 1,
        f"Could not decode {path}",
    )


def output_path_for(csv_path: Path) -> Path:
    relative_path = csv_path.relative_to(INPUT_DIR).with_suffix(".pkl")
    return OUTPUT_DIR / relative_path


def source_details(csv_path: Path) -> dict:
    relative_path = csv_path.relative_to(INPUT_DIR)
    location = relative_path.parts[0]
    year = extract_year(csv_path)

    return {
        "location": location,
        "year": year,
    }


def extract_year(csv_path: Path) -> str:
    text = str(csv_path)

    date_match = re.search(r"(20\d{2})-\d{2}-\d{2}-(20\d{2})-\d{2}-\d{2}", text)
    if date_match:
        return f"{date_match.group(1)}-{date_match.group(2)}"

    short_year_match = re.search(r"(?<!\d)(\d{2})[-_](\d{2})(?!\d)", text)
    if short_year_match:
        start_year = 2000 + int(short_year_match.group(1))
        end_year = 2000 + int(short_year_match.group(2))
        return f"{start_year}-{end_year}"

    return "unknown"


def dataset_name_for(columns: list[str], source_files: list[str]) -> str:
    joined_files = " ".join(source_files).lower()

    if "item-sales-summary" in joined_files:
        return "item_sales_summary"
    if "transactions" in joined_files:
        return "transactions"
    if "orders_export" in joined_files:
        return "online_orders"
    if any(column == "Item" for column in columns) and any(column == "Transaction ID" for column in columns):
        return "items"

    first_column = columns[0] if columns else "data"
    return slugify(first_column)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "data"


def unique_output_name(base_name: str, used_names: set[str]) -> str:
    name = base_name
    suffix = 2
    while name in used_names:
        name = f"{base_name}_{suffix}"
        suffix += 1
    used_names.add(name)
    return name


def write_combined_files(index: list[dict], data_by_csv: dict[str, dict]) -> list[dict]:
    COMBINED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    groups: dict[tuple[str, ...], list[dict]] = {}
    for item in index:
        columns_key = tuple(item["columns"])
        groups.setdefault(columns_key, []).append(item)

    combined_index = []
    used_names: set[str] = set()

    for columns_key, source_items in sorted(groups.items(), key=lambda group: group[1][0]["csv_file"]):
        columns = list(columns_key)
        source_files = [item["csv_file"] for item in source_items]
        base_name = dataset_name_for(columns, source_files)
        if len(source_items) == 1:
            base_name = f"{base_name}_{source_items[0]['location']}_{source_items[0]['year']}"
        output_name = unique_output_name(slugify(base_name), used_names)

        rows = []
        for item in source_items:
            data = data_by_csv[item["csv_file"]]
            for row in data["rows"]:
                combined_row = {
                    "location": item["location"],
                    "year": item["year"],
                    **row,
                }
                rows.append(combined_row)

        combined_data = {
            "dataset": output_name,
            "columns": ["location", "year", *columns],
            "row_count": len(rows),
            "source_files": source_files,
            "rows": rows,
        }

        pkl_path = COMBINED_OUTPUT_DIR / f"{output_name}.pkl"
        csv_path = COMBINED_OUTPUT_DIR / f"{output_name}.csv"

        with pkl_path.open("wb") as file:
            pickle.dump(combined_data, file)

        with csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=combined_data["columns"])
            writer.writeheader()
            writer.writerows(rows)

        combined_index.append(
            {
                "dataset": output_name,
                "python_data_file": str(pkl_path.relative_to(ROOT)),
                "csv_file": str(csv_path.relative_to(ROOT)),
                "source_files": source_files,
                "source_file_count": len(source_files),
                "row_count": len(rows),
                "columns": combined_data["columns"],
            }
        )
        print(f"Combined {len(source_files)} file(s) -> {pkl_path.relative_to(ROOT)}")

    combined_index_path = COMBINED_OUTPUT_DIR / "index.json"
    with combined_index_path.open("w", encoding="utf-8") as file:
        json.dump(combined_index, file, ensure_ascii=False, indent=2)

    return combined_index


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(
        path
        for path in INPUT_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in CSV_EXTENSIONS
    )

    index = []
    data_by_csv = {}
    for csv_path in csv_files:
        data = read_csv_file(csv_path)
        details = source_details(csv_path)
        pkl_path = output_path_for(csv_path)
        pkl_path.parent.mkdir(parents=True, exist_ok=True)

        with pkl_path.open("wb") as file:
            pickle.dump(data, file)

        index.append(
            {
                "csv_file": data["source_csv"],
                "python_data_file": str(pkl_path.relative_to(ROOT)),
                "location": details["location"],
                "year": details["year"],
                "columns": data["columns"],
                "row_count": data["row_count"],
                "encoding": data["encoding"],
            }
        )
        data_by_csv[data["source_csv"]] = data
        print(f"Saved {data['source_csv']} -> {pkl_path.relative_to(ROOT)}")

    index_path = OUTPUT_DIR / "index.json"
    with index_path.open("w", encoding="utf-8") as file:
        json.dump(index, file, ensure_ascii=False, indent=2)

    combined_index = write_combined_files(index, data_by_csv)

    print(f"\nConverted {len(index)} file(s). Index saved to {index_path.relative_to(ROOT)}")
    print(
        f"Created {len(combined_index)} combined file(s). "
        f"Index saved to {COMBINED_OUTPUT_DIR.relative_to(ROOT) / 'index.json'}"
    )


if __name__ == "__main__":
    main()
