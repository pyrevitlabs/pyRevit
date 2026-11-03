"""Validate the third-party extension catalog before it reaches users.

`extensions/extensions.json` is published to `master` by the catalog-publish
workflow without a release, and the Extension Manager and CLI download it from
there. A malformed entry would therefore reach every installed pyRevit at once,
so this check gates both the pull request and the publish job.

Invariant:
    The rules here must stay a superset of what
    `pyrevit.extensions.extcatalog.parse_catalog` accepts on the client, so a
    catalog that passes CI is never rejected by an installed pyRevit.

Exit code is 0 when the catalog is valid, 1 otherwise; every problem found is
printed, one per line.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = REPO_ROOT / "extensions" / "extensions.json"

REQUIRED_FIELDS = (
    "name",
    "type",
    "description",
    "author",
    "url",
    "builtin",
    "rocket_mode_compatible",
    "dependencies",
)
EXTENSION_TYPES = ("extension", "lib")
BOOLEAN_STRINGS = ("True", "False", "true", "false")
FLAG_FIELDS = ("builtin", "rocket_mode_compatible", "default_enabled")
NAME_LIST_FIELDS = ("dependencies", "authusers", "authgroups")
WEB_LINK_FIELDS = ("website", "image", "author_profile", "author-url")


def _check_entry(index, entry):
    label = "entry #{}".format(index)
    if not isinstance(entry, dict):
        return ["{}: must be an object".format(label)]

    name = entry.get("name")
    if isinstance(name, str) and name.strip():
        label = "entry #{} ({})".format(index, name)

    problems = [
        "{}: missing '{}'".format(label, field)
        for field in REQUIRED_FIELDS
        if field not in entry
    ]

    for field in ("name", "description", "author", "url"):
        value = entry.get(field)
        if field in entry and (not isinstance(value, str) or not value.strip()):
            problems.append("{}: '{}' must be a non-empty string".format(label, field))

    url = entry.get("url")
    if isinstance(url, str) and url.strip() and not url.startswith("https://"):
        problems.append("{}: 'url' must start with https://".format(label))

    if "type" in entry and entry["type"] not in EXTENSION_TYPES:
        problems.append(
            "{}: 'type' must be one of {}".format(label, ", ".join(EXTENSION_TYPES))
        )

    for field in FLAG_FIELDS:
        if field in entry and entry[field] not in BOOLEAN_STRINGS:
            problems.append(
                '{}: \'{}\' must be the string "True" or "False"'.format(label, field)
            )

    for field in NAME_LIST_FIELDS:
        value = entry.get(field)
        if field in entry and not (
            isinstance(value, list) and all(isinstance(item, str) for item in value)
        ):
            problems.append("{}: '{}' must be a list of names".format(label, field))

    for field in WEB_LINK_FIELDS:
        if field not in entry:
            continue
        value = entry[field]
        if not isinstance(value, str) or (
            value and not value.startswith(("https://", "http://"))
        ):
            problems.append("{}: '{}' must be an http(s) link".format(label, field))

    return problems


def check_catalog(catalog):
    """Return every problem found in a parsed catalog.

    Args:
        catalog: the decoded content of `extensions.json`.

    Returns:
        (list[str]): human-readable problems; empty when the catalog is valid.
    """
    if not isinstance(catalog, dict) or not isinstance(catalog.get("extensions"), list):
        return ["catalog must be an object with an 'extensions' list"]

    entries = catalog["extensions"]
    problems = []
    if not entries:
        problems.append("catalog must contain at least one entry")
    for index, entry in enumerate(entries):
        problems.extend(_check_entry(index, entry))

    seen = {}
    for entry in entries:
        name = entry.get("name") if isinstance(entry, dict) else None
        if isinstance(name, str) and name.strip():
            key = name.strip().lower()
            if key in seen:
                problems.append(
                    "duplicate name '{}' (also '{}')".format(name, seen[key])
                )
            else:
                seen[key] = name

    exact_names = set(seen.values())
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(
            entry.get("dependencies"), list
        ):
            continue
        for dependency in entry["dependencies"]:
            if isinstance(dependency, str) and dependency not in exact_names:
                problems.append(
                    "{}: dependency '{}' is not in the catalog".format(
                        entry.get("name"), dependency
                    )
                )

    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("catalog", nargs="?", default=str(DEFAULT_CATALOG))
    args = parser.parse_args(argv)

    try:
        catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    except (OSError, ValueError) as read_err:
        print("cannot read {}: {}".format(args.catalog, read_err))
        return 1

    problems = check_catalog(catalog)
    for problem in problems:
        print(problem)
    if problems:
        return 1

    print("{}: {} entries, valid".format(args.catalog, len(catalog["extensions"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
