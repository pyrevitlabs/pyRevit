"""Regression guard for #4183: every pickle writer pins protocol 2.

CPython pickles with protocol 4 or higher by default, which IronPython 2.7
cannot read. The tool scripts need Revit to run, so this inspects their source
with ``ast``. It is the only guard for the extension call sites.
"""

import ast
import unittest
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]
SCAN_ROOTS = ("pyrevitlib", "extensions")
SKIPPED_PARTS = {"site-packages", "rpw", "dev", "bin", "obj", "node_modules"}
PICKLE_MODULE_NAMES = {"pickle", "pl", "cPickle"}
CROSS_ENGINE_PROTOCOL = 2
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"


def _is_pickle_writer(call):
    func = call.func
    if not isinstance(func, ast.Attribute) or func.attr not in ("dump", "Pickler"):
        return False
    owner = func.value
    if isinstance(owner, ast.Attribute):
        owner = ast.Name(id=owner.attr)
    return isinstance(owner, ast.Name) and owner.id in PICKLE_MODULE_NAMES


def _protocol_argument(call):
    position = 2 if call.func.attr == "dump" else 1
    if len(call.args) > position:
        return call.args[position]
    for keyword in call.keywords:
        if keyword.arg == "protocol":
            return keyword.value
    return None


def _violations():
    found = []
    for root_name in SCAN_ROOTS:
        for path in sorted((ROOT_DIR / root_name).rglob("*.py")):
            if SKIPPED_PARTS & set(path.relative_to(ROOT_DIR).parts):
                continue
            tree = ast.parse(path.read_bytes())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and _is_pickle_writer(node):
                    protocol = _protocol_argument(node)
                    is_pinned = (
                        isinstance(protocol, ast.Constant)
                        and protocol.value == CROSS_ENGINE_PROTOCOL
                    )
                    if not is_pinned:
                        found.append(
                            "{}:{}".format(path.relative_to(ROOT_DIR), node.lineno)
                        )
    return found


@pytest.mark.regression
class PickleWriteProtocolTests(unittest.TestCase):
    """#4183: files shared between engines are written with protocol 2."""

    def test_every_pickle_writer_pins_protocol_2(self):
        """No pickle.dump or Pickler call relies on the engine default."""
        self.assertEqual([], _violations())


if __name__ == "__main__":
    unittest.main()
