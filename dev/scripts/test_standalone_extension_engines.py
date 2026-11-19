"""Regression tests for Python engine selection across every implementation.

``ENGINE_SELECTION_CASES`` is the single table of precedence and first-line
cases. Each implementation is asserted against the same rows: the pyrevitlib
command generator (``runtime.create_ipyengine_configs`` read the way the C#
``ScriptRuntime`` reads it), ``GenericUICommand.is_cpython``, and the
standalone ``check_py3_compat`` mirror.
"""

import ast
import importlib.util
import json
from pathlib import Path
import runpy
import tempfile
import types
import unittest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTENSIONS = runpy.run_path(
    str(REPO_ROOT / "pyrevitlib/pyrevit/extensions/__init__.py")
)
exts = types.SimpleNamespace(**EXTENSIONS)
get_declared_python_engine = exts.get_declared_python_engine
get_declared_engine_type = exts.get_declared_engine_type


def _load_function(relative_path, name, namespace, class_name=None):
    tree = ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
    body = tree.body
    if class_name is not None:
        body = next(
            n.body for n in body if isinstance(n, ast.ClassDef) and n.name == class_name
        )
    node = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), relative_path, "exec"),
        namespace,
    )
    return namespace[name]


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "check_py3_compat", REPO_ROOT / "dev/scripts/check_py3_compat.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


create_ipyengine_configs = _load_function(
    "pyrevitlib/pyrevit/runtime/__init__.py",
    "create_ipyengine_configs",
    {"json": json, "exts": exts},
)
_COMMAND_NAMESPACE = {"PY3": True, "exts": exts}
for _method in ("_read_script_first_line", "is_cpython", "has_cpython_hashbang"):
    _load_function(
        "pyrevitlib/pyrevit/extensions/genericcomps.py",
        _method,
        _COMMAND_NAMESPACE,
        class_name="GenericUICommand",
    )


class _Command:
    _read_script_first_line = _COMMAND_NAMESPACE["_read_script_first_line"]
    is_cpython = property(_COMMAND_NAMESPACE["is_cpython"])
    has_cpython_hashbang = property(_COMMAND_NAMESPACE["has_cpython_hashbang"])

    def __init__(self, script_file):
        self.script_file = script_file


checker = _load_checker()

_EXTENSION_NAMESPACE = {}


class _RecordingLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, message, *args):
        self.warnings.append(message % args)


class _FakeContainer:
    @staticmethod
    def _update_from_directory(extension):
        pass


class _FakeVersionManager:
    @staticmethod
    def get_pyrevit_version():
        return types.SimpleNamespace(get_formatted=lambda: "0.0.0")


_EXTENSION_NAMESPACE.update(
    exts=exts,
    op=__import__("os").path,
    mlogger=_RecordingLogger(),
    GenericUIContainer=_FakeContainer,
    versionmgr=_FakeVersionManager,
)
_update_extension_from_directory = _load_function(
    "pyrevitlib/pyrevit/extensions/components.py",
    "_update_from_directory",
    _EXTENSION_NAMESPACE,
    class_name="Extension",
)


class _FakeExtension:
    directory = "."
    script_engine = None

    def __init__(self, manifest=None, manifest_error=None):
        self._manifest = manifest
        self._manifest_error = manifest_error

    def get_manifest(self):
        if self._manifest_error:
            raise self._manifest_error
        return self._manifest

    def get_manifest_file(self):
        return "extension.json"

    def _calculate_extension_dir_hash(self):
        return "hash"


def _script_runtime_selects_cpython(engine_configs, first_line):
    """Read engine configs as C# ``ScriptRuntime.EngineType`` does."""
    configs = json.loads(engine_configs)
    engine_type = configs.get("type")
    if engine_type:
        if engine_type.lower() == "cpython":
            return True
        if engine_type.lower() == "ironpython" and configs.get("type_explicit"):
            return False
    return "python3" in first_line or "cpython" in first_line


ENGINE_SELECTION_CASES = (
    ("no declaration, plain first line", None, None, "import clr", False),
    ("no declaration, python3 shebang", None, None, "#! python3", True),
    ("no declaration, cpython shebang", None, None, "#! cpython", True),
    ("marker anywhere on the first line", None, None, "# needs python3 here", True),
    ("markers are case-sensitive", None, None, "#! Python3", False),
    ("CPython marker is case-sensitive", None, None, "#! CPython", False),
    ("extension cpython", None, "cpython", "import clr", True),
    ("extension cpython is normalized", None, " CPython ", "import clr", True),
    ("extension mapping form", None, {"type": "CPython"}, "import clr", True),
    ("extension ironpython keeps shebang", None, "ironpython", "#! python3", True),
    ("unsupported extension value", None, "python3", "import clr", False),
    ("mapping without type", None, {"clean": True}, "import clr", False),
    ("bundle cpython", "cpython", None, "import clr", True),
    ("bundle CPython over extension", "CPython", "ironpython", "import clr", True),
    ("bundle ironpython over all", "IronPython", "cpython", "#! python3", False),
    ("blank bundle type is no override", "  ", "cpython", "import clr", True),
    ("unknown bundle type drops extension", "python3", "cpython", "import clr", False),
    ("unknown bundle type uses shebang", "python3", "cpython", "#! python3", True),
)

