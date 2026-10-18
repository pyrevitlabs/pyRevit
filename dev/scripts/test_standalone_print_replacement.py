"""Check replacement recovery using real files without loading Revit."""

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Integration"


import ast
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Drawing Set.panel/Print Sheets.pushbutton/script.py"
)


def _load_replacement():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names = {
        "_OutputReplacement",
        "_LockedFileError",
        "_set_aside_files",
        "_put_back_files",
        "_delete_set_aside_files",
        "_unused_backup_path",
        "_existing_files",
    }
    selected = [node for node in tree.body if getattr(node, "name", "") in names]
    window = next(
        node for node in tree.body if getattr(node, "name", "") == "PrintSheetsWindow"
    )
    window.bases = []
    window.body = [
        method
        for method in window.body
        if getattr(method, "name", "")
        in ("print_sheets", "_replace_existing_outputs", "_planned_output_files")
    ]
    tree.body = selected + [window]
    namespace = {"os": os, "op": os.path, "logger": Mock(), "forms": Mock()}
    namespace["COMBINED_PDF_NAME"] = "Ordered Sheet Set"
    exec(compile(tree, str(SCRIPT), "exec"), namespace)
    return namespace


class ReplacementTests(unittest.TestCase):
    """Old exports survive incomplete, failed, and deferred replacements."""

    def setUp(self):
        """Create an existing export and another planned output."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.first = Path(self.temp.name) / "first.pdf"
        self.second = Path(self.temp.name) / "second.dwg"
        self.first.write_bytes(b"old")
        self.paths = [str(self.first), str(self.second)]
        self.namespace = _load_replacement()
        self.replacement = self.namespace["_OutputReplacement"](self.paths)

    def test_backups_remain_until_all_outputs_succeed(self):
        """A successful run discards backups only at finalization."""
        self.assertEqual(Path(str(self.first) + ".replaced").read_bytes(), b"old")
        self.first.write_bytes(b"new pdf")
        self.second.write_bytes(b"new dwg")
        self.replacement.finish(self.paths)
        self.assertEqual(self.first.read_bytes(), b"new pdf")
        self.assertFalse(Path(str(self.first) + ".replaced").exists())

    def test_cancellation_restores_old_and_removes_new_outputs(self):
        """A partial run restores previous files and removes partial exports."""
        self.first.write_bytes(b"new pdf")
        self.second.write_bytes(b"partial dwg")
        self.replacement.finish([str(self.first)])
        self.assertEqual(self.first.read_bytes(), b"old")
        self.assertFalse(self.second.exists())

    def test_existing_partial_files_do_not_count_as_success(self):
        """A failed export can leave every target present without succeeding."""
        self.first.write_bytes(b"partial pdf")
        self.second.write_bytes(b"partial dwg")
        self.replacement.finish([])
        self.assertEqual(self.first.read_bytes(), b"old")
        self.assertFalse(self.second.exists())

    def test_missing_confirmed_output_triggers_recovery(self):
        """Reported success also requires all expected files to exist."""
        self.replacement.finish(self.paths)
        self.assertEqual(self.first.read_bytes(), b"old")

    def test_external_printer_keeps_backups_for_manual_recovery(self):
        """Submission cannot establish completion of an external print job."""
        self.replacement.finish([], asynchronous=True)
        self.assertFalse(self.first.exists())
        self.assertEqual(Path(str(self.first) + ".replaced").read_bytes(), b"old")

    def test_locked_partial_output_preserves_backup(self):
        """Recovery never deletes a backup when its target cannot be removed."""
        self.first.write_bytes(b"locked partial")
        with patch.object(os, "remove", side_effect=OSError("locked")):
            self.replacement.finish([])
        self.assertEqual(Path(str(self.first) + ".replaced").read_bytes(), b"old")


class PrintFlowRecoveryTests(unittest.TestCase):
    """The real print entry point finalizes backups on every dispatch path."""

    def test_combined_individual_and_linked_failures_restore_previous_output(self):
        """An exception after writing a partial file restores the old export."""
        for mode in ("combined", "individual", "linked"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                namespace = _load_replacement()
                window = namespace["PrintSheetsWindow"]()
                window.combine_print = mode == "combined"
                window.selected_doc = SimpleNamespace(IsLinked=mode == "linked")
                window.selected_printer = "Revit Internal Printer"
                window.selected_print_setting = SimpleNamespace(
                    allows_variable_paper=False
                )
                window.export_dwg = SimpleNamespace(IsChecked=False)
                window.sheet_list = [
                    SimpleNamespace(printable=True, print_filename="sheet.pdf")
                ]
                window.selected_sheets = []
                window._get_output_dir = lambda: directory
                window.Close = Mock()
                name = "Ordered Sheet Set.pdf" if window.combine_print else "sheet.pdf"
                output = Path(directory) / name
                output.write_bytes(b"old")

                def fail_export(*args):
                    self.assertEqual(
                        Path(str(output) + ".replaced").read_bytes(), b"old"
                    )
                    output.write_bytes(b"partial")
                    raise RuntimeError("export failed")

                window._print_combined_sheets_in_order = fail_export
                window._print_sheets_in_order = fail_export
                window._print_linked_sheets_in_order = fail_export
                with self.assertRaisesRegex(RuntimeError, "export failed"):
                    window.print_sheets(None, None)
                self.assertEqual(output.read_bytes(), b"old")
                self.assertFalse(Path(str(output) + ".replaced").exists())


if __name__ == "__main__":
    unittest.main()
