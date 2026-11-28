"""Regression tests for #4183: an unreadable Memory index is treated as missing.

``selectionmemory`` is imported against stubbed pyRevit modules, so no pyRevit
or Revit is needed.
"""

import importlib.util
import pickle
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]
SELECTION_MEMORY = (
    ROOT_DIR
    / "extensions"
    / "pyRevitTools.extension"
    / "pyRevit.tab"
    / "Selection.panel"
    / "lib"
    / "selectionmemory.py"
)
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"
PROTOCOL_2_HEADER = b"\x80\x02"
UNREADABLE_PICKLE = b"\x80\x04unreadable"


def _load_selection_memory(data_files, selected, reported_errors):
    logger = types.SimpleNamespace(
        debug=lambda *args: None, exception=reported_errors.append
    )
    revit = types.SimpleNamespace(
        doc=types.SimpleNamespace(GetElement=lambda element_id: element_id),
        get_selection=lambda: types.SimpleNamespace(set_to=selected.extend),
    )
    script = types.SimpleNamespace(
        get_logger=lambda: logger,
        get_document_data_file=lambda name, ext: data_files[name],
    )
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.forms = types.SimpleNamespace()
    pyrevit.script = script
    pyrevit.revit = revit
    compat = types.ModuleType("pyrevit.compat")
    compat.get_elementid_from_value_func = lambda: lambda value: value
    compat.get_elementid_value_func = lambda: lambda element_id: element_id
    coreutils = types.ModuleType("pyrevit.coreutils")
    coreutils.applocales = types.SimpleNamespace()
    stubs = {
        "pyrevit": pyrevit,
        "pyrevit.compat": compat,
        "pyrevit.coreutils": coreutils,
    }

    spec = importlib.util.spec_from_file_location("selectionmemory", SELECTION_MEMORY)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


@pytest.mark.regression
class MemoryIndexTests(unittest.TestCase):
    """#4183: an unreadable index file is treated like a missing one."""

    def test_unreadable_index_is_rewritten_with_protocol_2(self):
        """A protocol 4 index that the engine cannot read does not block Next."""
        with tempfile.TemporaryDirectory() as folder:
            data_files = {
                name: str(Path(folder, name))
                for name in ("SelList", "SelListPrevNextIndex", "SelListPrevNextLastId")
            }
            with open(data_files["SelList"], "wb") as selection_file:
                pickle.dump({"22", "11"}, selection_file, 2)
            Path(data_files["SelListPrevNextIndex"]).write_bytes(UNREADABLE_PICKLE)

            selected = []
            reported_errors = []
            selection_memory = _load_selection_memory(
                data_files, selected, reported_errors
            )
            selection_memory.step_through_memory(1)

            self.assertEqual([11], selected)
            self.assertEqual([], reported_errors)
            for name in ("SelListPrevNextIndex", "SelListPrevNextLastId"):
                content = Path(data_files[name]).read_bytes()
                self.assertEqual(PROTOCOL_2_HEADER, content[:2])


if __name__ == "__main__":
    unittest.main()
