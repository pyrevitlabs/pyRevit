"""Tests for folder path templates.

The module is loaded by path rather than imported, because importing anything under
`pyrevit` pulls in .NET and needs a Revit host.
"""

import datetime
import importlib.util
import os
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

PATHTEMPLATE_PATH = os.path.join(
    REPO_ROOT,
    "pyrevitlib",
    "pyrevit",
    "coreutils",
    "pathtemplate.py",
)


def _load_pathtemplate():
    spec = importlib.util.spec_from_file_location(
        "pyrevit_pathtemplate_under_test", PATHTEMPLATE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pathtemplate = _load_pathtemplate()

NOW = datetime.datetime(2026, 10, 17, 14, 5, 9)
VALUES = {"model": "Tower", "sheet_index": "Issue Set"}


class FillTests(unittest.TestCase):
    def test_date_and_time_come_from_now(self):
        self.assertEqual(
            pathtemplate.fill("{date}_{time}_PRINT", now=NOW), "261017_140509_PRINT"
        )

    def test_caller_values_fill_their_placeholders(self):
        filled = pathtemplate.fill("{model}_{sheet_index}", VALUES, now=NOW)

        self.assertEqual(filled, "Tower_Issue Set")

    def test_caller_values_override_date_and_time(self):
        filled = pathtemplate.fill("{date}", {"date": "2026-10-17"}, now=NOW)

        self.assertEqual(filled, "2026-10-17")

    def test_typed_backslashes_create_nested_folders(self):
        filled = pathtemplate.fill("{model}\\{sheet_index}", VALUES, now=NOW)

        self.assertEqual(filled, "Tower\\Issue Set")

    def test_typed_forward_slashes_create_nested_folders(self):
        filled = pathtemplate.fill("{model}/{sheet_index}", VALUES, now=NOW)

        self.assertEqual(filled, "Tower\\Issue Set")

    def test_slashes_inside_values_do_not_nest_folders(self):
        for sheet_index in ("Arch\\Issue 01", "Arch/Issue 01"):
            with self.subTest(sheet_index=sheet_index):
                filled = pathtemplate.fill(
                    "{sheet_index}", {"sheet_index": sheet_index}
                )

                self.assertEqual(filled, "Arch Issue 01")

    def test_control_characters_are_removed(self):
        filled = pathtemplate.fill(
            "{sheet_index}", {"sheet_index": "Issue\tSet\r\n01\x7f"}
        )

        self.assertEqual(filled, "IssueSet01")

    def test_leading_dots_in_folder_names_are_kept(self):
        filled = pathtemplate.fill(".exports\\{model}", VALUES, now=NOW)

        self.assertEqual(filled, ".exports\\Tower")

    def test_parent_folder_names_are_dropped(self):
        filled = pathtemplate.fill("..\\{model}\\...", VALUES, now=NOW)

        self.assertEqual(filled, "Tower")

    def test_characters_windows_rejects_are_removed(self):
        filled = pathtemplate.fill("{model}", {"model": 'Tower: "A" <B>|C?*/'})

        self.assertEqual(filled, "Tower A BC")

    def test_empty_and_dot_only_parts_are_dropped(self):
        filled = pathtemplate.fill("{model}\\\\ . \\sets. ", VALUES, now=NOW)

        self.assertEqual(filled, "Tower\\sets")

    def test_empty_template_fills_to_an_empty_path(self):
        self.assertEqual(pathtemplate.fill("   ", VALUES, now=NOW), "")

    def test_malformed_templates_are_rejected(self):
        for template in ("{unknown}", "{date", "{date.year}", "{0}", "{date[x]}"):
            with self.subTest(template=template):
                with self.assertRaises(pathtemplate.InvalidTemplateError) as raised:
                    pathtemplate.fill(template, VALUES, now=NOW)

                self.assertEqual(raised.exception.template, template)

    def test_rejected_template_lists_the_placeholders_it_accepts(self):
        with self.assertRaises(pathtemplate.InvalidTemplateError) as raised:
            pathtemplate.fill("{unknown}", VALUES, now=NOW)

        self.assertEqual(
            raised.exception.placeholders, ["date", "model", "sheet_index", "time"]
        )


class ResolveFolderTests(unittest.TestCase):
    def test_empty_subfolder_resolves_to_the_root(self):
        self.assertEqual(
            pathtemplate.resolve_folder("C:\\Prints", now=NOW), "C:\\Prints"
        )

    def test_subfolder_is_joined_under_the_root(self):
        folder = pathtemplate.resolve_folder(
            "C:\\Prints", "{date}_{time}_PRINT", VALUES, now=NOW
        )

        self.assertEqual(folder, "C:\\Prints\\261017_140509_PRINT")

    def test_placeholders_in_the_root_are_filled_in(self):
        folder = pathtemplate.resolve_folder(
            "C:\\Prints\\{date}_{model}", "{time}", VALUES, now=NOW
        )

        self.assertEqual(folder, "C:\\Prints\\261017_Tower\\140509")

    def test_root_values_cannot_nest_folders_or_keep_unsafe_characters(self):
        folder = pathtemplate.resolve_folder(
            "C:\\Prints\\{model}", values={"model": "A:B\\C"}, now=NOW
        )

        self.assertEqual(folder, "C:\\Prints\\AB C")

    def test_forward_slash_roots_keep_their_folders(self):
        for root, expected in (
            ("C:/Prints/Issue", "C:\\Prints\\Issue"),
            ("C:\\Prints/Issue", "C:\\Prints\\Issue"),
            ("//server/share/Prints", "\\\\server\\share\\Prints"),
        ):
            with self.subTest(root=root):
                self.assertEqual(pathtemplate.resolve_folder(root, now=NOW), expected)

    def test_slashes_inside_root_values_do_not_nest_folders(self):
        folder = pathtemplate.resolve_folder(
            "C:/Prints/{model}", values={"model": "A/B"}, now=NOW
        )

        self.assertEqual(folder, "C:\\Prints\\A B")

    def test_unc_shares_are_full_paths(self):
        for root, expected in (
            ("\\\\server\\share\\Prints", "\\\\server\\share\\Prints"),
            ("\\\\server\\share", "\\\\server\\share\\"),
        ):
            with self.subTest(root=root):
                self.assertEqual(pathtemplate.resolve_folder(root, now=NOW), expected)

    def test_environment_variables_in_the_root_are_expanded(self):
        with mock.patch.dict(os.environ, {"PATHTEMPLATE_UNDER_TEST": "D:\\Out"}):
            folder = pathtemplate.resolve_folder(
                "%PATHTEMPLATE_UNDER_TEST%\\Sets", now=NOW
            )

        self.assertEqual(folder, "D:\\Out\\Sets")

    def test_relative_roots_are_rejected(self):
        for root in ("Prints", "C:", "C:Prints", "\\Prints", "", "{date}_{model}"):
            with self.subTest(root=root):
                with self.assertRaises(pathtemplate.NotFullPathError) as raised:
                    pathtemplate.resolve_folder(root, values=VALUES, now=NOW)

                self.assertEqual(raised.exception.template, root)

    def test_malformed_root_templates_are_rejected(self):
        with self.assertRaises(pathtemplate.InvalidTemplateError):
            pathtemplate.resolve_folder("C:\\Prints\\{unknown}", now=NOW)

    def test_errors_share_one_base_class(self):
        self.assertTrue(
            issubclass(pathtemplate.NotFullPathError, pathtemplate.PathTemplateError)
        )
        self.assertTrue(
            issubclass(
                pathtemplate.InvalidTemplateError, pathtemplate.PathTemplateError
            )
        )


if __name__ == "__main__":
    unittest.main()
