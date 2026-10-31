"""Count bundled-tool references to forms APIs without importing Revit."""

import ast
from collections import defaultdict
import json
from pathlib import Path
import re
from xml.dom import minidom


_NON_EVENT_ATTRIBUTES = {"DisplayMemberPath"}
_CPYTHON_MODAL_ONLY = set()
_CPYTHON_HOST_REQUIRED = set()
_CPYTHON_UNSUPPORTED = set()
_TEMPLATES = {
    "ControlTemplate",
    "DataTemplate",
    "HierarchicalDataTemplate",
    "ItemsPanelTemplate",
    "Style",
}
_TEMPLATE_DIRECT_EVENTS = {
    "Loaded",
    "Unloaded",
    "SizeChanged",
    "MouseEnter",
    "MouseLeave",
    "IsVisibleChanged",
}


def _in_template(node):
    parent = node.parentNode
    while parent is not None and parent.nodeType == parent.ELEMENT_NODE:
        if parent.localName in _TEMPLATES:
            return True
        parent = parent.parentNode
    return False


def _child_data_context_assignments(root):
    """Return bundled scripts that set a child control's DataContext directly.

    Under CPython a Python model reaches WPF unadapted that way; scripts must
    call ``forms.set_data_context`` instead.
    """
    found = []
    for path in sorted((root / "extensions").rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "DataContext"
                    and isinstance(target.value, ast.Attribute)
                ):
                    found.append("{}:{}".format(path.relative_to(root), node.lineno))
    return found


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


def _cpython_exports(root):
    tree = ast.parse(
        (root / "pyrevitlib" / "pyrevit" / "forms" / "_common.py").read_text(
            encoding="utf-8"
        )
    )
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    )
    return set(ast.literal_eval(assignment.value)) | {
        "settings_window",
        "utils",
        "toaster",
    }


def _xaml_event_audit(root):
    deferred = _deferred_events(root)
    supported = []
    unsupported = []
    template_direct = []
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
                if attribute.name in _TEMPLATE_DIRECT_EVENTS and _in_template(node):
                    template_direct.append(record)
                if attribute.name in deferred:
                    supported.append(record)
                else:
                    unsupported.append(record)
    return {
        "handler_count": len(supported) + len(unsupported),
        "supported": supported,
        "unsupported": unsupported,
        "template_direct": template_direct,
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
    references = {name: sorted(paths) for name, paths in sorted(references.items())}
    exports = _cpython_exports(root)
    modal_only = {
        name: paths for name, paths in references.items() if name in _CPYTHON_MODAL_ONLY
    }
    host_required = {
        name: paths
        for name, paths in references.items()
        if name in _CPYTHON_HOST_REQUIRED
    }
    supported = {
        name: paths
        for name, paths in references.items()
        if name in exports
        and name not in _CPYTHON_MODAL_ONLY
        and name not in _CPYTHON_HOST_REQUIRED
        and name not in _CPYTHON_UNSUPPORTED
    }
    unsupported = {
        name: paths
        for name, paths in references.items()
        if name not in exports or name in _CPYTHON_UNSUPPORTED
    }
    return {
        "references": {name: paths for name, paths in references.items()},
        "skipped": skipped,
        "xaml_events": _xaml_event_audit(root),
        "cpython_hazards": {
            "child_data_context": _child_data_context_assignments(root),
        },
        "cpython": {
            "supported_references": sum(len(paths) for paths in supported.values()),
            "modal_only_references": sum(len(paths) for paths in modal_only.values()),
            "host_required_references": sum(
                len(paths) for paths in host_required.values()
            ),
            "unsupported_references": sum(len(paths) for paths in unsupported.values()),
            "supported": supported,
            "modal_only": modal_only,
            "host_required": host_required,
            "unsupported": unsupported,
        },
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
                "cpython_supported_references": report["cpython"][
                    "supported_references"
                ],
                "cpython_unsupported_references": report["cpython"][
                    "unsupported_references"
                ],
                "cpython_host_required_references": report["cpython"][
                    "host_required_references"
                ],
                "cpython_modal_only_references": report["cpython"][
                    "modal_only_references"
                ],
                "cpython_modal_only_apis": report["cpython"]["modal_only"],
                "cpython_host_required_apis": report["cpython"]["host_required"],
                "cpython_unsupported_apis": report["cpython"]["unsupported"],
            },
            indent=2,
        )
    )
