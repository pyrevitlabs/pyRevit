"""Extract translation strings from pyRevit bundle YAML files.

This script scans bundle.yaml files for title and tooltip fields,
extracting English source text and any existing translations to a CSV file
for easier translation workflow.

Configuration:
    BASE_DIR: Root directory containing bundle YAML files
    OUTPUT_CSV: Path where the CSV file will be written
    LANGUAGE_KEY: Translation language key (e.g., 'chinese_s')
    SOURCE_LANG: Source language key (default: 'en_us')
"""

import os
from pathlib import Path
from ruamel.yaml import YAML  # pip install ruamel.yaml
import csv

# -------- CONFIG --------
BASE_DIR = r"C:\Program Files\pyRevit-Master\extensions\pyRevitTools.extension"  # adjust for custom installation
OUTPUT_CSV = r"C:\temp\translations.csv"  # same path as in other script
LANGUAGE_KEY = "chinese_s"  # translation key to extract/merge
SOURCE_LANG = "en_us"  # main source language
ONLY_EXPORT_MISSING = False
# ------------------------

yaml = YAML()


def find_yaml_files(base_dir):
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.endswith(".yaml"):
                yield Path(root) / f


def extract_field(path, field_name, value, results):
    """Extracts English + existing translated value from dict or scalar."""
    # CASE 1: multilingual dict
    if isinstance(value, dict):
        # English (preferred)
        en = value.get(SOURCE_LANG)

        # fallback to first language if no en_us exists
        if not en and len(value):
            first_key = next(iter(value.keys()))
            en = value[first_key]

        # Existing translation
        tr = value.get(LANGUAGE_KEY, "")

        if ONLY_EXPORT_MISSING and tr:
            return  # Skip entries that are already translated

        if en:
            results.append([path, field_name, en, tr])
        return

    # CASE 2: scalar string
    if isinstance(value, str):
        print(
            f"[Scalar detected] File: {path} | Field: {field_name} | Value: '{value}'"
        )

        # Scalars always represent untranslated values, so always export.
        # (Translation tr = "")
        results.append([path, field_name, value, ""])
        return


def extract_values(data, path, results):
    """Recursively walk through structure and extract fields."""
    if not isinstance(data, dict):
        return

    for field_name in ("title", "tooltip"):
        if field_name in data:
            extract_field(path, field_name, data[field_name], results)

    # recurse into children
    for k, v in data.items():
        child_path = f"{path}/{k}"
        extract_values(v, child_path, results)


def main():
    results = []

    for yaml_file in find_yaml_files(BASE_DIR):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.load(f)

            extract_values(data, str(yaml_file), results)

        except Exception as e:
            print(f"ERROR reading {yaml_file}: {e}")

    # write CSV
    output_dir = os.path.dirname(OUTPUT_CSV)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["yaml_file", "key_type", SOURCE_LANG, LANGUAGE_KEY])
        for row in results:
            writer.writerow(row)

    print(f"\nExtracted {len(results)} records to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
