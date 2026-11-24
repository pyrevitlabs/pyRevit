"""Regression tests for #4183: a failed Match recall save is logged visibly.

``RecallWindow._save_recall`` is compiled out of ``pane.py`` and run against
stubs. The window closes after the command returned, so the failure must go
through the logger captured when the window opened.
"""

import ast
import types
import unittest
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]
PANE = (
    ROOT_DIR
    / "extensions"
    / "pyRevitTools.extension"
    / "lib"
    / "panes"
    / "clipboard"
    / "pane.py"
)
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"


class _Logger(object):
    def __init__(self):
        self.warnings = []

    def warning(self, message, *args):
        self.warnings.append(message % args)


class _FailingPickle(object):
    @staticmethod
    def dump(*args):
        raise TypeError("cannot pickle")


def _load_save_recall(fresh_logger):
    tree = ast.parse(PANE.read_bytes())
    window = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "RecallWindow"
    )
    method = next(
        n
        for n in window.body
        if isinstance(n, ast.FunctionDef) and n.name == "_save_recall"
    )
    namespace = {
        "PropKeyValue": lambda **kwargs: types.SimpleNamespace(**kwargs),
        "pickle": _FailingPickle,
        "script": types.SimpleNamespace(get_logger=lambda: fresh_logger),
    }
    code = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
    exec(compile(code, str(PANE), "exec"), namespace)
    return namespace["_save_recall"]


@pytest.mark.regression
class RecallSaveLoggerTests(unittest.TestCase):
    """#4183: the save failure uses the logger captured at window open."""

    def test_failure_goes_through_captured_logger(self):
        """The captured command logger receives the warning, not a fresh one."""
        captured, fresh = _Logger(), _Logger()
        item = types.SimpleNamespace(
            IsSelected=True,
            source_prop=types.SimpleNamespace(
                name="n", datatype=None, value=1, istype=False, display_value="1"
            ),
        )
        content = types.SimpleNamespace(
            _memfile="memory.dat", _items=[item], _recall_target_type="Elements"
        )
        window = types.SimpleNamespace(_content=content, recall_logger=captured)
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            content._memfile = folder + "/memory.dat"
            _load_save_recall(fresh)(window)
        self.assertEqual(1, len(captured.warnings))
        self.assertEqual([], fresh.warnings)


if __name__ == "__main__":
    unittest.main()
