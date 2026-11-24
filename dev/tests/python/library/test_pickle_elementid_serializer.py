"""Regression tests for #4183: the ElementId serializer stores a plain int.

The serializer is compiled out of its source and run against stubs, so no
pyRevit, Revit or ``clr`` is needed.
"""

import ast
import pickle
import types
import unittest
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]
PICKLING = ROOT_DIR / "pyrevitlib" / "pyrevit" / "revit" / "db" / "pickling.py"
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"
CROSS_ENGINE_PROTOCOL = 2


def _compile(path, node_type, name, namespace):
    tree = ast.parse(path.read_bytes())
    node = next(n for n in tree.body if isinstance(n, node_type) and n.name == name)
    code = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(code, str(path), "exec"), namespace)
    return namespace[name]


class _Int64Like(object):
    def __init__(self, number):
        self.number = number

    def __int__(self):
        return self.number

    def __reduce__(self):
        raise TypeError("not picklable")


class _AmbiguousElementId(object):
    def __init__(self, value):
        if not isinstance(value, _Int64Like):
            raise TypeError("Multiple targets could match: ElementId(Int64)")
        self.number = value.number


@pytest.mark.regression
class ElementIdSerializerTests(unittest.TestCase):
    """#4183: the saved id is a plain int and rebuilds through compat."""

    def _serializer(self):
        namespace = {
            "Serializable": object,
            "DB": types.SimpleNamespace(ElementId=_AmbiguousElementId),
            "get_elementid_value_func": lambda: lambda element_id: element_id.number,
            "get_elementid_from_value_func": lambda: (
                lambda value: _AmbiguousElementId(_Int64Like(value))
            ),
        }
        return _compile(PICKLING, ast.ClassDef, "ElementId", namespace)

    def test_saved_id_is_plain_and_rebuilds_through_compat(self):
        """The Int64 never reaches the pickle; loading rebuilds the id."""
        serializer = self._serializer()(_Int64Like(593176))
        self.assertIs(type(serializer.integer_value), int)
        restored = pickle.loads(
            pickle.dumps(serializer.__dict__, CROSS_ENGINE_PROTOCOL)
        )
        rebuilt = self._serializer().deserialize(
            types.SimpleNamespace(integer_value=restored["integer_value"])
        )
        self.assertEqual(593176, rebuilt.number)


if __name__ == "__main__":
    unittest.main()
