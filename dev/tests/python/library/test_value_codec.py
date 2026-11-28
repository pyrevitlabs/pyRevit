# -*- coding: utf-8 -*-
"""Host-free tests for the shared parameter value codec (issue #4259).

Loads the real ``pyrevit/revit/units.py`` and ``pyrevit/revit/valuecodec.py``
against a fake ``DB`` namespace, a fake document and fake parameters, with both
the unit API of Revit 2021 and the one of 2022 and newer. The fake Revit parser
only records what reaches it, so the tests check which text is judged by the
shared number rule and which is left to Revit.
"""

import copy
import importlib.util
import pathlib
import sys
import types
import unittest

import pytest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

REVIT_LIB = (
    pathlib.Path(__file__).resolve().parents[4] / "pyrevitlib" / "pyrevit" / "revit"
)

STUBBED_MODULES = (
    "pyrevit",
    "pyrevit.compat",
    "pyrevit.coreutils",
    "pyrevit.coreutils.logger",
    "pyrevit.revit",
    "pyrevit.revit.db",
    "pyrevit.revit.units",
    "pyrevit.revit.valuecodec",
)

UNIT_FACTORS = {"mm": 304.8, "m": 0.3048, "degrees": 57.29577951308232, "sf": 1.0}
SPEC_UNITS = {"length": ("mm", "m"), "angle": ("degrees",), "area": ("sf",)}
INVALID_ID = -1
NOT_BUILT_IN = -1
WORKSET_PARAMETER = -1002053


class FormatOptions(object):
    def __init__(self, unit, grouping=False, use_default=False):
        self.unit = unit
        self.UseDigitGrouping = grouping
        self.UseDefault = use_default

    def GetUnitTypeId(self):
        return self.unit

    @property
    def DisplayUnits(self):
        return self.unit


class Units(object):
    def __init__(self, decimal="Dot", grouping=False):
        self.DecimalSymbol = decimal
        self.formats = dict(
            (spec, FormatOptions(units[0], grouping))
            for spec, units in SPEC_UNITS.items()
        )

    def GetFormatOptions(self, spec):
        return copy.copy(self.formats[spec])

    def SetFormatOptions(self, spec, options):
        self.formats[spec] = copy.copy(options)

    @staticmethod
    def IsModifiableSpec(spec):
        return spec in SPEC_UNITS

    @staticmethod
    def IsModifiableUnitType(spec):
        return spec in SPEC_UNITS


class RevitParser(object):
    """Stands in for ``UnitFormatUtils`` and records every call."""

    def __init__(self):
        self.parsed = []

    def TryParse(self, units, spec, text, options):
        self.parsed.append((units.formats[spec].unit, text))
        return (False, 0.0) if text == "nonsense" else (True, 42.0)

    def Format(self, units, spec, value, *flags):
        options = units.formats[spec]
        return "{} {} grouping={}".format(
            value * UNIT_FACTORS[options.unit], options.unit, options.UseDigitGrouping
        )


class StorageType(object):
    Double = "Double"
    Integer = "Integer"
    String = "String"
    ElementId = "ElementId"


class Category(object):
    def __init__(self, category_id):
        self.Id = category_id


class Element(object):
    def __init__(self, element_id, name="", category=None):
        self.Id = element_id
        self.name = name
        self.Category = category
        self.parameters = {}

    def get_Parameter(self, definition):
        return self.parameters.get(definition)

    def GetType(self):
        element_class = type(self)
        return types.SimpleNamespace(
            FullName=element_class.__name__, element_class=element_class
        )


class ElementType(Element):
    def __init__(self, element_id, name, category=None, family=""):
        Element.__init__(self, element_id, name, category)
        self.FamilyName = family


class Material(Element):
    pass


class Level(Element):
    pass


class Collector(object):
    def __init__(self, doc, elements=None):
        self.doc = doc
        self.elements = list(doc.elements if elements is None else elements)

    def _only(self, keep):
        return Collector(self.doc, [item for item in self.elements if keep(item)])

    def OfCategoryId(self, category_id):
        return self._only(
            lambda item: item.Category and item.Category.Id == category_id
        )

    def OfClass(self, element_class):
        wanted = getattr(element_class, "element_class", element_class)
        return self._only(lambda item: type(item) is wanted)

    def WhereElementIsElementType(self):
        return self._only(lambda item: isinstance(item, ElementType))

    def WhereElementIsNotElementType(self):
        return self._only(lambda item: not isinstance(item, ElementType))

    def __iter__(self):
        return iter(self.elements)


