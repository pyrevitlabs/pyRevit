"""Count bundled-tool references to forms APIs without importing Revit."""

import ast
from collections import defaultdict
import json
from pathlib import Path


def inventory(root):
    """Return API-to-file references and files requiring manual syntax review."""
    references = defaultdict(set)
    skipped = []
    for path in sorted((root / "extensions").rglob("*.py")):
        if "pyRevitDevTools.extension" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeError):
            skipped.append(str(path.relative_to(root)))
            continue
        aliases = {"forms"}
        direct = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "pyrevit":
                    aliases.update(
                        item.asname or item.name
                        for item in node.names
                        if item.name == "forms"
                    )
                elif node.module == "pyrevit.forms":
                    direct.update(
                        (item.asname or item.name, item.name)
                        for item in node.names
                        if item.name != "*"
                    )
            elif isinstance(node, ast.Import):
                aliases.update(
                    item.asname
                    for item in node.names
                    if item.name == "pyrevit.forms" and item.asname
                )
        for node in ast.walk(tree):
            name = None
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in aliases
            ):
                name = node.attr
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                name = direct.get(node.id)
            if name:
                references[name].add(str(path.relative_to(root)))
    return {
        "references": {
            name: sorted(paths) for name, paths in sorted(references.items())
        },
        "skipped": skipped,
    }


if __name__ == "__main__":
    report = inventory(Path(__file__).resolve().parents[2])
    print(
        json.dumps(
            {
                "counts": {
                    name: len(paths) for name, paths in report["references"].items()
                },
                "skipped": report["skipped"],
            },
            indent=2,
        )
    )
