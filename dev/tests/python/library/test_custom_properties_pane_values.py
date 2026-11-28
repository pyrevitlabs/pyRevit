# -*- coding: utf-8 -*-
"""Host-free regression tests for what the Custom Properties pane applies.

The pane shows rounded Revit text, so writing back a field the user did not edit
would change its value (issue #4259). The methods under test are cut out of
``pane.py``, which cannot be imported without Revit and WPF.
"""

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

import ast
from collections import Counter, namedtuple
from pathlib import Path
import types
import unittest

import pytest


LIB = Path(__file__).resolve().parents[4] / "extensions/pyRevitTools.extension/lib"
PANE = LIB / "panes/customprops/pane.py"
MATCH_UTILS = LIB / "match/match_utils.py"
PANE_METHODS = ("_collect_pending", "_is_field_changed", "_get_field_original")
PASTE_METHODS = ("paste_clicked", "_on_field_text_changed")
PastedNumber = namedtuple("PastedNumber", ["text", "internal_value", "data_type"])


def _load_definitions(names, source=PANE, **namespace):
    tree = ast.parse(source.read_text(encoding="utf-8"))
    found = [node for node in ast.walk(tree) if getattr(node, "name", "") in set(names)]
    tree.body = found
    exec(compile(tree, str(source), "exec"), namespace)
    return namespace


def _property_value_class():
    return _load_definitions(("PropKeyValue",), source=MATCH_UTILS)["PropKeyValue"]


class _Control(object):
    def __init__(self, **attributes):
        self.Tag = None
        self.__dict__.update(attributes)


class _TextBlock(_Control):
    pass


class _TextBox(_Control):
    IsReadOnly = False


class _ComboBox(_Control):
    SelectedItem = None


class _CheckBox(_Control):
    IsEnabled = True


class _Button(_Control):
    pass


class _ElementType(_Control):
    pass


def _fake_framework():
    return types.SimpleNamespace(
        Controls=types.SimpleNamespace(
            TextBlock=_TextBlock,
            TextBox=_TextBox,
            ComboBox=_ComboBox,
            CheckBox=_CheckBox,
            Button=_Button,
        )
    )


def _row(name, field, original):
    row = types.SimpleNamespace(
        Children=[_TextBlock(Text=name), field, _Button(Tag=original)]
    )
    field.Parent = row
    return row


class _PaneTestCase(unittest.TestCase):
    def setUp(self):
        namespace = _load_definitions(
            PANE_METHODS + PASTE_METHODS + ("_pasted_number",),
            framework=_fake_framework(),
            DB=types.SimpleNamespace(
                StorageType=types.SimpleNamespace(Double="Double", Integer="Integer")
            ),
            PastedNumber=PastedNumber,
            _SEL_CB_TAG="sel_checkbox",
            _COPIED_INTEGER_TAG="_copied_integer",
            _PASTED_NUMBER_TAG="_pasted_number",
        )
        methods = dict((name, namespace[name]) for name in PANE_METHODS + PASTE_METHODS)
        self.pane = type("Pane", (object,), methods)()
        self.pane._varies = "<varies>"
        self.pane._worksets = [("Shared", 5)]
        self.pane.workset_combo = _ComboBox(Text="Shared")
        self.pane.workset_undo_btn = _Button(Tag="Shared")

    def collect(self, *rows):
        self.pane.additional_panel = types.SimpleNamespace(Children=list(rows))
        return self.pane._collect_pending()


@pytest.mark.regression
class ApplyOnlyEditedFieldsTests(_PaneTestCase):
    def test_untouched_fields_are_not_written_back(self):
        pending = self.collect(
            _row("Length", _TextBox(Text="1500"), "1500"),
            _row("Level", _ComboBox(Text="L1"), "L1"),
            _row("Done", _CheckBox(IsChecked=True), True),
        )
        self.assertEqual({"additional": {}}, pending)

    def test_edited_fields_are_collected_as_typed(self):
        pending = self.collect(
            _row("Length", _TextBox(Text=" 1500 mm "), "1500"),
            _row("Level", _ComboBox(Text="L2"), "L1"),
            _row("Done", _CheckBox(IsChecked=False), True),
        )
        self.assertEqual(
            {"Length": "1500 mm", "Level": "L2", "Done": "0"}, pending["additional"]
        )

    def test_an_edited_workset_is_collected(self):
        self.pane.workset_undo_btn.Tag = "<varies>"
        self.assertEqual(5, self.collect()["workset_id"])