FIRST_LINE_ONLY_CASES = tuple(
    case for case in ENGINE_SELECTION_CASES if case[1] is None and case[2] is None
)


class EngineSelectionTableTests(unittest.TestCase):
    """Every Python implementation agrees on the shared selection table."""

    def test_command_generator_configs(self):
        """Engine configs from pyrevitlib select the engine the table expects."""
        for name, bundle, extension, first_line, expected in ENGINE_SELECTION_CASES:
            with self.subTest(name):
                configs = create_ipyengine_configs(
                    engine_type=get_declared_python_engine({"engine": extension}),
                    bundle_engine_type=bundle,
                )
                self.assertEqual(
                    expected, _script_runtime_selects_cpython(configs, first_line)
                )

    def test_checker_mirror(self):
        """The standalone checker reads bundle.yaml and extension.json the same way."""
        for name, bundle, extension, first_line, expected in ENGINE_SELECTION_CASES:
            with self.subTest(name), tempfile.TemporaryDirectory() as directory:
                extension_dir = Path(directory) / "Ext.extension"
                bundle_dir = extension_dir / "Tool.pushbutton"
                bundle_dir.mkdir(parents=True)
                if extension is not None:
                    (extension_dir / "extension.json").write_text(
                        json.dumps({"engine": extension})
                    )
                if bundle is not None:
                    (bundle_dir / "bundle.yaml").write_text(
                        "engine:\n  type: {}\n".format(json.dumps(bundle))
                    )
                self.assertEqual(
                    expected,
                    checker._may_run_under_cpython(
                        bundle_dir / "script.py", first_line + "\nx = 1\n"
                    ),
                )

    def test_first_line_rule(self):
        """The shared first-line rule and the checker mirror agree."""
        for name, _, _, first_line, expected in FIRST_LINE_ONLY_CASES:
            with self.subTest(name):
                self.assertEqual(expected, exts.first_line_selects_cpython(first_line))
                self.assertEqual(
                    expected, checker._first_line_selects_cpython(first_line)
                )
                self.assertEqual(
                    exts.CPYTHON_FIRST_LINE_MARKERS, checker.CPYTHON_FIRST_LINE_MARKERS
                )

    def test_generic_ui_command_is_cpython(self):
        """GenericUICommand.is_cpython applies the first-line rule to the script."""
        for name, _, _, first_line, expected in FIRST_LINE_ONLY_CASES:
            with self.subTest(name), tempfile.TemporaryDirectory() as directory:
                script = Path(directory) / "script.py"
                script.write_text(first_line + "\nx = 1\n", encoding="utf-8")
                self.assertEqual(expected, _Command(str(script)).is_cpython)

    def test_metadata_gate_requires_the_exact_hashbang(self):
        """A first line that only mentions python3 still reads script metadata."""
        for first_line, expected in (
            ("#! python3", True),
            ("# Not compatible with python3", False),
            ("#! cpython", False),
            ("import clr", False),
        ):
            with self.subTest(first_line), tempfile.TemporaryDirectory() as directory:
                script = Path(directory) / "script.py"
                script.write_text(first_line + "\nx = 1\n", encoding="utf-8")
                self.assertEqual(expected, _Command(str(script)).has_cpython_hashbang)


