"""Check the engine versions the About window shows without loading Revit."""

import ast
from pathlib import Path
import types
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "extensions/pyRevitCore.extension/pyRevit.tab"
    / "pyRevit.panel/About.pushbutton/aboutscript.py"
)


def _load_functions(**names):
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    namespace = dict(names)
    exec(
        compile(ast.Module(body=functions, type_ignores=[]), str(SCRIPT), "exec"),
        namespace,
    )
    return namespace


class FormatEngineVersionTests(unittest.TestCase):
    """Engine version codes and dotted versions become ``major.minor.patch``."""

    def setUp(self):
        self.format = _load_functions()["_format_engine_version"]

    def test_version_codes_split_into_major_minor_patch(self):
        self.assertEqual("2.7.12", self.format("2712"))
        self.assertEqual("3.4.2", self.format("342"))
        self.assertEqual("2.7.12", self.format(2712))

    def test_dotted_versions_keep_three_parts(self):
        self.assertEqual("3.4.2", self.format("3.4.2"))
        self.assertEqual("2.7.12", self.format("2.7.12.0"))


if __name__ == "__main__":
    unittest.main()
