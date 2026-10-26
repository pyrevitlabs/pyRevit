"""Count bundled-tool references to forms APIs without importing Revit."""

import ast
from collections import defaultdict
import json
from pathlib import Path
import re
from xml.dom import minidom


_NON_EVENT_ATTRIBUTES = {"DisplayMemberPath"}


def _deferred_events(root):
    tree = ast.parse(
        (root / "pyrevitlib" / "pyrevit" / "forms" / "_xaml.py").read_text(
            encoding="utf-8"
        )
    )
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_EVENTS"
            for target in node.targets
        )
    )
    return set(ast.literal_eval(assignment.value))


def _xaml_event_audit(root):
    deferred = _deferred_events(root)
    supported = []
    unsupported = []
    unparsed = []
    for path in sorted((root / "extensions").rglob("*.xaml")):
        if "pyRevitDevTools.extension" in path.parts:
            continue
        handlers = set()
        for script in path.parent.glob("*.py"):
            handlers.update(
                re.findall(
                    r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                    script.read_text(encoding="utf-8-sig"),
                    re.MULTILINE,
                )
            )
        if not handlers:
            continue
        try:
            document = minidom.parse(str(path))
        except Exception:
            unparsed.append(str(path.relative_to(root)))
            continue
        for node in document.getElementsByTagName("*"):
            for index in range(node.attributes.length):
                attribute = node.attributes.item(index)
                if (
                    attribute.name in _NON_EVENT_ATTRIBUTES
                    or attribute.value not in handlers
                ):
                    continue
                record = (str(path.relative_to(root)), attribute.name, attribute.value)
                if attribute.name in deferred:
                    supported.append(record)
                else:
                    unsupported.append(record)
    return {
        "handler_count": len(supported) + len(unsupported),
        "supported": supported,
        "unsupported": unsupported,
        "unparsed": unparsed,
    }


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
        "xaml_events": _xaml_event_audit(root),
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
                "xaml_event_handlers": report["xaml_events"]["handler_count"],
                "unsupported_xaml_events": report["xaml_events"]["unsupported"],
                "unparsed_xaml": report["xaml_events"]["unparsed"],
            },
            indent=2,
        )
    )