class ExtensionEngineTests(unittest.TestCase):
    """Extension metadata declarations preserve explicit engine choice."""

    def test_cpython_declaration_is_normalized(self):
        """CPython declarations are case-insensitive metadata values."""
        self.assertEqual("cpython", get_declared_python_engine({"engine": " CPython "}))

    def test_ironpython_declaration_is_normalized(self):
        """IronPython declarations are case-insensitive metadata values."""
        self.assertEqual(
            "ironpython", get_declared_python_engine({"engine": "IRONPYTHON"})
        )

    def test_missing_or_unknown_declarations_do_not_override_shebangs(self):
        """Only supported declarations supply an explicit runtime override."""
        self.assertIsNone(get_declared_python_engine({}))
        self.assertIsNone(get_declared_python_engine({"engine": "python3"}))

    def test_bundle_style_mapping_declares_its_type(self):
        """The mapping form the C# loader reads declares the same engine."""
        self.assertEqual(
            "cpython",
            get_declared_python_engine({"engine": {"type": "CPython", "clean": True}}),
        )

    def test_mapping_without_type_declares_nothing(self):
        """Engine behavior settings alone are not an unsupported declaration."""
        self.assertIsNone(get_declared_engine_type({"engine": {"clean": True}}))
        self.assertIsNone(get_declared_python_engine({"engine": {"clean": True}}))

    def test_bundle_engine_type_reads_only_the_mapping_form(self):
        """A scalar bundle ``engine:`` is ignored, as the C# BundleParser does."""
        self.assertEqual(
            "CPython", exts.get_bundle_engine_type({"engine": {"type": "CPython"}})
        )
        self.assertIsNone(exts.get_bundle_engine_type({"engine": "cpython"}))
        self.assertIsNone(exts.get_bundle_engine_type(None))

    def test_bundle_engine_type_is_trimmed(self):
        """Padding around ``engine.type`` does not hide the declaration."""
        self.assertEqual(
            "cpython", exts.get_bundle_engine_type({"engine": {"type": " cpython "}})
        )

    def test_bundle_engine_type_key_ignores_case_and_padding(self):
        """``Type:`` declares the same override the C# BundleParser reads."""
        for key in ("Type", "TYPE", " type "):
            with self.subTest(key):
                self.assertEqual(
                    "IronPython",
                    exts.get_bundle_engine_type({"engine": {key: "IronPython"}}),
                )
        self.assertFalse(exts.get_bundle_engine_type({"engine": {"Type": "  "}}))

    def test_extension_class_defaults_script_engine(self):
        """Extensions restored from the binary cache skip __init__ and need a default."""
        tree = ast.parse(
            (REPO_ROOT / "pyrevitlib/pyrevit/extensions/components.py").read_text(
                encoding="utf-8"
            )
        )
        extension = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Extension"
        )
        defaults = [
            target.id
            for node in extension.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        ]
        self.assertIn("script_engine", defaults)


class ExtensionManifestLoadingTests(unittest.TestCase):
    """Extension discovery survives unreadable manifests and reports bad engines."""

    def setUp(self):
        """Start each case with an empty warning log."""
        _EXTENSION_NAMESPACE["mlogger"].warnings[:] = []

    @property
    def warnings(self):
        """Warnings the extension code logged during the case."""
        return _EXTENSION_NAMESPACE["mlogger"].warnings

    def test_unreadable_manifest_declares_no_engine(self):
        """An open failure is logged and does not abort extension construction."""
        extension = _FakeExtension(manifest_error=IOError("sharing violation"))
        _update_extension_from_directory(extension)
        self.assertIsNone(extension.script_engine)
        self.assertEqual(1, len(self.warnings))
        self.assertIn("sharing violation", self.warnings[0])

    def test_non_string_engine_type_is_reported(self):
        """A declared but non-string type warns instead of silently falling back."""
        for manifest in ({"engine": {"type": 42}}, {"engine": 42}):
            with self.subTest(manifest):
                self.warnings[:] = []
                extension = _FakeExtension(manifest)
                _update_extension_from_directory(extension)
                self.assertIsNone(extension.script_engine)
                self.assertEqual(1, len(self.warnings))

    def test_behavior_only_engine_mapping_stays_silent(self):
        """A mapping without ``type`` declares nothing and logs nothing."""
        for manifest in (
            None,
            {},
            {"engine": {"clean": True}},
            {"engine": {"type": None}},
        ):
            with self.subTest(manifest):
                extension = _FakeExtension(manifest)
                _update_extension_from_directory(extension)
                self.assertIsNone(extension.script_engine)
                self.assertEqual([], self.warnings)

    def test_supported_engine_is_kept(self):
        """A supported declaration becomes the extension's script engine."""
        extension = _FakeExtension({"engine": "CPython"})
        _update_extension_from_directory(extension)
        self.assertEqual("cpython", extension.script_engine)
        self.assertEqual([], self.warnings)


class EngineConfigPrecedenceTests(unittest.TestCase):
    """The Python command generator matches C# BuildEngineConfigs precedence."""

    def test_extension_cpython_declaration_sets_type(self):
        """A cpython extension makes CPython the default without marking it explicit."""
        configs = json.loads(create_ipyengine_configs(engine_type="cpython"))
        self.assertEqual("CPython", configs["type"])
        self.assertNotIn("type_explicit", configs)

    def test_bundle_engine_type_wins_over_extension(self):
        """A bundle's own engine.type overrides the extension declaration."""
        configs = json.loads(
            create_ipyengine_configs(
                engine_type="cpython", bundle_engine_type="IronPython"
            )
        )
        self.assertEqual("IronPython", configs["type"])
        self.assertTrue(configs["type_explicit"])

    def test_no_declarations_leave_type_to_the_shebang(self):
        """Without any declaration the runtime picks the engine per script."""
        self.assertNotIn("type", json.loads(create_ipyengine_configs()))


if __name__ == "__main__":
    unittest.main()
