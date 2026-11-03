"""Check that `pyrevit.interop.xl` reads and writes Excel workbooks under CPython.

xlrd 1.1.0 times every .xls parse with `time.clock`, which Python 3.8 removed,
so `xl.load` failed on CPython for every .xls workbook. These tests run the
real module and the vendored xlrd and xlsxwriter, loaded by path from the
repo's `site-packages` so neither an installed copy nor the stdlib backports
vendored there can stand in for them.
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import time
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE_PACKAGES = os.path.join(REPO_ROOT, "site-packages")
XL_PATH = os.path.join(REPO_ROOT, "pyrevitlib", "pyrevit", "interop", "xl.py")
LEGACY_WORKBOOK = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "legacy_workbook.xls"
)


def _load_vendored_package(name):
    for loaded in [key for key in sys.modules if key.split(".")[0] == name]:
        del sys.modules[loaded]
    package_dir = os.path.join(SITE_PACKAGES, name)
    spec = importlib.util.spec_from_file_location(
        name,
        os.path.join(package_dir, "__init__.py"),
        submodule_search_locations=[package_dir],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


xlrd = _load_vendored_package("xlrd")
xlsxwriter = _load_vendored_package("xlsxwriter")


def _load_xl():
    spec = importlib.util.spec_from_file_location(
        "pyrevit_xl_interop_under_test", XL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


xl = _load_xl()


class ExcelInteropTests(unittest.TestCase):
    """`load` and `dump` work on CPython with the same readers IronPython uses."""

    def setUp(self):
        """Give each test its own folder for the workbooks it writes."""
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        """Remove the test's workbook folder."""
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_legacy_xls_workbooks_load(self):
        """A .xls workbook loads instead of failing on the missing time.clock."""
        self.assertEqual(
            {"Legacy": {"headers": ["Name", "Count"], "rows": [["A", 1.0]]}},
            xl.load(LEGACY_WORKBOOK),
        )

    def test_xlsx_workbooks_round_trip(self):
        """What `dump` writes, `load` reads back, sheet by sheet."""
        path = os.path.join(self.tempdir, "rooms.xlsx")
        xl.dump(
            path,
            {
                "Rooms": [["Name", "Area"], ["Lobby", 12.5], ["Office", 30.0]],
                "Levels": [["Name"], ["Level 1"]],
            },
        )

        self.assertEqual(
            {
                "Rooms": {
                    "headers": ["Name", "Area"],
                    "rows": [["Lobby", 12.5], ["Office", 30.0]],
                },
                "Levels": {"headers": ["Name"], "rows": [["Level 1"]]},
            },
            xl.load(path),
        )

    def test_clock_shim_stays_inside_xlrd(self):
        """Only xlrd's book module gets a clock; the stdlib time module is unchanged."""
        self.assertTrue(callable(xlrd.book.time.clock))
        if sys.version_info >= (3, 8):
            self.assertFalse(hasattr(time, "clock"))

    def test_vendored_libraries_are_under_test(self):
        """Exercise the repo's vendored xlrd and xlsxwriter, not installed copies."""
        for module in (xl.xlrd, xl.xlsxwriter):
            self.assertTrue(
                os.path.abspath(module.__file__).startswith(SITE_PACKAGES + os.sep),
                module.__file__,
            )


if __name__ == "__main__":
    unittest.main()
