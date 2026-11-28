"""Regression tests for #4183: an unreadable Memory index is treated as missing.

``iterate`` is compiled out of its source and run against stubs, so no pyRevit
or Revit is needed.
"""

import ast
import pickle
import tempfile
import types
import unittest
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]
ITER_SELECTION = (
    ROOT_DIR
    / "extensions"
    / "pyRevitTools.extension"
    / "pyRevit.tab"
    / "Selection.panel"
    / "memo.stack"
    / "Memory.pulldown"
    / "lib"
    / "iter_selection.py"
)
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"
CROSS_ENGINE_PROTOCOL = 2


def _compile(path, node_type, name, namespace):
    tree = ast.parse(path.read_bytes())
    node = next(n for n in tree.body if isinstance(n, node_type) and n.name == name)
    code = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(code, str(path), "exec"), namespace)
    return namespace[name]


@pytest.mark.regression
class IterateIndexTests(unittest.TestCase):
    """#4183: an unreadable index file is treated like a missing one."""

    def test_unreadable_index_is_rewritten_with_protocol_2(self):
        """A protocol 4 index that the engine cannot read does not block Next."""
        import os.path as op

        with tempfile.TemporaryDirectory() as folder:
            files = {
                "SelListPrevNextIndex": op.join(folder, "index.pym"),
                "SelList": op.join(folder, "list.pym"),
            }
            with open(files["SelList"], "wb") as selection_file:
                pickle.dump({"11", "22"}, selection_file, CROSS_ENGINE_PROTOCOL)
            with open(files["SelListPrevNextIndex"], "wb") as index_file:
                index_file.write(b"\x80\x04unreadable")

            selected = []
            namespace = {
                "op": op,
                "pickle": pickle,
                "revit": types.SimpleNamespace(
                    get_selection=lambda: types.SimpleNamespace(set_to=selected.append)
                ),
                "script": types.SimpleNamespace(
                    get_document_data_file=lambda name, ext: files[name]
                ),
                "get_elementid_from_value": lambda value: value,
                "logger": types.SimpleNamespace(
                    debug=lambda *args: None, error=lambda *args: self.fail(args)
                ),
            }
            iterate = _compile(ITER_SELECTION, ast.FunctionDef, "iterate", namespace)
            iterate("+")
            with open(files["SelListPrevNextIndex"], "rb") as index_file:
                content = index_file.read()
            self.assertEqual(content[:2], b"\x80\x02")
            self.assertEqual(1, len(selected))


if __name__ == "__main__":
    unittest.main()
