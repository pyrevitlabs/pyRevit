"""Check how Params2Param reads an element's type name without loading Revit."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Modify.panel/edit3.stack/Edit.pulldown"
    / "ParametersValuesToParameter.pushbutton/script.py"
)


class _PythonnetElement(object):
    """Element class whose ``Name`` descriptor has no IronPython ``GetValue``."""

    @property
    def Name(self):
        return self._name

    def __init__(self, name):
        self._name = name

    def LookupParameter(self, name):
        return None


def _load_get_parameter_value():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    tree.body = [
        node for node in tree.body if getattr(node, "name", "") == "get_parameter_value"
    ]
    namespace = {
        "DB": SimpleNamespace(Element=_PythonnetElement),
        "revit": SimpleNamespace(
            query=SimpleNamespace(get_name=lambda element: element.Name)
        ),
    }
    exec(compile(tree, str(SCRIPT), "exec"), namespace)
    return namespace["get_parameter_value"]


class TypeNameTests(unittest.TestCase):
    """The type name source must read on every engine."""

    def test_type_name_reads_through_the_engine_neutral_name(self):
        """A pythonnet property descriptor has no ``GetValue``; the name still reads."""
        get_parameter_value = _load_get_parameter_value()

        self.assertEqual(
            "Basic Wall",
            get_parameter_value(_PythonnetElement("Basic Wall"), "Type Name"),
        )


if __name__ == "__main__":
    unittest.main()
