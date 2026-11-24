# -*- coding: utf-8 -*-
"""Host-free regression tests for the value handling of XLS Import and XLS Export.

Covers Yes/No cells, text written as Excel formulas, numbers in text columns,
Integer range checks and decimal commas. The import helpers are loaded by path
from the button bundle; the export cell writer is cut out of the export script,
which cannot be imported without Revit.
"""

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

import ast
import importlib.util
from pathlib import Path
import unittest

import pytest


EDIT_PULLDOWN = (
    Path(__file__).resolve().parents[4]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Modify.panel/edit3.stack/Edit.pulldown"
)
VALUES_MODULE = EDIT_PULLDOWN / "XLS Import.pushbutton/xls_values.py"
EXPORT_SCRIPT = EDIT_PULLDOWN / "XLS Export.pushbutton/xlsex_script.py"


def _load_values_module():
    spec = importlib.util.spec_from_file_location("xls_values", VALUES_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_write_cell():
    import numbers

    tree = ast.parse(EXPORT_SCRIPT.read_text(encoding="utf-8"))
    tree.body = [
        node for node in tree.body if getattr(node, "name", "") == "write_cell"
    ]
    namespace = {"numbers": numbers}
    exec(compile(tree, str(EXPORT_SCRIPT), "exec"), namespace)
    return namespace["write_cell"]


class _RecordingWorksheet(object):
    def __init__(self):
        self.calls = []

    def write(self, *args):
        self.calls.append(("write",) + args)

    def write_number(self, *args):
        self.calls.append(("write_number",) + args)

    def write_string(self, *args):
        self.calls.append(("write_string",) + args)


xls_values = _load_values_module()


@pytest.mark.regression
class YesNoTests(unittest.TestCase):
    """Yes/No cells must never silently become No."""

    def test_numeric_cells_are_read_as_numbers(self):
        self.assertEqual(1, xls_values.parse_yes_no(1.0))
        self.assertEqual(0, xls_values.parse_yes_no(0.0))

    def test_english_words_and_digits(self):
        for label in ("yes", "Yes", " TRUE ", "1", "1.0", "y"):
            self.assertEqual(1, xls_values.parse_yes_no(label), label)
        for label in ("no", "No", "false", "0", "0.0", "n"):
            self.assertEqual(0, xls_values.parse_yes_no(label), label)

    def test_localized_labels(self):
        for label in ("Ja", "Oui", "Sí", "Sim", "Да", "예", "是"):
            self.assertEqual(1, xls_values.parse_yes_no(label), label)
        for label in ("Nein", "Non", "Não", "Нет", "아니요", "否"):
            self.assertEqual(0, xls_values.parse_yes_no(label), label)

    def test_unknown_words_and_numbers_are_rejected(self):
        for value in ("maybe", "", 2.0, -1.0, "2", float("nan")):
            with self.assertRaises(ValueError, msg=repr(value)):
                xls_values.parse_yes_no(value)


@pytest.mark.regression
class NumberTests(unittest.TestCase):
    """Decimal commas in text cells and the finite-number guard."""

    def test_numeric_cell_passes_through(self):
        self.assertEqual(5.0, xls_values.parse_number(5.0))

    def test_decimal_point_and_comma(self):
        self.assertEqual(1.5, xls_values.parse_number("1.5"))
        self.assertEqual(1.5, xls_values.parse_number("1,5"))

    def test_group_separators_with_either_decimal_separator(self):
        self.assertEqual(1234.5, xls_values.parse_number("1.234,5"))
        self.assertEqual(1234.5, xls_values.parse_number("1,234.5"))
        self.assertEqual(1234567.0, xls_values.parse_number("1,234,567"))

    def test_spaces_as_group_separators(self):
        self.assertEqual(1234.5, xls_values.parse_number("1 234,5"))
        self.assertEqual(1234.5, xls_values.parse_number("1 234,5"))

    def test_group_separators_must_group_three_digits(self):
        for value in (
            "1,23,45",
            "12 34",
            "1.23.456",
            "1,234.56,7",
            "1,234 567",
        ):
            with self.assertRaises(ValueError, msg=value):
                xls_values.parse_number(value)

    def test_signs_and_grouped_decimals(self):
        self.assertEqual(-1234.5, xls_values.parse_number("-1.234,5"))
        self.assertEqual(1234567.0, xls_values.parse_number("1.234.567"))
        self.assertEqual(0.5, xls_values.parse_number(".5"))

    def test_lone_comma_before_three_digits_is_ambiguous(self):
        with self.assertRaises(ValueError):
            xls_values.parse_number("1,234")

    def test_text_that_is_not_a_finite_number_is_rejected(self):
        for value in ("abc", "1.2.3", "nan", "inf", "-inf", float("inf")):
            with self.assertRaises(ValueError, msg=repr(value)):
                xls_values.parse_number(value)


@pytest.mark.regression
class WholeNumberTests(unittest.TestCase):
    """Integer parameters must not truncate or wrap."""

    def test_whole_floats_and_text_are_accepted(self):
        self.assertEqual(7, xls_values.parse_whole_number(7.0))
        self.assertEqual(7, xls_values.parse_whole_number("7"))
        self.assertEqual(-5, xls_values.parse_whole_number(-5.0))

    def test_int32_bounds_are_accepted(self):
        self.assertEqual(2**31 - 1, xls_values.parse_whole_number(2.0**31 - 1))
        self.assertEqual(-(2**31), xls_values.parse_whole_number(-(2.0**31)))

    def test_fractions_are_rejected_instead_of_truncated(self):
        with self.assertRaises(ValueError):
            xls_values.parse_whole_number(5.7)

    def test_values_outside_int32_are_rejected_instead_of_wrapped(self):
        for value in (2.0**31, -(2.0**31) - 1, 1e20):
            with self.assertRaises(ValueError, msg=repr(value)):
                xls_values.parse_whole_number(value)


@pytest.mark.regression
class TextValueTests(unittest.TestCase):
    """A number typed into a text column keeps its typed form."""

    def test_whole_floats_lose_the_trailing_zero(self):
        self.assertEqual("123", xls_values.format_text_value(123.0))
        self.assertEqual("-4", xls_values.format_text_value(-4.0))

    def test_fractions_keep_their_digits(self):
        self.assertEqual("5.5", xls_values.format_text_value(5.5))
        self.assertEqual("0.1", xls_values.format_text_value(0.1))
        self.assertEqual("0.3", xls_values.format_text_value(0.1 + 0.2))

    def test_text_is_unchanged(self):
        for text in ("abc", "=1+1", "123.0", ""):
            self.assertEqual(text, xls_values.format_text_value(text))


@pytest.mark.regression
class ExportCellTests(unittest.TestCase):
    """Export must write every value with its own type."""

    def setUp(self):
        self.write_cell = _load_write_cell()
        self.worksheet = _RecordingWorksheet()

    def test_formula_and_url_lookalikes_are_written_as_strings(self):
        self.write_cell(self.worksheet, 1, 2, "=1+1", None)
        self.write_cell(self.worksheet, 2, 2, "http://example.com", None)

        self.assertEqual(
            [
                ("write_string", 1, 2, "=1+1", None),
                ("write_string", 2, 2, "http://example.com", None),
            ],
            self.worksheet.calls,
        )

    def test_numbers_are_written_as_numbers(self):
        self.write_cell(self.worksheet, 1, 2, 1.5, "fmt")
        self.write_cell(self.worksheet, 2, 2, 3, "fmt")

        self.assertEqual(
            [("write_number", 1, 2, 1.5, "fmt"), ("write_number", 2, 2, 3, "fmt")],
            self.worksheet.calls,
        )

    def test_missing_value_is_written_as_an_empty_string(self):
        self.write_cell(self.worksheet, 1, 2, None, "fmt")

        self.assertEqual([("write_string", 1, 2, "", "fmt")], self.worksheet.calls)


if __name__ == "__main__":
    unittest.main()
