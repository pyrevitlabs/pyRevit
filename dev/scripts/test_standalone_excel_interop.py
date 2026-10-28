"""Regression tests for the CPython Excel interop backend."""

import datetime
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_PACKAGES = str(REPO_ROOT / "site-packages")
FIXTURES = Path(__file__).parent / "fixtures"

xl = None
_module_patches = None


def _stub_pyrevit_modules():
    pyrevit = types.ModuleType("pyrevit")
    compat = types.ModuleType("pyrevit.compat")
    compat.PY3 = True
    compat.IRONPY = False
    pyrevit.compat = compat
    return {"pyrevit": pyrevit, "pyrevit.compat": compat}


def setUpModule():
    """Load xl.py against stub pyrevit modules restored in tearDownModule."""
    global xl, _module_patches
    _module_patches = mock.patch.dict(sys.modules, _stub_pyrevit_modules())
    _module_patches.start()
    sys.path.insert(0, SITE_PACKAGES)
    spec = importlib.util.spec_from_file_location(
        "test_excel_interop_module", REPO_ROOT / "pyrevitlib/pyrevit/interop/xl.py"
    )
    xl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(xl)


def tearDownModule():
    """Restore the real pyrevit modules and sys.path."""
    _module_patches.stop()
    if SITE_PACKAGES in sys.path:
        sys.path.remove(SITE_PACKAGES)


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
        fixture = FIXTURES / "legacy_workbook.xls"
        loaded = xl.load(fixture)

        self.assertEqual(["Name", "Count"], loaded["Legacy"]["headers"])
        self.assertEqual([["A", 1.0]], loaded["Legacy"]["rows"])

    def test_legacy_reader_shim_is_restored(self):
        """Reading .xls does not leave xlrd's time module replaced."""
        import xlrd.book

        original = xlrd.book.time
        xl.load(FIXTURES / "legacy_workbook.xls")
        self.assertIs(original, xlrd.book.time)

    def test_dump_refuses_legacy_xls_names(self):
        """Writing OOXML content under an .xls name fails instead of corrupting."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.xls"
            with self.assertRaises(ValueError):
                xl.dump(path, {"Rows": [["A"]]})
            self.assertFalse(path.exists())

    def _load_written(self, name, build):
        import openpyxl

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            workbook = openpyxl.Workbook()
            build(workbook)
            workbook.save(path)
            return xl.load(path, headers=False)

    def test_openpyxl_values_match_xlrd_types(self):
        """Blanks, numbers, booleans and errors load as xlrd reports them."""

        def build(workbook):
            sheet = workbook.active
            sheet.title = "Types"
            sheet.append(["text", None, 3, 2.5, True, False])
            sheet["G1"] = "#N/A"
            sheet["G1"].data_type = "e"

        rows = self._load_written("types.xlsx", build)["Types"]["rows"]
        self.assertEqual([["text", "", 3.0, 2.5, 1, 0, 0x2A]], rows)
        self.assertIs(float, type(rows[0][2]))
        self.assertIs(int, type(rows[0][4]))

    def test_openpyxl_dates_load_as_excel_serials(self):
        """Dates are Excel serial floats relative to the workbook epoch."""
        from openpyxl.utils.datetime import MAC_EPOCH

        def build_1900(workbook):
            workbook.active.append([datetime.datetime(2024, 1, 2, 12, 0)])

        def build_1904(workbook):
            workbook.epoch = MAC_EPOCH
            workbook.active.append([datetime.date(2024, 1, 2)])

        windows = self._load_written("w.xlsx", build_1900)
        mac = self._load_written("m.xlsx", build_1904)
        self.assertEqual([[45293.5]], list(windows.values())[0]["rows"])
        self.assertEqual([[43831.0]], list(mac.values())[0]["rows"])

    def test_openpyxl_empty_sheet_has_no_rows(self):
        """An empty worksheet yields no headers or rows, as xlrd does."""
        rows = self._load_written("blank.xlsx", lambda workbook: None)
        self.assertEqual({"headers": [], "rows": []}, list(rows.values())[0])

    def test_reader_is_chosen_by_file_signature(self):
        """Workbook content wins over a misleading file extension."""
        with tempfile.TemporaryDirectory() as directory:
            xlsx_named_xls = Path(directory) / "modern.xls"
            xl.dump(
                Path(directory) / "modern.xlsx", {"Rows": [["Name", "Count"], ["A", 1]]}
            )
            (Path(directory) / "modern.xlsx").rename(xlsx_named_xls)
            modern = xl.load(xlsx_named_xls)

            xls_named_xlsx = Path(directory) / "legacy.xlsx"
            xls_named_xlsx.write_bytes((FIXTURES / "legacy_workbook.xls").read_bytes())
            legacy = xl.load(xls_named_xlsx)

        self.assertEqual([["A", 1.0]], modern["Rows"]["rows"])
        self.assertEqual([["A", 1.0]], legacy["Legacy"]["rows"])

    def test_ironpython_dump_keeps_xls_names(self):
        """IronPython still hands .xls targets to xlsxwriter instead of raising."""
        writer = mock.MagicMock()
        with (
            mock.patch.object(xl, "IRONPY", True),
            mock.patch.object(xl, "xlsxwriter", writer, create=True),
        ):
            xl.dump("book.xls", {"Rows": [["A"]]})
        writer.Workbook.assert_called_once_with("book.xls")


if __name__ == "__main__":
    unittest.main()
