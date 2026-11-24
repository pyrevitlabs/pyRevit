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
PICKLE_MODULES = ("pickle", "cPickle")
WRITER_NAMES = ("dump", "Pickler")
CROSS_ENGINE_PROTOCOL = 2
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"


def _pickle_imports(tree):
    module_aliases = set(PICKLE_MODULES)
    writer_aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in PICKLE_MODULES:
                    module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module in PICKLE_MODULES:
            for alias in node.names:
                if alias.name in WRITER_NAMES:
                    writer_aliases[alias.asname or alias.name] = alias.name
    return module_aliases, writer_aliases


def _writer_name(call, module_aliases, writer_aliases):
    func = call.func
    if isinstance(func, ast.Name):
        return writer_aliases.get(func.id)
    if isinstance(func, ast.Attribute) and func.attr in WRITER_NAMES:
        owner = func.value
        owner_name = owner.attr if isinstance(owner, ast.Attribute) else None
        if isinstance(owner, ast.Name):
            owner_name = owner.id
        if owner_name in module_aliases:
            return func.attr
    return None


def _protocol_argument(call, writer_name):
    position = 2 if writer_name == "dump" else 1
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
            module_aliases, writer_aliases = _pickle_imports(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                writer_name = _writer_name(node, module_aliases, writer_aliases)
                if writer_name:
                    protocol = _protocol_argument(node, writer_name)
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
