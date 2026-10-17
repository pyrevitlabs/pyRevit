"""Tests for the Print Sheets output folder rules.

The module is loaded by path because it lives in a pushbutton bundle, which is not
an importable package outside Revit.
"""

import datetime
import importlib.util
import os
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

OUTPUT_FOLDER_PATH = os.path.join(
    REPO_ROOT,
    "extensions",
    "pyRevitTools.extension",
    "pyRevit.tab",
    "Drawing Set.panel",
    "Print Sheets.pushbutton",
    "print_output_folder.py",
)


def _load_output_folder():
    spec = importlib.util.spec_from_file_location(
        "print_output_folder_under_test", OUTPUT_FOLDER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


print_output_folder = _load_output_folder()
OutputFolder = print_output_folder.OutputFolder
PrintRun = print_output_folder.PrintRun
InvalidOutputRoot = print_output_folder.InvalidOutputRoot
InvalidFolderTemplate = print_output_folder.InvalidFolderTemplate

STARTED_AT = datetime.datetime(2026, 10, 17, 14, 5, 9)


def _run(model="Tower", sheet_index="Issue Set"):
    return PrintRun(model=model, sheet_index=sheet_index, started_at=STARTED_AT)


class OutputRootTests(unittest.TestCase):
    def test_empty_template_prints_straight_into_the_root(self):
        folder = OutputFolder("C:\\Prints", "")

        self.assertEqual(folder.path_for(_run()), "C:\\Prints")

    def test_unc_share_is_a_valid_root(self):
        folder = OutputFolder("\\\\server\\share\\Prints", "")

        self.assertEqual(folder.path_for(_run()), "\\\\server\\share\\Prints")

    def test_unc_share_without_subfolders_is_a_valid_root(self):
        folder = OutputFolder("\\\\server\\share", "{model}")

        self.assertEqual(folder.path_for(_run()), "\\\\server\\share\\Tower")

    def test_environment_variables_in_the_root_are_expanded(self):
        folder = OutputFolder("%PRINT_ROOT_UNDER_TEST%\\Sets", "")

        with mock.patch.dict(os.environ, {"PRINT_ROOT_UNDER_TEST": "D:\\Out"}):
            path = folder.path_for(_run())

        self.assertEqual(path, "D:\\Out\\Sets")

    def test_relative_roots_are_rejected(self):
        for root in ("Prints", "C:", "C:Prints", "\\Prints", ""):
            with self.subTest(root=root):
                folder = OutputFolder(root, "")

                with self.assertRaises(InvalidOutputRoot):
                    folder.path_for(_run())

    def test_rejected_root_names_what_was_typed(self):
        folder = OutputFolder("Prints", "")

        with self.assertRaises(InvalidOutputRoot) as raised:
            folder.path_for(_run())

        self.assertIn('"Prints"', str(raised.exception))

    def test_placeholders_in_the_root_are_filled_in(self):
        folder = OutputFolder("C:\\Prints\\{date}_{model}", "{time}")

        path = folder.path_for(_run())

        self.assertEqual(path, "C:\\Prints\\261017_Tower\\140509")

    def test_root_placeholders_cannot_nest_folders_through_names(self):
        folder = OutputFolder("C:\\Prints\\{sheet_index}", "")

        path = folder.path_for(_run(sheet_index="Arch\\Issue 01"))

        self.assertEqual(path, "C:\\Prints\\Arch Issue 01")

    def test_root_placeholders_remove_characters_windows_rejects(self):
        folder = OutputFolder("C:\\Prints\\{model}", "")

        self.assertEqual(folder.path_for(_run(model="A:B")), "C:\\Prints\\AB")

    def test_root_must_still_be_a_full_path_once_filled_in(self):
        folder = OutputFolder("{date}_{model}", "{time}")

        with self.assertRaises(InvalidOutputRoot):
            folder.path_for(_run())


class SubfolderTemplateTests(unittest.TestCase):
    def test_date_and_time_use_the_run_start(self):
        folder = OutputFolder("C:\\Prints", "{date}_{time}_PRINT")

        self.assertEqual(folder.path_for(_run()), "C:\\Prints\\261017_140509_PRINT")

    def test_typed_backslashes_create_nested_folders(self):
        folder = OutputFolder("C:\\Prints", "{model}\\{sheet_index}")

        self.assertEqual(folder.path_for(_run()), "C:\\Prints\\Tower\\Issue Set")

    def test_backslashes_inside_names_do_not_nest_folders(self):
        folder = OutputFolder("C:\\Prints", "{sheet_index}")

        path = folder.path_for(_run(sheet_index="Arch\\Issue 01"))

        self.assertEqual(path, "C:\\Prints\\Arch Issue 01")

    def test_characters_windows_rejects_are_removed(self):
        folder = OutputFolder("C:\\Prints", "{model}")

        path = folder.path_for(_run(model='Tower: "A" <B>|C?*/'))

        self.assertEqual(path, "C:\\Prints\\Tower A BC")

    def test_empty_and_dot_only_parts_are_dropped(self):
        folder = OutputFolder("C:\\Prints", "{model}\\\\ . \\sets. ")

        self.assertEqual(folder.path_for(_run()), "C:\\Prints\\Tower\\sets")

    def test_malformed_templates_are_rejected(self):
        for template in ("{unknown}", "{date", "{date.year}", "{0}"):
            with self.subTest(template=template):
                folder = OutputFolder("C:\\Prints", template)

                with self.assertRaises(InvalidFolderTemplate):
                    folder.path_for(_run())

    def test_malformed_root_templates_are_rejected(self):
        folder = OutputFolder("C:\\Prints\\{unknown}", "")

        with self.assertRaises(InvalidFolderTemplate):
            folder.path_for(_run())


if __name__ == "__main__":
    unittest.main()
