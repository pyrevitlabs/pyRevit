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
    code = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
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


if __name__ == "__main__":
    unittest.main()
