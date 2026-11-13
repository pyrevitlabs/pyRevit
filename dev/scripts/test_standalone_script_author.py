"""Regression tests for ``__author__`` / ``__authors__`` script metadata.

``GenericUICommand._read_bundle_metadata_from_python_script`` is compiled out
of ``genericcomps.py`` and run against fakes, so no pyRevit, Revit or ``clr``
is needed.
"""

import ast
import os.path as op
import types
import unittest


ROOT_DIR = op.dirname(op.dirname(op.dirname(op.abspath(__file__))))
GENERICCOMPS = op.join(
    ROOT_DIR, "pyrevitlib", "pyrevit", "extensions", "genericcomps.py"
)
EXTENSIONS_INIT = op.join(
    ROOT_DIR, "pyrevitlib", "pyrevit", "extensions", "__init__.py"
)
METHOD_NAME = "_read_bundle_metadata_from_python_script"


def _load_method():
    with open(GENERICCOMPS, "rb") as source_file:
        tree = ast.parse(source_file.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == METHOD_NAME:
            module = ast.Module(body=[node], type_ignores=[])
            return module, {}
    raise AssertionError("{} not found".format(METHOD_NAME))


class _FakeScriptFileParser(object):
    params = {}

    def __init__(self, script_file):
        pass

    def extract_param(self, name):
        return self.params.get(name)

    def get_docstring(self):
        return None


def _load_exts_constants():
    with open(EXTENSIONS_INIT, "rb") as source_file:
        tree = ast.parse(source_file.read())
    constants = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            constants[node.targets[0].id] = node.value.value
    return constants


def _make_exts():
    return types.SimpleNamespace(**_load_exts_constants())


class _RaisingLogger(object):
    def log_parse_except(self, script_file, error):
        raise error


class _CommandStub(object):
    max_revit_ver = None
    min_revit_ver = None
    is_beta = None
    highlight_type = None
    context = None
    _ui_title = None
    _tooltip = None
    _help_url = None

    def __init__(self, **attributes):
        self.__dict__.update(attributes)

    def _parse_context_directives(self, value):
        return value


def _read_author(params, existing_author=None):
    module, namespace = _load_method()
    _FakeScriptFileParser.params = params
    namespace["exts"] = _make_exts()
    namespace["mlogger"] = _RaisingLogger()
    namespace["coreutils"] = types.SimpleNamespace(
        ScriptFileParser=_FakeScriptFileParser
    )
    exec(compile(module, GENERICCOMPS, "exec"), namespace)
    self_stub = _CommandStub(
        script_file="script.py",
        author=existing_author,
        type_id="pushbutton",
    )
    namespace[METHOD_NAME](self_stub)
    return self_stub.author


class ScriptAuthorTests(unittest.TestCase):
    def test_author_alone_is_used(self):
        self.assertEqual("Ann", _read_author({"__author__": "Ann"}))

    def test_authors_wins_over_author(self):
        author = _read_author({"__author__": "Ann", "__authors__": ["Bob", "Cy"]})

        self.assertEqual("Bob\nCy", author)

    def test_authors_list_is_joined_with_newlines(self):
        self.assertEqual("Bob\nCy", _read_author({"__authors__": ["Bob", "Cy"]}))

    def test_missing_author_keeps_existing_value(self):
        self.assertEqual("Bundle", _read_author({}, existing_author="Bundle"))


if __name__ == "__main__":
    unittest.main()