class Document(object):
    def __init__(self, decimal="Dot", grouping=False, worksets=()):
        self.project_units = Units(decimal, grouping)
        self.elements = []
        self.worksets = [
            types.SimpleNamespace(Name=name, Id=types.SimpleNamespace(IntegerValue=i))
            for i, name in enumerate(worksets, 100)
        ]

    def GetUnits(self):
        return copy.deepcopy(self.project_units)

    def GetElement(self, element_id):
        return next((item for item in self.elements if item.Id == element_id), None)

    def add(self, element):
        self.elements.append(element)
        return element


class InternalDefinition(object):
    def __init__(self, spec, built_in=NOT_BUILT_IN, yesno=False, material=False):
        self.spec = spec
        self.UnitType = spec
        self.BuiltInParameter = built_in
        self.yesno = yesno
        self.ParameterType = "Material" if material else "Other"

    def GetDataType(self):
        return self.spec


class Parameter(object):
    def __init__(
        self,
        storage,
        spec="text",
        owner=None,
        value=None,
        shown=None,
        has_value=True,
        read_only=False,
        definition=None,
        set_value_string_accepts=True,
    ):
        self.StorageType = storage
        self.Definition = definition or InternalDefinition(spec)
        self.Element = owner
        self.value = value
        self.shown = shown
        self.HasValue = has_value
        self.IsReadOnly = read_only
        self.IsShared = False
        self.Id = id(self.Definition)
        self.written = []
        self.typed = []
        self.set_value_string_accepts = set_value_string_accepts
        if owner is not None:
            owner.parameters[self.Definition] = self

    def AsDouble(self):
        return self.value

    def AsInteger(self):
        return self.value

    def AsString(self):
        return self.value

    def AsElementId(self):
        return INVALID_ID if self.value is None else self.value

    def AsValueString(self):
        return self.shown

    def Set(self, value):
        self.written.append(value)
        return True

    def SetValueString(self, text):
        self.typed.append(text)
        return self.set_value_string_accepts


def make_fake_db(parser):
    def convert_from(value, unit):
        return value * UNIT_FACTORS[unit]

    def convert_to(value, unit):
        return value / UNIT_FACTORS[unit]

    def is_valid(spec, unit):
        return unit in SPEC_UNITS.get(spec, ())

    return types.SimpleNamespace(
        StorageType=StorageType,
        ElementType=ElementType,
        Material=Material,
        InternalDefinition=InternalDefinition,
        ElementId=types.SimpleNamespace(InvalidElementId=INVALID_ID),
        BuiltInParameter=types.SimpleNamespace(
            INVALID=NOT_BUILT_IN, ELEM_PARTITION_PARAM=WORKSET_PARAMETER
        ),
        DecimalSymbol=types.SimpleNamespace(Dot="Dot", Comma="Comma"),
        SpecTypeId=types.SimpleNamespace(
            Reference=types.SimpleNamespace(Material="material")
        ),
        ParameterType=types.SimpleNamespace(Material="Material"),
        UnitType=types.SimpleNamespace(UT_Undefined="text"),
        Units=Units,
        FormatOptions=FormatOptions,
        UnitFormatUtils=parser,
        ValueParsingOptions=lambda: None,
        UnitUtils=types.SimpleNamespace(
            ConvertFromInternalUnits=convert_from,
            ConvertToInternalUnits=convert_to,
            IsMeasurableSpec=lambda spec: spec in SPEC_UNITS,
            IsValidUnit=is_valid,
            IsValidDisplayUnit=is_valid,
        ),
        FilteredElementCollector=Collector,
        FilteredWorksetCollector=lambda doc: types.SimpleNamespace(
            OfKind=lambda kind: doc.worksets
        ),
        WorksetKind=types.SimpleNamespace(UserWorkset="user"),
    )


