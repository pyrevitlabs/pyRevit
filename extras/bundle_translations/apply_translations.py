import csv
from pathlib import Path
from ruamel.yaml import YAML  # pip install ruamel.yaml

# -------- CONFIG --------
TRANSLATION_CSV = r"C:\temp\translations.csv"
LANGUAGE_KEY = "chinese_s"
SOURCE_LANG = "en_us"
# ------------------------

yaml = YAML()


def build_lookup(csv_path):
    """Build dictionary: {yaml_file: {key_type: {"en_us":..., "translation":...}}}"""
    lookup = {}

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            file = row["yaml_file"]
            key = row["key_type"]

            en = row[SOURCE_LANG]
            tr = row[LANGUAGE_KEY]

            lookup.setdefault(file, {}).setdefault(key, {})
            lookup[file][key] = {"en": en, "tr": tr}

    return lookup


def insert_translation(data, key_type, trans, node_path=""):
    """Insert translation from CSV.
       Rule: write ONLY if CSV provides a non-empty translation; always overwrite."""
    if not isinstance(data, dict):
        return

    translation = trans["tr"].strip()

    if key_type in data:
        value = data[key_type]

        # CASE A: scalar -> convert to dict
        if isinstance(value, str):
            print(f"[Scalar detected during import] {node_path}/{key_type} | Converting to multilingual")
            new_dict = {SOURCE_LANG: value}

            if translation:
                new_dict[LANGUAGE_KEY] = translation
                print(f"[Write] {node_path}/{key_type} | {LANGUAGE_KEY} = '{translation}'")
            else:
                print(f"[Skip] CSV translation empty for {node_path}/{key_type}")

            data[key_type] = new_dict
            return

        # CASE B: dict
        elif isinstance(value, dict):
            # ensure en_us exists
            if SOURCE_LANG not in value:
                if len(value):
                    first_key = next(iter(value.keys()))
                    value[SOURCE_LANG] = value[first_key]
                    print(f"[Promotion] No {SOURCE_LANG} → using '{first_key}' value")

            # write only if CSV translation provided
            if translation:
                value[LANGUAGE_KEY] = translation
                print(f"[Write] {node_path}/{key_type} | Overwriting {LANGUAGE_KEY} = '{translation}'")
            else:
                print(f"[Skip] CSV translation empty for {node_path}/{key_type}")

    # recurse deeper
    for k, v in data.items():
        child_path = f"{node_path}/{k}" if node_path else k
        insert_translation(v, key_type, trans, child_path)


def main():
    lookup = build_lookup(TRANSLATION_CSV)

    for yaml_file, fields in lookup.items():
        yaml_file = Path(yaml_file)

        if not yaml_file.exists():
            print(f"[Missing] {yaml_file}")
            continue

        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.load(f)

            for key_type, trans in fields.items():
                insert_translation(data, key_type, trans)

            with open(yaml_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f)

            print(f"[Updating] {yaml_file}")

        except Exception as e:
            print(f"[ERROR] writing {yaml_file}: {e}")


if __name__ == "__main__":
    main()
