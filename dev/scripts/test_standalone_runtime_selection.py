"""Portable tests for how ``pyrevit.runtime`` picks an already loaded runtime."""

import ast
from pathlib import Path
import unittest


RUNTIME = (
    Path(__file__).resolve().parents[2]
    / "pyrevitlib"
    / "pyrevit"
    / "runtime"
    / "__init__.py"
)


def _select():
    tree = ast.parse(RUNTIME.read_text(encoding="utf-8"))
    tree.body = [
        node
        for node in tree.body
        if getattr(node, "name", None) == "_select_year_runtime"
        or (
            isinstance(node, ast.Assign)
            and any(
                getattr(target, "id", None) == "RUNTIME_NAMESPACE"
                for target in node.targets
            )
        )
    ]
    scope = {"safe_strtype": str}
    exec(compile(tree, str(RUNTIME), "exec"), scope)
    return lambda names: scope["_select_year_runtime"](names, lambda name: name)


class SelectYearRuntimeTests(unittest.TestCase):
    """The runner's single per-year runtime is reused; anything else is not."""

    def test_single_year_runtime_is_selected(self):
        """The runner loads one year's runtime, which may not be the host year's."""
        names = [
            "pyRevitLabs.PyRevit.Runtime.Shared",
            "pyRevitLabs.PyRevit.Runtime.2021",
            "RevitAPI",
        ]
        self.assertEqual(["pyRevitLabs.PyRevit.Runtime.2021"], _select()(names))

    def test_several_year_runtimes_are_ambiguous(self):
        """With several years loaded, none is picked."""
        names = ["pyRevitLabs.PyRevit.Runtime.2025", "pyRevitLabs.PyRevit.Runtime.2026"]
        self.assertEqual([], _select()(names))

    def test_shared_and_unrelated_assemblies_are_ignored(self):
        """The shared runtime and lookalike names are not per-year runtimes."""
        names = [
            "pyRevitLabs.PyRevit.Runtime.Shared",
            "pyRevitLabs.PyRevit.Runtime.",
            "pyRevitLabs.PyRevit.Runtime.2026.Extra",
            "pyRevitLabs.PyRevit.Runtime",
        ]
        self.assertEqual([], _select()(names))


if __name__ == "__main__":
    unittest.main()
