"""Regression tests for the CPython Excel interop backend."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "site-packages"))

pyrevit = types.ModuleType("pyrevit")
compat = types.ModuleType("pyrevit.compat")
compat.PY3 = True
pyrevit.compat = compat
sys.modules["pyrevit"] = pyrevit
sys.modules["pyrevit.compat"] = compat

spec = importlib.util.spec_from_file_location(
    "test_excel_interop_module", REPO_ROOT / "pyrevitlib/pyrevit/interop/xl.py"
)
xl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xl)


class ExcelInteropTests(unittest.TestCase):
    """The CPython backend round-trips worksheet values through openpyxl."""

    def test_dump_and_load_rows_and_headers(self):
        """Written workbook data has the same worksheet, header, and row values."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.xlsx"
            xl.dump(path, {"Rows": [["Name", "Count"], ["A", 1]]})
            loaded = xl.load(path)

        self.assertEqual(["Name", "Count"], loaded["Rows"]["headers"])
        self.assertEqual([["A", 1]], loaded["Rows"]["rows"])

    def test_load_can_name_columns(self):
        """Column names continue to map each worksheet row to a dictionary."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "columns.xlsx"
            xl.dump(path, {"Rows": [["A", 1]]})
            loaded = xl.load(path, columns=["name", "count"], headers=False)

        self.assertEqual([{"name": "A", "count": 1}], loaded["Rows"]["rows"])


if __name__ == "__main__":
    unittest.main()
