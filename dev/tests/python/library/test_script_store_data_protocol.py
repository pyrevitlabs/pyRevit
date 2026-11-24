"""Regression tests for issue 4183: script.store_data writes cross-engine pickles.

``store_data`` is compiled out of ``script.py`` and run against stubs, so no
pyRevit, Revit or ``clr`` is needed.
"""

import ast
import os.path as op
import pickle
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = str(Path(__file__).resolve().parents[4])
SCRIPT_MODULE = op.join(ROOT_DIR, "pyrevitlib", "pyrevit", "script.py")
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"
IRONPYTHON_27_MAX_PROTOCOL = 2


def _load_store_data(data_file):
    with open(SCRIPT_MODULE, "rb") as source_file:
        tree = ast.parse(source_file.read())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "store_data":
            module = ast.Module(body=[node], type_ignores=[])
            namespace = {
                "pickle": pickle,
                "DATAFEXT": "dat",
                "get_document_data_file": lambda **kwargs: data_file,
                "get_data_file": lambda **kwargs: data_file,
            }
            exec(
                compile(ast.fix_missing_locations(module), SCRIPT_MODULE, "exec"),
                namespace,
            )
            return namespace["store_data"]
    raise AssertionError("store_data not found")


class StoreDataProtocolTests(unittest.TestCase):
    """Issue 4183: files must stay readable by IronPython 2.7."""

    def test_store_data_writes_protocol_2(self):
        """The stored file starts with the protocol 2 marker and round-trips."""
        with tempfile.TemporaryDirectory() as folder:
            data_file = op.join(folder, "slot.dat")
            _load_store_data(data_file)("slot", {"a": [1, 2]})
            with open(data_file, "rb") as written:
                content = written.read()
            self.assertEqual(content[:2], b"\x80\x02")
            self.assertEqual(pickle.loads(content), {"a": [1, 2]})


if __name__ == "__main__":
    unittest.main()
