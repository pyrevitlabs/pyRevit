"""Host-free tests for the value codec of the Attribute Editor.

Loads the bundle's real ``attribute_columns.py`` and ``attribute_values.py``
against a fake ``DB`` namespace and fake parameters, so no Revit is involved,
and checks how numbers are parsed and formatted and how a cell is converted
with the unit of its own parameter.
"""

import importlib.util
import pathlib
import sys
import types
import unittest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

BUNDLE = (
    pathlib.Path(__file__).resolve().parents[4]
    / "extensions"
    / "pyRevitTools.extension"
    / "pyRevit.tab"
    / "Modify.panel"
    / "edit3.stack"
    / "Edit.pulldown"
    / "Attribute Editor.pushbutton"
)

STUBBED_MODULES = (
    "pyrevit",
    "pyrevit.compat",
    "pyrevit.framework",
    "pyrevit.revit",
    "attribute_strings",
    "attribute_columns",
    "attribute_values",
)

UNIT_FACTORS = {"degrees": 57.29577951308232, "square-feet": 1.0, "millimeters": 304.8}


class ElementTypeStub(object):
    pass


class StorageType(object):
    Double = "Double"
    Integer = "Integer"
    String = "String"
    ElementId = "ElementId"


def make_fake_db():
    return types.SimpleNamespace(
        ElementType=ElementTypeStub,
        StorageType=StorageType,
        ElementId=types.SimpleNamespace(InvalidElementId=-1),
        DecimalSymbol=types.SimpleNamespace(Dot="Dot", Comma="Comma"),
        BuiltInParameter=lambda value: value,
        UnitUtils=types.SimpleNamespace(
            ConvertFromInternalUnits=lambda value, unit: value * UNIT_FACTORS[unit],
            ConvertToInternalUnits=lambda value, unit: value / UNIT_FACTORS[unit],
        ),
    )


def make_strings():
    texts = {
        "tokens_yes": "yes;y;true;1;x;oui",
        "tokens_no": "no;n;false;0;non",
    }
    strings = types.ModuleType("attribute_strings")
    strings.t = lambda key: key
    strings.token_set = lambda key: frozenset(texts[key].split(";"))
    strings.translations = lambda key: frozenset()
    return strings


def load_modules():
    previous = {name: sys.modules.get(name) for name in STUBBED_MODULES}
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.DB = make_fake_db()
    pyrevit.script = types.SimpleNamespace(
        get_logger=lambda: types.SimpleNamespace(debug=lambda *args: None)
    )
    compat = types.ModuleType("pyrevit.compat")
    compat.safe_strtype = str
    compat.get_elementid_value_func = lambda: int
    framework = types.ModuleType("pyrevit.framework")
    framework.System = types.SimpleNamespace(Guid=str)
    revit = types.ModuleType("pyrevit.revit")
    revit.get_parameter_data_type = lambda definition: None
    revit.query = types.SimpleNamespace(get_param=lambda element, key: None)
    revit.units = types.SimpleNamespace()
    sys.modules.update(
        {
            "pyrevit": pyrevit,
            "pyrevit.compat": compat,
            "pyrevit.framework": framework,
            "pyrevit.revit": revit,
            "attribute_strings": make_strings(),
        }
    )
    loaded = {}
    try:
        for name in ("attribute_columns", "attribute_values"):
            spec = importlib.util.spec_from_file_location(name, BUNDLE / (name + ".py"))
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            loaded[name] = module
    finally:
        for name, module_before in previous.items():
            if module_before is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module_before
    return loaded["attribute_columns"], loaded["attribute_values"]


class FakeParameter(object):
    def __init__(
        self,
        columns,
        storage,
        spec_id="",
        unit_id=None,
        double=0.0,
        integer=0,
        text="",
        shown=None,
        has_value=True,
        is_yesno=False,
        read_only=False,
    ):
        self.traits = columns.ParameterTraits(
            storage, spec_id, is_yesno, False, unit_id, "u" if unit_id else ""
        )
        self.StorageType = storage
        self.IsReadOnly = read_only
        self.HasValue = has_value
        self.double = double
        self.integer = integer
        self.text = text
        self.shown = shown
        self.written = []

    def AsDouble(self):
        return self.double

    def AsInteger(self):
        return self.integer

    def AsString(self):
        return self.text

    def AsValueString(self):
        return self.shown

    def Set(self, value):
        self.written.append(value)
        return True

    def SetValueString(self, text):
        self.written.append(("text", text))
        return True


class ValueTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.columns, cls.values = load_modules()

    def codec(self, mode, decimal="."):
        codec = self.values.ValueCodec(None, mode, "Yes", "No")
        codec._decimal = decimal
        codec.traits_of = lambda parameter: parameter.traits
        return codec

    def column(self, first_parameter):
        column = self.columns.ColumnSpec("name|A|i")
        column.traits = first_parameter.traits
        column.available = True
        return column

    def angle(self, **extra):
        return FakeParameter(
            self.columns, StorageType.Double, "spec:angle", "degrees", **extra
        )

    def area(self, **extra):
        return FakeParameter(
            self.columns, StorageType.Double, "spec:area", "square-feet", **extra
        )


