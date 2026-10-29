"""Check that `pyrevit.interop.xl.load` releases the workbook file before returning.

IronPython has no reference counting, so any file handle xlrd leaves open stays
open until the garbage collector runs, and the workbook cannot be renamed or
deleted in the meantime. CPython would close those handles as soon as the last
reference drops, hiding the leak, so the tests keep every `zipfile.ZipFile`
xlrd creates alive for the duration of the test, as IronPython effectively does.

`xl.py` is loaded by path because importing the `pyrevit` package needs a Revit
host. The vendored xlrd and xlsxwriter are taken from the repo's `site-packages`,
appended to `sys.path` so the stdlib backports vendored there do not shadow the
real stdlib.
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

if SITE_PACKAGES not in sys.path:
    sys.path.append(SITE_PACKAGES)

import xlrd  # noqa: E402
import xlsxwriter  # noqa: E402


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
    def setUp(self):
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

    def test_load_reads_the_workbook(self):
        data = xl.load(self.xlfile)

        self.assertEqual(data["Sheet1"]["headers"], ["name", "count"])
        self.assertEqual(data["Sheet1"]["rows"], [["walls", 3.0]])

    def test_workbook_can_be_renamed_right_after_load(self):
        xl.load(self.xlfile)

        renamed = os.path.join(self.tempdir, "renamed.xlsx")
        os.rename(self.xlfile, renamed)

        self.assertTrue(os.path.exists(renamed))

    def test_workbook_can_be_deleted_right_after_load(self):
        xl.load(self.xlfile)

        os.remove(self.xlfile)

        self.assertFalse(os.path.exists(self.xlfile))


if __name__ == "__main__":
    unittest.main()
