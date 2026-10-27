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
compat.IRONPY = False
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

    def test_empty_dump_still_writes_a_workbook(self):
        """An export with no worksheets keeps one empty default sheet."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.xlsx"
            xl.dump(path, {})
            loaded = xl.load(path)

        self.assertEqual(1, len(loaded))
        self.assertEqual({"headers": [], "rows": []}, list(loaded.values())[0])

    def test_legacy_xls_workbooks_still_load(self):
        """Legacy .xls files are read with xlrd because openpyxl rejects them."""
        fixture = Path(__file__).parent / "fixtures" / "legacy_workbook.xls"
        loaded = xl.load(fixture)

        self.assertEqual(["Name", "Count"], loaded["Legacy"]["headers"])
        self.assertEqual([["A", 1.0]], loaded["Legacy"]["rows"])


if __name__ == "__main__":
    unittest.main()