class ParseNumberTests(ValueTestCase):
    def parse(self, text, decimal="."):
        return self.values.parse_number(text, decimal)

    def refused(self, text, decimal="."):
        with self.assertRaises(self.values.EditError) as caught:
            self.parse(text, decimal)
        self.assertEqual(str(caught.exception), "err_number")

    def test_plain_numbers(self):
        self.assertEqual(self.parse("12"), 12.0)
        self.assertEqual(self.parse("-3.5"), -3.5)
        self.assertEqual(self.parse(" 7 "), 7.0)
        self.assertEqual(self.parse(".5"), 0.5)
        self.assertEqual(self.parse("5."), 5.0)
        self.assertEqual(self.parse("1e-5"), 1e-05)

    def test_a_dot_project_reads_a_comma_as_grouping_in_groups_of_three(self):
        self.assertEqual(self.parse("1,250"), 1250.0)
        self.assertEqual(self.parse("1,250,000"), 1250000.0)
        self.assertEqual(self.parse("1,234.5"), 1234.5)
        self.assertEqual(self.parse("1 234.5"), 1234.5)

    def test_a_comma_project_reads_a_dot_as_grouping_in_groups_of_three(self):
        self.assertEqual(self.parse("1,5", ","), 1.5)
        self.assertEqual(self.parse("1.250", ","), 1250.0)
        self.assertEqual(self.parse("1.234,5", ","), 1234.5)
        self.assertEqual(self.parse("1 234,5", ","), 1234.5)
        self.assertEqual(self.parse(" 1 234,5", ","), 1234.5)

    def test_ambiguous_notation_is_refused_instead_of_guessed(self):
        self.refused("1,5")
        self.refused("1,2,3.4")
        self.refused("1.234,5")
        self.refused("1.5", ",")
        self.refused("1,23,456")

    def test_non_numbers_and_non_finite_values_are_refused(self):
        for text in ("abc", "", "nan", "inf", "-inf", "1e400", "1e", "--1", "1 2 3"):
            self.refused(text)

    def test_only_ascii_digits_count(self):
        self.refused("١٢٣")
        self.refused("１２")


class FormatNumberTests(ValueTestCase):
    def test_whole_numbers_have_no_fraction(self):
        self.assertEqual(self.values.format_number(5.0), "5")
        self.assertEqual(self.values.format_number(-12.0), "-12")

    def test_small_and_large_values_never_use_exponent_notation(self):
        self.assertEqual(self.values.format_number(4.659288394e-05), "0.00004659288394")
        self.assertEqual(self.values.format_number(1e22), "10000000000000000000000")

    def test_the_project_decimal_symbol_is_used(self):
        self.assertEqual(self.values.format_number(2.5, ","), "2,5")

    def test_a_formatted_value_reads_back_exactly(self):
        for value in (3.280839895013123, 0.1, 123456789012.345, 1e-07, 999.99999997):
            for decimal in (".", ","):
                text = self.values.format_number(value, decimal)
                self.assertEqual(self.values.parse_number(text, decimal), value, text)


class UnitPerParameterTests(ValueTestCase):
    def test_number_mode_converts_each_cell_with_its_own_unit(self):
        codec = self.codec("number")
        angle = self.angle(double=0.5)
        area = self.area(double=2.0)
        column = self.column(angle)
        self.assertEqual(
            codec.read(column, angle),
            self.values.format_number(0.5 * UNIT_FACTORS["degrees"]),
        )
        area.shown = "2.00 SF"
        self.assertEqual(codec.read(column, area), "2.00 SF")

    def test_a_cell_of_another_spec_is_locked_in_number_mode_only(self):
        angle = self.angle()
        area = self.area()
        column = self.column(angle)
        self.assertFalse(self.codec("number").is_editable(column, area))
        self.assertTrue(self.codec("number").is_editable(column, angle))
        self.assertTrue(self.codec("display").is_editable(column, area))
        self.assertTrue(self.codec("internal").is_editable(column, area))

    def test_typing_into_a_cell_of_another_spec_never_writes(self):
        area = self.area()
        column = self.column(self.angle())
        with self.assertRaises(self.values.EditError) as caught:
            self.codec("number").write(column, area, "5")
        self.assertEqual(str(caught.exception), "err_spec_differs")
        self.assertEqual(area.written, [])

    def test_typing_into_a_cell_of_another_kind_says_so(self):
        text = FakeParameter(self.columns, StorageType.String)
        column = self.column(self.area())
        with self.assertRaises(self.values.EditError) as caught:
            self.codec("display").write(column, text, "x")
        self.assertEqual(str(caught.exception), "err_kind_differs")
        self.assertEqual(text.written, [])

    def test_number_mode_writes_the_number_in_the_cells_own_unit(self):
        area = self.area()
        column = self.column(area)
        self.codec("number").write(column, area, "5")
        self.assertEqual(area.written, [5.0])

    def test_number_mode_uses_the_project_decimal_symbol(self):
        angle = self.angle()
        column = self.column(angle)
        self.codec("number", ",").write(column, angle, "90")
        self.assertAlmostEqual(angle.written[0], 90 / UNIT_FACTORS["degrees"])
        with self.assertRaises(self.values.EditError):
            self.codec("number", ",").write(column, angle, "1.5")

    def test_internal_mode_writes_the_raw_value(self):
        area = self.area()
        column = self.column(area)
        self.codec("internal").write(column, area, "2.5")
        self.assertEqual(area.written, [2.5])

    def test_display_mode_hands_the_text_to_revit(self):
        area = self.area()
        column = self.column(area)
        self.codec("display").write(column, area, "5 m2")
        self.assertEqual(area.written, [("text", "5 m2")])

    def test_a_parameter_without_a_value_reads_empty(self):
        for parameter in (
            self.area(has_value=False),
            FakeParameter(
                self.columns, StorageType.Integer, is_yesno=True, has_value=False
            ),
        ):
            self.assertEqual(
                self.codec("display").read(self.column(parameter), parameter), ""
            )