def load_modules(revit_year):
    previous = {name: sys.modules.get(name) for name in STUBBED_MODULES}

    class PyRevitException(Exception):
        @property
        def msg(self):
            return self.args[0] if self.args else ""

    parser = RevitParser()
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.DB = make_fake_db(parser)
    pyrevit.DOCS = types.SimpleNamespace(doc=None)
    pyrevit.HOST_APP = types.SimpleNamespace(
        is_newer_than=lambda year: revit_year > year,
        is_older_than=lambda year: revit_year < year,
    )
    pyrevit.PyRevitException = PyRevitException
    pyrevit.automation = types.SimpleNamespace(
        operation=lambda *args, **kwargs: lambda function: function
    )
    compat = types.ModuleType("pyrevit.compat")
    compat.safe_strtype = str
    compat.get_elementid_value_func = lambda: int
    logger = types.ModuleType("pyrevit.coreutils.logger")
    logger.get_logger = lambda name: types.SimpleNamespace(debug=lambda *args: None)
    revit = types.ModuleType("pyrevit.revit")
    revit_db = types.ModuleType("pyrevit.revit.db")
    revit_db.get_parameter_data_type = lambda definition: definition.spec
    revit_db.is_yesno_parameter = lambda definition: definition.yesno
    revit_db.query = types.SimpleNamespace(get_name=lambda element: element.name)
    sys.modules.update(
        {
            "pyrevit": pyrevit,
            "pyrevit.compat": compat,
            "pyrevit.coreutils": types.ModuleType("pyrevit.coreutils"),
            "pyrevit.coreutils.logger": logger,
            "pyrevit.revit": revit,
            "pyrevit.revit.db": revit_db,
        }
    )
    loaded = {}
    try:
        for name in ("units", "valuecodec"):
            module_name = "pyrevit.revit." + name
            spec = importlib.util.spec_from_file_location(
                module_name, REVIT_LIB / (name + ".py")
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            setattr(revit, name, module)
            spec.loader.exec_module(module)
            loaded[name] = module
    finally:
        for name, module_before in previous.items():
            if module_before is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module_before
    return loaded["units"], loaded["valuecodec"], parser


class CodecTestCase(unittest.TestCase):
    REVIT_YEAR = 2026

    def setUp(self):
        self.units, self.values, self.parser = load_modules(self.REVIT_YEAR)
        self.walls = Category(1)

    def codec(self, mode="display", **document):
        return self.values.ValueCodec(Document(**document), mode)

    def double(self, spec="length", value=1.0, **extra):
        return Parameter(StorageType.Double, spec, value=value, **extra)

    def assert_refused(self, reason, function, *args, **kwargs):
        with self.assertRaises(self.units.ValueRefused) as caught:
            function(*args, **kwargs)
        self.assertEqual(reason, caught.exception.reason, str(caught.exception))


@pytest.mark.regression
class NumberNotationTests(CodecTestCase):
    """Issue #4259: one rule for ``.`` and ``,``, and no guessing."""

    DOT_PROJECT = {
        "1.5": 1.5,
        "1.234": 1.234,
        "1,234.5": 1234.5,
        "1,234,567": 1234567.0,
        "-1,234,567.25": -1234567.25,
        "1 234.5": 1234.5,
        "1 234": 1234.0,
        " 7 ": 7.0,
        ".5": 0.5,
        "5.": 5.0,
        "1e-5": 1e-05,
    }
    COMMA_PROJECT = {
        "1,5": 1.5,
        "1,234": 1.234,
        "1.234,5": 1234.5,
        "1.234.567": 1234567.0,
        "1 234,5": 1234.5,
        ",5": 0.5,
    }

    def test_a_dot_project(self):
        for text, number in self.DOT_PROJECT.items():
            self.assertEqual(number, self.units.parse_number(text, "."), text)

    def test_a_comma_project(self):
        for text, number in self.COMMA_PROJECT.items():
            self.assertEqual(number, self.units.parse_number(text, ","), text)

    def test_a_lone_grouping_symbol_is_refused(self):
        for text in ("1,5", "1,234", "1.234,5", "1.234.567", "1,234.", "0,123.4"):
            self.assert_refused("number", self.units.parse_number, text, ".")
        for text in ("1.5", "1.234", "1,234.5", "1,234,567"):
            self.assert_refused("number", self.units.parse_number, text, ",")

    def test_groups_are_three_digits_with_one_separator(self):
        for text in ("1,23,456", "12 34", "1,234 567", "1,2,3.4", "1 2 3"):
            self.assert_refused("number", self.units.parse_number, text, ".")

    def test_non_numbers_and_non_finite_values_are_refused(self):
        texts = ("abc", "", "nan", "inf", "-inf", "1e400", "1e", "--1", "١٢")
        for value in texts + (float("nan"), float("inf")):
            self.assert_refused("number", self.units.parse_number, value, ".")

    def test_formatting_never_uses_exponents_or_grouping(self):
        self.assertEqual("5", self.units.format_number(5.0))
        self.assertEqual("0", self.units.format_number(-0.0))
        self.assertEqual("2,5", self.units.format_number(2.5, ","))
        self.assertEqual("0.00004659288394", self.units.format_number(4.659288394e-05))
        self.assertEqual("10000000000000000000000", self.units.format_number(1e22))

    def test_a_formatted_number_reads_back_exactly(self):
        for value in (3.280839895013123, 0.1, 123456789012.345, 1e-07, 999.99999997):
            for decimal in (".", ","):
                text = self.units.format_number(value, decimal)
                self.assertEqual(value, self.units.parse_number(text, decimal), text)

    def test_a_refusal_prints_its_message_only(self):
        with self.assertRaises(self.units.ValueRefused) as caught:
            self.units.parse_number("1,5", ".")
        self.assertNotIn("Traceback", str(caught.exception))
        self.assertIn("'1,5'", str(caught.exception))


@pytest.mark.regression
class WholeNumberTests(CodecTestCase):
    """Integer parameters must not truncate or wrap."""

    def test_whole_numbers_and_the_int32_bounds_are_accepted(self):
        parse = self.values.parse_whole_number
        self.assertEqual(7, parse(7.0))
        self.assertEqual(-5, parse("-5"))
        self.assertEqual(2**31 - 1, parse(2.0**31 - 1))
        self.assertEqual(-(2**31), parse(-(2.0**31)))

    def test_fractions_are_refused_instead_of_truncated(self):
        self.assert_refused("whole_number", self.values.parse_whole_number, 5.7)

    def test_values_outside_int32_are_refused_instead_of_wrapped(self):
        for value in (2.0**31, -(2.0**31) - 1, 1e20):
            self.assert_refused("range", self.values.parse_whole_number, value)


@pytest.mark.regression
class YesNoTests(CodecTestCase):
    """Yes/No text must never silently become No."""

    def test_english_words_digits_and_numbers(self):
        for value in ("yes", "Yes", " TRUE ", "1", "1.0", "y", "x", 1.0):
            self.assertEqual(1, self.values.parse_yes_no(value), value)
        for value in ("no", "No", "false", "0", "0.0", "n", 0.0):
            self.assertEqual(0, self.values.parse_yes_no(value), value)

    def test_the_shipped_languages(self):
        yes = ("Ja", "Oui", "Sí", "Sim", "Да", "예", "是")
        no = ("Nein", "Non", "Não", "Нет", "아니요")
        for label in yes:
            self.assertEqual(1, self.values.parse_yes_no(label), label)
        for label in no + ("否",):
            self.assertEqual(0, self.values.parse_yes_no(label), label)

    def test_unknown_words_and_numbers_are_refused(self):
        for value in ("maybe", "", 2.0, -1.0, "2", float("nan")):
            self.assert_refused("yes_no", self.values.parse_yes_no, value)

    def test_the_codec_reads_and_writes_its_own_labels(self):
        codec = self.values.ValueCodec(Document(), "display", "Aye", "Nay")
        definition = InternalDefinition("yesno", yesno=True)
        parameter = Parameter(StorageType.Integer, definition=definition, value=1)
        self.assertEqual("Aye", codec.read(parameter))
        codec.write(parameter, "nay")
        codec.write(parameter, "Oui")
        self.assertEqual([0, 1], parameter.written)


@pytest.mark.regression
class CellTextTests(CodecTestCase):
    """A number from a spreadsheet keeps its typed form as text."""

    def test_numbers(self):
        for value, text in (
            (123.0, "123"),
            (-4.0, "-4"),
            (5.5, "5.5"),
            (0.1 + 0.2, "0.3"),
            (1e20, "100000000000000000000"),
        ):
            self.assertEqual(text, self.values.as_text(value))

    def test_text_is_unchanged(self):
        for text in ("abc", "=1+1", "123.0", ""):
            self.assertEqual(text, self.values.as_text(text))
        self.assertEqual("", self.values.as_text(None))

    def test_a_text_parameter_takes_a_numeric_cell_as_excel_shows_it(self):
        parameter = Parameter(StorageType.String)
        self.codec(decimal="Comma").write(parameter, 5.5)
        self.assertEqual(["5.5"], parameter.written)


@pytest.mark.regression
class ReadTests(CodecTestCase):
    """Every value reads with the unit of its own parameter."""

    def test_number_mode_converts_each_parameter_with_its_own_unit(self):
        codec = self.codec("number")
        self.assertEqual("304.8", codec.read(self.double("length", 1.0)))
        self.assertEqual("2", codec.read(self.double("area", 2.0)))

    def test_number_mode_uses_the_project_decimal_symbol(self):
        codec = self.codec("number", decimal="Comma")
        self.assertEqual("304,8", codec.read(self.double()))

    def test_internal_mode_reads_the_raw_value(self):
        self.assertEqual("1.5", self.codec("internal").read(self.double(value=1.5)))

    def test_a_field_format_applies_where_its_unit_fits(self):
        codec = self.codec("number")
        metres = FormatOptions("m")
        self.assertEqual("0.3048", codec.read(self.double(), metres))
        self.assertEqual("2", codec.read(self.double("area", 2.0), metres))

    def test_a_field_format_that_uses_the_default_is_ignored(self):
        field = FormatOptions("m", use_default=True)
        self.assertEqual("304.8", self.codec("number").read(self.double(), field))

    def test_display_mode_returns_revits_text(self):
        parameter = self.double(shown="305 mm")
        self.assertEqual("305 mm", self.codec().read(parameter))

    def test_display_mode_leaves_out_digit_grouping(self):
        parameter = self.double(shown="12,345 mm")
        self.assertEqual(
            "304.8 mm grouping=False",
            self.codec(grouping=True).read(parameter),
        )

    def test_display_mode_applies_the_field_format(self):
        self.assertEqual(
            "0.3048 m grouping=False",
            self.codec().read(self.double(), FormatOptions("m", grouping=True)),
        )

    def test_a_parameter_without_a_value_reads_empty(self):
        for parameter in (
            self.double(has_value=False),
            Parameter(StorageType.Integer, has_value=False),
        ):
            self.assertEqual("", self.codec().read(parameter))

    def test_integers_show_their_label_except_in_internal_mode(self):
        parameter = Parameter(StorageType.Integer, value=3, shown="Girder")
        self.assertEqual("Girder", self.codec().read(parameter))
        self.assertEqual("3", self.codec("internal").read(parameter))

    def test_an_empty_reference_reads_empty_whatever_revit_shows(self):
        parameter = Parameter(StorageType.ElementId, shown="<By Category>")
        self.assertEqual("", self.codec().read(parameter))


@pytest.mark.regression
class WriteNumberTests(CodecTestCase):
    """Bare numbers follow the shared rule; other text goes to Revit."""

    def test_number_mode_converts_with_the_parameters_unit(self):
        parameter = self.double()
        self.codec("number").write(parameter, "304.8")
        self.assertEqual([1.0], parameter.written)

    def test_a_numeric_value_is_in_the_display_unit(self):
        for mode in ("display", "number"):
            parameter = self.double()
            self.codec(mode).write(parameter, 304.8)
            self.assertEqual([1.0], parameter.written, mode)

    def test_internal_mode_writes_the_raw_value(self):
        parameter = self.double()
        self.codec("internal").write(parameter, "2.5")
        self.assertEqual([2.5], parameter.written)

    def test_a_given_unit_overrides_the_mode(self):
        for mode in ("display", "number", "internal"):
            parameter = self.double()
            self.codec(mode).write(parameter, "0.3048", unit_id="m")
            self.assertEqual([1.0], parameter.written, mode)

    def test_a_unit_of_another_kind_is_refused(self):
        parameter = self.double("angle")
        self.assert_refused(
            "unsupported",
            self.codec("number").write,
            parameter,
            "5",
            unit_id="mm",
        )
        self.assertEqual([], parameter.written)

    def test_display_mode_gives_revit_the_ungrouped_number(self):
        parameter = self.double()
        self.codec().write(parameter, "1,234.50")
        self.assertEqual(["1234.5"], parameter.typed)

    def test_a_refused_number_never_reaches_revits_parser(self):
        for mode in ("display", "number"):
            parameter = self.double()
            codec = self.codec(mode, decimal="Comma")
            self.assert_refused("number", codec.write, parameter, "1.234")
            self.assert_refused("number", codec.write, parameter, "1.234", unit_id="mm")
            self.assertEqual(
                ([], [], []), (parameter.written, parameter.typed, self.parser.parsed)
            )

    def test_text_with_a_unit_goes_to_revit(self):
        shown = self.double()
        self.codec().write(shown, "1500 mm")
        self.assertEqual(["1500 mm"], shown.typed)
        number = self.double()
        self.codec("number").write(number, "1'-6\"")
        self.assertEqual([("mm", "1'-6\"")], self.parser.parsed)
        self.assertEqual([42.0], number.written)

    def test_revit_parses_with_the_given_unit_or_the_field_format(self):
        self.codec("number").write(self.double(), "=2*3", unit_id="m")
        self.codec().write(self.double(), "5 m", FormatOptions("m"))
        self.assertEqual([("m", "=2*3"), ("m", "5 m")], self.parser.parsed)

    def test_text_revit_cannot_read_is_refused(self):
        parameter = self.double()
        self.assert_refused(
            "rejected", self.codec("number").write, parameter, "nonsense"
        )
        self.assertEqual([], parameter.written)
        typed = self.double(set_value_string_accepts=False)
        self.assert_refused("rejected", self.codec().write, typed, "5 parsecs")

    def test_empty_text_and_non_finite_numbers_are_refused(self):
        parameter = self.double()
        self.assert_refused("empty", self.codec().write, parameter, "  ")
        self.assert_refused("number", self.codec().write, parameter, float("nan"))
        self.assertEqual([], parameter.written)

    def test_a_unitless_double_takes_a_bare_number_only(self):
        parameter = self.double("text")
        self.codec().write(parameter, "2.5")
        self.assertEqual([2.5], parameter.written)
        self.assert_refused("number", self.codec().write, parameter, "2.5 mm")

    def test_a_read_only_parameter_is_refused(self):
        parameter = self.double(read_only=True)
        self.assert_refused("read_only", self.codec().write, parameter, "1")


class Revit2021ReadTests(ReadTests):
    REVIT_YEAR = 2021


class Revit2021WriteNumberTests(WriteNumberTests):
    REVIT_YEAR = 2021


@pytest.mark.regression
class IntegerAndWorksetTests(CodecTestCase):
    def integer(self, owner=None, **extra):
        return Parameter(StorageType.Integer, owner=owner, **extra)

    def test_a_plain_integer_is_written_as_is(self):
        parameter = self.integer()
        self.codec().write(parameter, "3")
        self.codec().write(parameter, 4.0)
        self.assertEqual([3, 4], parameter.written)

    def test_a_label_the_category_shows_is_written_as_its_number(self):
        doc = Document()
        definition = InternalDefinition("int")
        shown = doc.add(Element(1, category=self.walls))
        self.integer(shown, definition=definition, value=7, shown="Interior")
        target = doc.add(Element(2, category=self.walls))
        parameter = self.integer(target, definition=definition, value=0, shown="Other")
        self.values.ValueCodec(doc).write(parameter, "interior")
        self.assertEqual([7], parameter.written)

    def test_a_grouped_integer_follows_the_number_rule(self):
        parameter = self.integer()
        self.codec().write(parameter, "1,234,567")
        self.assertEqual([1234567], parameter.written)
        self.assert_refused("number", self.codec().write, parameter, "1,234")

    def test_an_unknown_label_is_refused(self):
        parameter = self.integer(set_value_string_accepts=False)
        self.assert_refused("rejected", self.codec().write, parameter, "Exterior")
        self.assertEqual([], parameter.written)

    def test_a_workset_is_found_by_its_whole_name(self):
        codec = self.codec(worksets=("Architecture", "Structure"))
        definition = InternalDefinition("int", built_in=WORKSET_PARAMETER)
        parameter = self.integer(definition=definition)
        codec.write(parameter, "Structure")
        self.assertEqual([101], parameter.written)
        for name in ("Arch", "architecture"):
            self.assert_refused("workset", codec.write, parameter, name)


@pytest.mark.regression
class ReferenceTests(CodecTestCase):
    def setUp(self):
        super(ReferenceTests, self).setUp()
        self.doc = Document()
        self.definition = InternalDefinition("reference")
        self.types = Category(2)

    def element(self, element_id, target=None, shown=None, category=None):
        owner = self.doc.add(Element(element_id, category=category or self.walls))
        return Parameter(
            StorageType.ElementId,
            owner=owner,
            definition=self.definition,
            value=target,
            shown=shown,
        )

    def add_type(self, element_id, name, family):
        return self.doc.add(ElementType(element_id, name, self.types, family))

    def write(self, parameter, text):
        self.values.ValueCodec(self.doc).write(parameter, text)

    def test_the_text_the_category_shows_wins(self):
        self.add_type(10, "Concrete", "Basic Wall")
        parameter = self.element(1, target=10, shown="Basic Wall: Concrete")
        self.write(parameter, "basic wall: concrete")
        self.assertEqual([10], parameter.written)

    def test_an_unused_element_is_found_by_name_or_family_and_type(self):
        self.add_type(10, "Concrete", "Basic Wall")
        self.add_type(11, "Brick", "Basic Wall")
        parameter = self.element(1, target=10, shown="Concrete")
        for text in ("Brick", "Basic Wall: Brick", "Basic Wall : Brick"):
            self.write(parameter, text)
        self.assertEqual([11, 11, 11], parameter.written)

    def test_a_name_that_matches_twice_is_refused(self):
        self.add_type(10, "Concrete", "Basic Wall")
        self.add_type(11, "200", "Basic Wall")
        self.add_type(12, "200", "Curtain Wall")
        parameter = self.element(1, target=10, shown="Concrete")
        self.assert_refused("ambiguous", self.write, parameter, "200")
        self.write(parameter, "Curtain Wall: 200")
        self.assertEqual([12], parameter.written)

    def test_two_targets_shown_with_one_text_are_refused(self):
        self.element(2, target=10, shown="200")
        self.element(3, target=11, shown="200")
        parameter = self.element(1)
        self.assert_refused("ambiguous", self.write, parameter, "200")

    def test_an_unknown_name_is_refused(self):
        self.add_type(10, "Concrete", "Basic Wall")
        parameter = self.element(1, target=10, shown="Concrete")
        self.assert_refused("reference", self.write, parameter, "Straw")
        self.assertEqual([], parameter.written)

    def test_empty_text_clears_the_reference(self):
        parameter = self.element(1, target=10)
        self.write(parameter, " ")
        self.assertEqual([INVALID_ID], parameter.written)

    def test_an_empty_reference_uses_another_element_of_the_category(self):
        self.doc.add(Level(20, "L1"))
        self.doc.add(Level(21, "L2"))
        self.element(2, target=20, shown="L1")
        parameter = self.element(1)
        self.write(parameter, "L2")
        self.assertEqual([21], parameter.written)

    def test_the_sample_of_one_category_is_not_used_for_another(self):
        self.doc.add(Level(20, "L1"))
        self.doc.add(Level(21, "L2"))
        self.element(2, target=20, shown="L1")
        with_sample = self.element(1)
        without_sample = self.element(3, category=Category(9))
        codec = self.values.ValueCodec(self.doc)
        codec.write(with_sample, "L2")
        self.assert_refused("reference", codec.write, without_sample, "L2")

    def test_an_empty_material_is_found_among_the_materials(self):
        self.definition = InternalDefinition("material", material=True)
        self.doc.add(Material(30, "Concrete"))
        parameter = self.element(1)
        self.write(parameter, "concrete")
        self.assertEqual([30], parameter.written)


class Revit2021ReferenceTests(ReferenceTests):
    REVIT_YEAR = 2021


class ConstructionTests(CodecTestCase):
    def test_an_unknown_unit_mode_is_refused(self):
        with self.assertRaises(ValueError):
            self.values.ValueCodec(Document(), "bare")


if __name__ == "__main__":
    unittest.main()