@pytest.mark.regression
class PastedNumberTests(_PaneTestCase):
    """Issue #4259: shown numbers are rounded, so a paste keeps the exact one."""

    def paste(self, field, shown="1000"):
        copied = types.SimpleNamespace(
            name="Length",
            datatype="Double",
            value=3.2821522309711,
            display_value=shown,
            data_type="length",
        )
        row = _row("Length", field, field.Text)
        self.pane._copy_clipboard = [copied]
        self.pane._find_field_for_param = lambda name: field
        self.pane._mark_field_dirty = lambda changed: None
        self.pane.paste_clicked(None, None)
        return row

    def test_a_pasted_number_keeps_its_exact_value(self):
        row = self.paste(_TextBox(Text="1500"))
        self.assertEqual(
            PastedNumber("1000", 3.2821522309711, "length"),
            self.collect(row)["additional"]["Length"],
        )

    def test_it_is_applied_even_when_the_target_shows_the_same_text(self):
        row = self.paste(_TextBox(Text="1000"))
        self.assertEqual(
            3.2821522309711,
            self.collect(row)["additional"]["Length"].internal_value,
        )

    def type_into(self, field, *texts):
        self.pane._suppress_dirty = False
        for text in texts:
            field.Text = text
            self.pane._on_field_text_changed(field, None)

    def test_typing_after_a_paste_wins(self):
        field = _TextBox(Text="1500")
        row = self.paste(field)
        self.type_into(field, "1200")
        self.assertEqual({"Length": "1200"}, self.collect(row)["additional"])

    def test_retyping_the_pasted_text_writes_what_was_typed(self):
        field = _TextBox(Text="1500")
        row = self.paste(field)
        self.type_into(field, "1", "1000")
        self.assertEqual({"Length": "1000"}, self.collect(row)["additional"])

    def test_a_blank_copy_is_not_written(self):
        row = self.paste(_TextBox(Text="1500"), shown="")
        self.assertEqual({}, self.collect(row)["additional"])


@pytest.mark.regression
class PastedIntegerTests(_PaneTestCase):
    """Integers shown as text are read-only fields that only a paste can fill."""

    def apply_paste(self, pasted_value, shown):
        field = _TextBox(Text="Other", IsReadOnly=True)
        row = _row("Value", field, field.Text)
        self.pane._copy_clipboard = [
            types.SimpleNamespace(
                name="Value",
                datatype="Integer",
                value=5,
                paste_value=pasted_value,
                display_value=shown,
            )
        ]
        self.pane._find_field_for_param = lambda name: field
        self.pane._mark_field_dirty = lambda changed: None
        self.pane.paste_clicked(None, None)
        return self.collect(row)["additional"]

    def test_a_named_value_is_written_as_its_number(self):
        self.assertEqual({"Value": "5"}, self.apply_paste(5, "Column"))

    def test_a_workset_is_written_by_name(self):
        self.assertEqual(
            {"Value": "Shared Levels"},
            self.apply_paste("Shared Levels", "Shared Levels"),
        )


@pytest.mark.regression
class PastedNumberWriteTests(unittest.TestCase):
    def write_to(self, data_type):
        written = []
        namespace = _load_definitions(
            ("_write_param",),
            PastedNumber=PastedNumber,
            UNIT_INTERNAL="internal",
            get_parameter_data_type=lambda definition: definition,
            ValueCodec=lambda doc, mode: types.SimpleNamespace(
                write=lambda param, value: written.append((mode, value))
            ),
        )
        codec = types.SimpleNamespace(
            doc=None, write=lambda param, value: written.append(("display", value))
        )
        parameter = types.SimpleNamespace(Definition=data_type)
        element = types.SimpleNamespace(LookupParameter=lambda name: parameter)
        namespace["_write_param"](
            codec, element, "Length", PastedNumber("1000", 3.25, "length"), Counter()
        )
        return written

    def test_the_same_data_type_gets_the_exact_internal_value(self):
        self.assertEqual([("internal", 3.25)], self.write_to("length"))

    def test_another_data_type_gets_the_shown_text(self):
        self.assertEqual([("display", "1000")], self.write_to("angle"))


@pytest.mark.regression
class RefusalReportTests(unittest.TestCase):
    def setUp(self):
        self.write = _load_definitions(("_write_param",), PastedNumber=PastedNumber)[
            "_write_param"
        ]

    def apply(self, codec, parameter):
        element = types.SimpleNamespace(LookupParameter=lambda name: parameter)
        refusals = Counter()
        self.write(codec, element, "Length", "1,5", refusals)
        self.write(codec, element, "Length", "1,5", refusals)
        return refusals

    def test_a_refused_value_is_counted_with_its_reason(self):
        def refuse(parameter, text):
            raise ValueError("not a number")

        refusals = self.apply(types.SimpleNamespace(write=refuse), object())
        self.assertEqual({("Length", "not a number"): 2}, dict(refusals))

    def test_an_element_without_the_parameter_is_skipped(self):
        codec = types.SimpleNamespace(write=lambda *args: self.fail("written"))
        self.assertEqual({}, dict(self.apply(codec, None)))


