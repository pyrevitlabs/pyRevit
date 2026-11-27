# -*- coding: utf-8 -*-
"""Host-free regression tests for the value handling of XLS Import and XLS Export.

Covers text written as Excel formulas and the unit each number is exported and
imported with (issue #4259). The value rules themselves belong to the shared
codec and are tested in ``test_value_codec.py``. The tested definitions are cut
out of the button scripts, which cannot be imported without Revit.
"""

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

import ast
import numbers
from pathlib import Path
import types
import unittest

import pytest


EDIT_PULLDOWN = (
    Path(__file__).resolve().parents[4]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Modify.panel/edit3.stack/Edit.pulldown"
)
IMPORT_SCRIPT = EDIT_PULLDOWN / "XLS Import.pushbutton/script.py"
EXPORT_SCRIPT = EDIT_PULLDOWN / "XLS Export.pushbutton/xlsex_script.py"


def _load_definition(script, name, **namespace):
    tree = ast.parse(script.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if getattr(node, "name", "") == name]
    exec(compile(tree, str(script), "exec"), namespace)
    return namespace[name]


VALID_UNITS = {"length": ("mm", "m"), "angle": ("degrees",)}
FACTORS = {"mm": 304.8, "m": 0.3048, "degrees": 57.0}


def _fake_db():
    return types.SimpleNamespace(
        UnitUtils=types.SimpleNamespace(
            IsMeasurableSpec=lambda spec: spec in VALID_UNITS,
            IsValidUnit=lambda spec, unit: unit in VALID_UNITS.get(spec, ()),
            ConvertFromInternalUnits=lambda value, unit: value * FACTORS[unit],
        )
    )


def _parameter(spec, value=1.0):
    return types.SimpleNamespace(
        Definition=types.SimpleNamespace(spec=spec), AsDouble=lambda: value
    )


class _RecordingWorksheet(object):
    def __init__(self):
        self.calls = []

    def write(self, *args):
        self.calls.append(("write",) + args)

    def write_number(self, *args):
        self.calls.append(("write_number",) + args)

    def write_string(self, *args):
        self.calls.append(("write_string",) + args)


@pytest.mark.regression
class ExportCellTests(unittest.TestCase):
    """Export must write every value with its own type."""

    def setUp(self):
        self.write_cell = _load_definition(EXPORT_SCRIPT, "write_cell", numbers=numbers)
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


@pytest.mark.regression
class UnitPerParameterTests(unittest.TestCase):
    """Issue #4259: a number uses its own parameter's unit, not the column's."""

    def setUp(self):
        get_data_type = lambda definition: definition.spec
        db = _fake_db()
        self.cell_number = _load_definition(
            EXPORT_SCRIPT,
            "get_cell_number",
            DB=db,
            get_parameter_data_type=get_data_type,
            measurable=db.UnitUtils.IsMeasurableSpec,
        )
        self.codec = types.SimpleNamespace(
            display_number=lambda param: ("own unit", param.Definition.spec)
        )
        writer_class = _load_definition(
            IMPORT_SCRIPT,
            "ParameterWriter",
            DB=db,
            get_parameter_data_type=get_data_type,
        )
        self.writer = writer_class.__new__(writer_class)
        self.writer.metadata = {"A": ("spec", "m", None, False)}
        self.column = types.SimpleNamespace(name="A", unit_tag="")

    def test_a_parameter_that_fits_the_column_unit_is_exported_in_it(self):
        self.assertEqual(
            (0.3048, True), self.cell_number(self.codec, _parameter("length"), "m")
        )

    def test_another_kind_of_parameter_is_exported_in_its_own_unit(self):
        self.assertEqual(
            (("own unit", "angle"), False),
            self.cell_number(self.codec, _parameter("angle"), "m"),
        )

    def test_a_unitless_parameter_keeps_its_raw_value(self):
        self.assertEqual(
            (2.5, True),
            self.cell_number(self.codec, _parameter("integer", 2.5), None),
        )

    def test_import_reads_the_unit_that_export_wrote(self):
        self.assertEqual(
            "m", self.writer.get_unit_type_id(_parameter("length"), self.column)
        )
        self.assertIsNone(
            self.writer.get_unit_type_id(_parameter("angle"), self.column)
        )


if __name__ == "__main__":
    unittest.main()
