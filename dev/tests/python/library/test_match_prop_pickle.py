"""Regression tests for #4183: the Match Properties memory payload is picklable.

``PropKeyValue`` is compiled out of ``match_utils.py`` and run against a stub
``DB.StorageType`` that, like the .NET enum on CPython, cannot be pickled.
"""

import ast
import pickle
import sys
import types
import unittest
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]
MATCH_UTILS = (
    ROOT_DIR
    / "extensions"
    / "pyRevitTools.extension"
    / "lib"
    / "match"
    / "match_utils.py"
)
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"
CROSS_ENGINE_PROTOCOL = 2
MODULE_NAME = "match_utils_under_test"


class _StorageType(object):
    def __init__(self, name):
        self._name = name

    def ToString(self):
        return self._name

    def __reduce__(self):
        raise TypeError("cannot pickle 'StorageType' object")


def _clr_deserialize(type_name, text):
    return _Int64Like(int(text))


_clr_deserialize.__module__ = "clr"
_clr_deserialize.__qualname__ = "Deserialize"
_clr_deserialize.__name__ = "Deserialize"


class _Int64Like(object):
    def __init__(self, number):
        self._number = number

    def __int__(self):
        return self._number

    __module__ = "__builtin__"

    def __reduce__(self):
        return (_clr_deserialize, ("System.Int64", str(self._number)))


for _name in ("Integer", "Double", "String", "ElementId"):
    setattr(_StorageType, _name, _StorageType(_name))


def _load_prop_key_value():
    tree = ast.parse(MATCH_UTILS.read_bytes())
    node = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "PropKeyValue"
    )
    module = types.ModuleType(MODULE_NAME)
    module.DB = types.SimpleNamespace(StorageType=_StorageType)
    module.get_elementid_value = int
    sys.modules[MODULE_NAME] = module
    plain_types = next(n for n in tree.body if isinstance(n, ast.Try))
    code = ast.fix_missing_locations(
        ast.Module(body=[plain_types, node], type_ignores=[])
    )
    exec(compile(code, str(MATCH_UTILS), "exec"), module.__dict__)
    return module.PropKeyValue


@pytest.mark.regression
class PropKeyValuePickleTests(unittest.TestCase):
    """#4183: the recall file must not contain .NET objects."""

    def setUp(self):
        """Load PropKeyValue against the stub."""
        self.prop_key_value = _load_prop_key_value()
        self.addCleanup(sys.modules.pop, MODULE_NAME, None)

    def test_raw_storage_type_is_not_picklable(self):
        """The stub reproduces the CPython failure for the raw enum."""
        with self.assertRaises(TypeError):
            pickle.dumps(_StorageType.Double, CROSS_ENGINE_PROTOCOL)

    def test_round_trip_restores_storage_type(self):
        """Pickling stores the name and loading converts it back."""
        original = self.prop_key_value(
            name="Mark", datatype=_StorageType.Double, value=1.5, istype=True
        )
        payload = pickle.dumps(("Elements", [original]), CROSS_ENGINE_PROTOCOL)
        target_type, restored = pickle.loads(payload)
        self.assertEqual("Elements", target_type)
        self.assertIs(restored[0].datatype, _StorageType.Double)
        self.assertEqual(
            (original.name, original.value, original.istype, original.display_value),
            (
                restored[0].name,
                restored[0].value,
                restored[0].istype,
                restored[0].display_value,
            ),
        )
        self.assertEqual(restored[0].categories, [])
        self.assertIs(original.datatype, _StorageType.Double)

    def test_net_numeric_value_is_stored_as_plain_int(self):
        """An Int64-like value must not pickle as a clr reference."""
        clr_stub = types.ModuleType("clr")
        clr_stub.Deserialize = _clr_deserialize
        missing = object()
        original_clr = sys.modules.get("clr", missing)
        sys.modules["clr"] = clr_stub
        try:
            original = self.prop_key_value(
                name="Base Constraint",
                datatype=_StorageType.ElementId,
                value=_Int64Like(593176),
                istype=False,
            )
            payload = pickle.dumps(("Elements", [original]), CROSS_ENGINE_PROTOCOL)
        finally:
            if original_clr is missing:
                del sys.modules["clr"]
            else:
                sys.modules["clr"] = original_clr
        self.assertNotIn(b"clr", payload)
        restored = pickle.loads(payload)[1][0]
        self.assertEqual(593176, restored.value)
        self.assertIs(type(restored.value), int)


class _AmbiguousElementId(object):
    def __init__(self, value):
        if not isinstance(value, _Int64Like):
            raise TypeError("Multiple targets could match: ElementId(Int64)")
        self.value = int(value)


class _Parameter(object):
    StorageType = _StorageType.ElementId

    def __init__(self):
        self.applied = None

    def Set(self, value):
        self.applied = value


class _Target(object):
    def __init__(self, parameter):
        self._parameter = parameter

    def LookupParameter(self, name):
        return self._parameter


def _load_match_prop():
    tree = ast.parse(MATCH_UTILS.read_bytes())
    node = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "match_prop"
    )
    module = types.ModuleType(MODULE_NAME)
    module.DB = types.SimpleNamespace(
        StorageType=_StorageType, ElementId=_AmbiguousElementId
    )
    module.get_logger = lambda name: types.SimpleNamespace(
        debug=lambda *args: None, warning=lambda *args: None
    )
    module.get_elementid_from_value = lambda value: _AmbiguousElementId(
        _Int64Like(value)
    )
    code = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(code, str(MATCH_UTILS), "exec"), module.__dict__)
    return module.match_prop


@pytest.mark.regression
class MatchPropElementIdTests(unittest.TestCase):
    """#4183: a loaded plain int must be turned into an ElementId unambiguously."""

    def test_elementid_row_uses_compat_constructor(self):
        """The ElementId branch builds the id through the compat function."""
        parameter = _Parameter()
        pkv = types.SimpleNamespace(
            name="Base Constraint",
            datatype=_StorageType.ElementId,
            value=593176,
            istype=False,
        )
        _load_match_prop()(_Target(parameter), None, [pkv])
        self.assertEqual(593176, parameter.applied.value)


if __name__ == "__main__":
    unittest.main()