@pytest.mark.regression
class ReferenceOptionTests(unittest.TestCase):
    def test_same_named_types_of_the_category_are_told_apart(self):
        namespace = _load_definitions(
            ("_reference_label", "_reference_options"),
            DB=types.SimpleNamespace(ElementType=_ElementType),
            query=types.SimpleNamespace(get_name=lambda element: element.Name),
        )
        framing = types.SimpleNamespace(Id="framing")
        columns = types.SimpleNamespace(Id="columns")
        elements = [
            _ElementType(Name="Standard", FamilyName=family, Category=category)
            for family, category in (
                ("Round", framing),
                ("Square", framing),
                ("Post", columns),
            )
        ]
        self.assertEqual(
            ["Round: Standard", "Square: Standard"],
            namespace["_reference_options"](elements, "framing"),
        )


@pytest.mark.regression
class FilterNameTests(unittest.TestCase):
    def name_for(self, display_value, value=7):
        build = _load_definitions(("_filter_base_name",))["_filter_base_name"]
        return build(
            types.SimpleNamespace(name="Type", display_value=display_value, value=value)
        )

    def test_a_qualified_type_gives_a_name_revit_accepts(self):
        self.assertEqual(
            "Type == Round Column - Standard",
            self.name_for("Round Column: Standard"),
        )

    def test_a_blank_text_falls_back_to_the_value(self):
        self.assertEqual("Type == 7", self.name_for(""))


@pytest.mark.regression
class CopyTests(unittest.TestCase):
    """Copies through the real ``PropKeyValue``, which replaces blank text."""

    def copy(self, parameter, target=None, shown=""):
        namespace = _load_definitions(
            ("_build_pkv_for_param", "_reference_label", "_is_workset_parameter"),
            DB=types.SimpleNamespace(
                ElementType=_ElementType,
                BuiltInParameter=types.SimpleNamespace(
                    ELEM_PARTITION_PARAM="partition"
                ),
                StorageType=types.SimpleNamespace(
                    String="String",
                    Double="Double",
                    Integer="Integer",
                    ElementId="ElementId",
                ),
                ElementId=types.SimpleNamespace(InvalidElementId=-1),
            ),
            ValueCodec=lambda doc: types.SimpleNamespace(read=lambda param: shown),
            query=types.SimpleNamespace(get_name=lambda element: element.Name),
            is_yesno_parameter=lambda definition: False,
            PropKeyValue=_property_value_class(),
            get_elementid_value=int,
            get_parameter_data_type=lambda definition: definition,
        )
        element = types.SimpleNamespace(
            LookupParameter=lambda name: parameter, Category=None
        )
        pane = types.SimpleNamespace(_elements=[element])
        document = types.SimpleNamespace(GetElement=lambda found: target)
        return namespace["_build_pkv_for_param"](pane, "Value", document)

    def reference(self, element_id):
        return types.SimpleNamespace(
            StorageType="ElementId", AsElementId=lambda: element_id
        )

    def test_an_empty_reference_copies_as_blank_text(self):
        copied = self.copy(self.reference(-1))
        self.assertEqual("", copied.display_value)
        self.assertEqual(-1, copied.value)

    def test_a_reference_copies_the_element_name(self):
        target = types.SimpleNamespace(Name="Concrete")
        copied = self.copy(self.reference(7), target)
        self.assertEqual("Concrete", copied.display_value)

    def test_a_reference_to_a_type_copies_its_family_too(self):
        target = _ElementType(Name="Standard", FamilyName="Round Column")
        copied = self.copy(self.reference(7), target)
        self.assertEqual("Round Column: Standard", copied.display_value)

    def integer(self, built_in_parameter):
        return types.SimpleNamespace(
            StorageType="Integer",
            AsInteger=lambda: 5,
            Definition=types.SimpleNamespace(BuiltInParameter=built_in_parameter),
        )

    def test_a_workset_is_pasted_by_name(self):
        copied = self.copy(self.integer("partition"), shown="Shared Levels")
        self.assertEqual("Shared Levels", copied.paste_value)
        self.assertEqual(5, copied.value)

    def test_another_integer_is_pasted_by_number(self):
        copied = self.copy(self.integer("usage"), shown="Column")
        self.assertEqual(5, copied.paste_value)

    def test_a_number_without_a_value_copies_as_blank_text(self):
        parameter = types.SimpleNamespace(
            StorageType="Double", AsDouble=lambda: 0.0, Definition="length"
        )
        copied = self.copy(parameter)
        self.assertEqual("", copied.display_value)
        self.assertEqual("length", copied.data_type)


if __name__ == "__main__":
    unittest.main()
