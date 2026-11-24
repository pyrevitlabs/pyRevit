"""Check the pyRevit version string formatting without loading Revit."""

import ast
from pathlib import Path
import re
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

MODULE = (
    Path(__file__).resolve().parents[4] / "pyrevitlib/pyrevit/versionmgr/__init__.py"
)


def _load_version_class():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    nodes = [
        node
        for node in tree.body
        if (
            isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and node.name in ("_PyRevitVersion", "parse_version_string")
        )
        or (
            isinstance(node, ast.Assign)
            and [getattr(target, "id", None) for target in node.targets]
            == ["VERSION_REGEX"]
        )
    ]
    namespace = {
        "re": re,
        "safe_strtype": str,
        "VERSION_MAJOR": 0,
        "VERSION_MINOR": 0,
        "VERSION_PATCH": 0,
        "BUILD_METADATA": "",
    }
    exec(
        compile(ast.Module(body=nodes, type_ignores=[]), str(MODULE), "exec"),
        namespace,
    )
    return namespace["_PyRevitVersion"]


class ExtendedFormatTests(unittest.TestCase):
    """Extended reporting appends the commit signature only when there is one."""

    def setUp(self):
        self.version_class = _load_version_class()

    def test_signature_is_appended_and_shortened(self):
        version = self.version_class("abcdef0123456789", "9.9.9.99999+9999")
        self.assertEqual(
            "9.9.9.99999+9999:abcdef0", version.get_formatted(extended=True)
        )

    def test_no_dangling_separator_without_a_repo(self):
        version = self.version_class("", "9.9.9.99999+9999")
        self.assertEqual("9.9.9.99999+9999", version.get_formatted(extended=True))

    def test_none_signature_leaves_no_separator(self):
        version = self.version_class(None, "9.9.9.99999+9999")
        self.assertEqual("9.9.9.99999+9999", version.get_formatted(extended=True))

    def test_strict_ignores_the_signature(self):
        version = self.version_class("abcdef0123456789", "9.9.9.99999+9999")
        self.assertEqual("9.9.9", version.get_formatted(strict=True, extended=True))


if __name__ == "__main__":
    unittest.main()
