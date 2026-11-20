"""Check the engine versions the About window shows without loading Revit."""

import ast
from pathlib import Path
import types
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "extensions/pyRevitCore.extension/pyRevit.tab"
    / "pyRevit.panel/About.pushbutton/aboutscript.py"
)


def _load_functions(**names):
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    namespace = dict(names)
    exec(
        compile(ast.Module(body=functions, type_ignores=[]), str(SCRIPT), "exec"),
        namespace,
    )
    return namespace


class FormatEngineVersionTests(unittest.TestCase):
    """Engine version codes and dotted versions become ``major.minor.patch``."""

    def setUp(self):
        self.format = _load_functions()["_format_engine_version"]

    def test_version_codes_split_into_major_minor_patch(self):
        self.assertEqual("2.7.12", self.format("2712"))
        self.assertEqual("3.4.2", self.format("342"))
        self.assertEqual("2.7.12", self.format(2712))

    def test_dotted_versions_keep_three_parts(self):
        self.assertEqual("3.4.2", self.format("3.4.2"))
        self.assertEqual("2.7.12", self.format("2.7.12.0"))

    def test_missing_or_unreadable_versions_are_unknown(self):
        for code in ("0", "", None, "abc"):
            self.assertIsNone(self.format(code), code)


LOCALE = {
    "pyRevit.Engine": "Running on IronPython {} (cpython {})",
    "pyRevit.Engine.CPython": "Running on cpython {}",
}


def _engine_text(attachment=None, env_code=None, ironpy=False):
    user_config = types.SimpleNamespace(get_current_attachment=lambda: attachment)
    envvars = types.SimpleNamespace(
        IPYVERSION_ENVVAR="PYREVIT_IPYVERSION",
        get_pyrevit_env_var=lambda name: env_code,
    )
    namespace = _load_functions(
        sys=types.SimpleNamespace(version="2.7.12 (2.7.12.1000)"),
        IRONPY=ironpy,
        user_config=user_config,
        envvars=envvars,
        logger=types.SimpleNamespace(debug=lambda *args: None),
    )
    return namespace["_engine_text"](LOCALE.get, "3.12.3")


class EngineTextTests(unittest.TestCase):
    """The engine line names IronPython only when its version is known."""

    def test_running_on_ironpython_shows_the_interpreter_version(self):
        self.assertEqual(
            "Running on IronPython 2.7.12 (cpython 3.12.3)",
            _engine_text(ironpy=True),
        )

    def test_unknown_ironpython_version_is_left_out(self):
        self.assertEqual("Running on cpython 3.12.3", _engine_text(env_code="0"))
        self.assertEqual("Running on cpython 3.12.3", _engine_text())

    def test_env_var_version_is_shown_without_attachment(self):
        self.assertEqual(
            "Running on IronPython 2.7.12 (cpython 3.12.3)",
            _engine_text(env_code="2712"),
        )


def _attachment(kernel, version):
    engine = types.SimpleNamespace(KernelName=kernel, Version=version)
    return types.SimpleNamespace(Engine=engine)


class AttachedEngineTests(unittest.TestCase):
    """Only an attached IronPython engine supplies the IronPython version."""

    def test_attached_ironpython_engines_are_shown(self):
        self.assertEqual(
            "Running on IronPython 2.7.12 (cpython 3.12.3)",
            _engine_text(_attachment("IronPython 2", 2712)),
        )
        self.assertEqual(
            "Running on IronPython 3.4.2 (cpython 3.12.3)",
            _engine_text(_attachment("IronPython 3", 342), env_code="2712"),
        )

    def test_attached_cpython_engine_falls_back_to_env_var(self):
        self.assertEqual(
            "Running on IronPython 2.7.12 (cpython 3.12.3)",
            _engine_text(_attachment("CPython", 3123), env_code="2712"),
        )
        self.assertEqual(
            "Running on cpython 3.12.3",
            _engine_text(_attachment("CPython", 3123)),
        )


if __name__ == "__main__":
    unittest.main()
