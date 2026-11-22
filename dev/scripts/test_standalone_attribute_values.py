"""Host-free tests for the number parsing of the Attribute Editor.

Loads the bundle's ``attribute_values.py`` with stubbed ``pyrevit`` modules, so
no Revit is involved, and checks how pasted number texts are read.
"""

import importlib.util
import pathlib
import sys
import types
import unittest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

BUNDLE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "extensions"
    / "pyRevitTools.extension"
    / "pyRevit.tab"
    / "Modify.panel"
    / "edit3.stack"
    / "Edit.pulldown"
    / "Attribute Editor.pushbutton"
)


class ElementTypeStub(object):
    pass


def load_values():
    names = ("pyrevit", "pyrevit.compat", "attribute_strings")
    previous = {name: sys.modules.get(name) for name in names}
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.DB = types.SimpleNamespace(ElementType=ElementTypeStub)
    pyrevit.script = types.SimpleNamespace(
        get_logger=lambda: types.SimpleNamespace(debug=lambda *args: None)
    )
    compat = types.ModuleType("pyrevit.compat")
    compat.safe_strtype = str
    strings = types.ModuleType("attribute_strings")
    strings.t = lambda key: key
    sys.modules.update(
        {"pyrevit": pyrevit, "pyrevit.compat": compat, "attribute_strings": strings}
    )
    try:
        spec = importlib.util.spec_from_file_location(
            "attribute_values_under_test", BUNDLE / "attribute_values.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, module_before in previous.items():
            if module_before is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module_before
    return module


class ParseNumberTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = load_values()

    def parse(self, text):
        return self.values.parse_number(text)

    def test_plain_numbers(self):
        self.assertEqual(self.parse("12"), 12.0)
        self.assertEqual(self.parse("-3.5"), -3.5)
        self.assertEqual(self.parse(" 7 "), 7.0)

    def test_a_single_comma_is_a_decimal_comma(self):
        self.assertEqual(self.parse("1,5"), 1.5)

    def test_grouped_numbers_keep_their_scale_in_either_convention(self):
        self.assertEqual(self.parse("1.234,5"), 1234.5)
        self.assertEqual(self.parse("1,234.5"), 1234.5)
        self.assertEqual(self.parse("1 234,5"), 1234.5)
        self.assertEqual(self.parse("12.345.678,9"), 12345678.9)
        self.assertEqual(self.parse("12,345,678.9"), 12345678.9)

    def test_text_is_rejected_with_the_user_message(self):
        with self.assertRaises(self.values.EditError) as caught:
            self.parse("abc")
        self.assertEqual(str(caught.exception), "err_number")


class ReferenceSampleCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = load_values()

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


if __name__ == "__main__":
    unittest.main()
