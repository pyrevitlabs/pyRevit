"""Check that `pyrevit.interop.xl.load` releases the workbook file before returning.

IronPython has no reference counting, so any file handle xlrd leaves open stays
open until the garbage collector runs, and the workbook cannot be renamed or
deleted in the meantime. CPython would close those handles as soon as the last
reference drops, hiding the leak, so the tests keep every `zipfile.ZipFile`
xlrd creates alive for the duration of the test, as IronPython effectively does.

`xl.py` is loaded by path because importing the `pyrevit` package needs a Revit
host. The vendored xlrd and xlsxwriter are loaded by path from the repo's
`site-packages` rather than through `sys.path`, so neither an installed copy nor
the stdlib backports vendored there can stand in for them.
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE_PACKAGES = os.path.join(REPO_ROOT, "site-packages")
XL_PATH = os.path.join(REPO_ROOT, "pyrevitlib", "pyrevit", "interop", "xl.py")


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
    spec = importlib.util.spec_from_file_location("pyrevit_xl_under_test", XL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


xl = _load_xl()


class _RetainedZipFile(zipfile.ZipFile):
    instances = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _RetainedZipFile.instances.append(self)


class LoadReleasesWorkbookTests(unittest.TestCase):
    """Check workbook data and file release while ZIP objects stay alive."""

    def setUp(self):
        """Write a small workbook and retain every ZipFile xlrd opens."""
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir, True)
        self.xlfile = os.path.join(self.tempdir, "data.xlsx")
        workbook = xlsxwriter.Workbook(self.xlfile)
        sheet = workbook.add_worksheet("Sheet1")
        sheet.write_row(0, 0, ["name", "count"])
        sheet.write_row(1, 0, ["walls", 3])
        workbook.close()

        _RetainedZipFile.instances = []
        self.addCleanup(self._close_retained_zipfiles)
        patcher = mock.patch.object(xlrd.zipfile, "ZipFile", _RetainedZipFile)
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _close_retained_zipfiles():
        for zf in _RetainedZipFile.instances:
            zf.close()
        _RetainedZipFile.instances = []

    def test_vendored_libraries_are_under_test(self):
        """Exercise the repo's vendored xlrd and xlsxwriter, not installed copies."""
        for module in (xlrd, xlsxwriter, xl.xlrd, xl.xlsxwriter, xlrd.book):
            self.assertTrue(
                os.path.abspath(module.__file__).startswith(SITE_PACKAGES + os.sep),
                module.__file__,
            )

    def test_load_reads_the_workbook(self):
        """Read headers and rows from the workbook."""
        data = xl.load(self.xlfile)

        self.assertEqual(data["Sheet1"]["headers"], ["name", "count"])
        self.assertEqual(data["Sheet1"]["rows"], [["walls", 3.0]])

    def test_workbook_can_be_renamed_right_after_load(self):
        """Release the file so it can be renamed right after loading."""
        xl.load(self.xlfile)

        renamed = os.path.join(self.tempdir, "renamed.xlsx")
        os.rename(self.xlfile, renamed)

        self.assertTrue(os.path.exists(renamed))

    def test_workbook_can_be_deleted_right_after_load(self):
        """Release the file so it can be deleted right after loading."""
        xl.load(self.xlfile)

        os.remove(self.xlfile)

        self.assertFalse(os.path.exists(self.xlfile))


if __name__ == "__main__":
    unittest.main()