class YesNoTests(ValueTestCase):
    def yes_no(self):
        return FakeParameter(
            self.columns, StorageType.Integer, "spec:yesno", is_yesno=True
        )

    def test_the_answer_may_be_in_any_shipped_language(self):
        parameter = self.yes_no()
        column = self.column(parameter)
        codec = self.codec("display")
        codec.write(column, parameter, "Oui")
        codec.write(column, parameter, "NON")
        self.assertEqual(parameter.written, [1, 0])

    def test_other_text_is_refused(self):
        parameter = self.yes_no()
        with self.assertRaises(self.values.EditError):
            self.codec("display").write(self.column(parameter), parameter, "maybe")


class IntegerLabelTests(ValueTestCase):
    def test_a_label_the_category_shows_is_written_as_its_number(self):
        parameter = FakeParameter(self.columns, StorageType.Integer, shown="Interior")
        column = self.column(parameter)
        codec = self.codec("display")
        codec._integer_labels = lambda column, parameter: {"interior": 1}
        codec.write(column, parameter, "interior")
        self.assertEqual(parameter.written, [1])

    def test_a_plain_integer_is_written_as_is(self):
        parameter = FakeParameter(self.columns, StorageType.Integer)
        self.codec("display").write(self.column(parameter), parameter, "3")
        self.assertEqual(parameter.written, [3])


class ReferenceSampleCacheTests(ValueTestCase):
    def setUp(self):
        self.calls = []
        self.codec = self.values.ValueCodec(None, "display", "Yes", "No")
        self.codec._find_reference_sample = self.find

    def find(self, column, owner):
        self.calls.append(owner.Category.Id.ToString())
        return (
            None
            if owner.Category.Id.ToString() == "A"
            else "sample-" + owner.Category.Id.ToString()
        )

    @staticmethod
    def parameter(category, type_owner=False):
        owner = ElementTypeStub() if type_owner else types.SimpleNamespace()
        owner.Category = types.SimpleNamespace(
            Id=types.SimpleNamespace(ToString=lambda: category)
        )
        return types.SimpleNamespace(Element=owner)

    def sample(self, category, type_owner=False):
        column = types.SimpleNamespace(key="bip|-1|i")
        return self.codec._reference_sample(
            column, self.parameter(category, type_owner)
        )

    def test_an_empty_result_of_one_category_is_not_reused_for_another(self):
        self.assertIsNone(self.sample("A"))
        self.assertEqual(self.sample("B"), "sample-B")
        self.assertEqual(self.calls, ["A", "B"])

    def test_a_repeated_lookup_in_the_same_category_is_cached(self):
        self.sample("B")
        self.sample("B")
        self.assertEqual(self.calls, ["B"])

    def test_instances_and_types_of_a_category_are_looked_up_separately(self):
        self.sample("B")
        self.sample("B", type_owner=True)
        self.assertEqual(self.calls, ["B", "B"])


class ColumnFitTests(ValueTestCase):
    def test_a_column_accepts_cells_of_its_own_kind_only(self):
        text = FakeParameter(self.columns, StorageType.String)
        number = self.area()
        column = self.column(text)
        self.assertFalse(column.accepts(number.traits, "display"))
        self.assertTrue(column.accepts(text.traits, "display"))

    def test_unitless_numbers_fit_each_other_in_number_mode(self):
        plain = FakeParameter(self.columns, StorageType.Double, "spec:number")
        other = FakeParameter(self.columns, StorageType.Double, "spec:other")
        self.assertTrue(self.column(plain).accepts(other.traits, "number"))


if __name__ == "__main__":
    unittest.main()
