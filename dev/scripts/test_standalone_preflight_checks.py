"""Exercise preflight check discovery and naming without a Revit host (#4014)."""

import ast
import importlib.util
import json
import logging
import os
import re
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PYREVIT_ROOT = os.path.join(REPO_ROOT, "pyrevitlib", "pyrevit")
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_production_modules(imp_available=True):
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.PyRevitException = Exception
    pyrevit.HOST_APP = MagicMock()
    pyrevit.framework = MagicMock()
    pyrevit.coreutils = MagicMock()
    pyrevit.versionmgr = MagicMock()
    logger = types.ModuleType("pyrevit.coreutils.logger")
    logger.get_logger = logging.getLogger
    compat = types.ModuleType("pyrevit.compat")
    compat.safe_strtype = str

    extensions = _load_module(
        "pyrevit.extensions", os.path.join(PYREVIT_ROOT, "extensions", "__init__.py")
    )
    extensions.extensionmgr = MagicMock()
    extensions.extpackages = MagicMock()
    pyrevit.extensions = extensions

    genericcomps = types.ModuleType("pyrevit.extensions.genericcomps")
    for class_name in ("GenericComponent", "GenericUIContainer", "GenericUICommand"):
        setattr(genericcomps, class_name, type(class_name, (object,), {}))

    case = types.ModuleType("pyrevit.preflight.case")
    case.PreflightTestCase = type("PreflightTestCase", (object,), {})

    modules = {
        "pyrevit": pyrevit,
        "pyrevit.compat": compat,
        "pyrevit.framework": pyrevit.framework,
        "pyrevit.coreutils": pyrevit.coreutils,
        "pyrevit.coreutils.logger": logger,
        "pyrevit.versionmgr": pyrevit.versionmgr,
        "pyrevit.extensions": extensions,
        "pyrevit.extensions.genericcomps": genericcomps,
        "pyrevit.preflight.case": case,
        "imp": MagicMock() if imp_available else None,
    }
    with patch.dict(sys.modules, modules):
        components = _load_module(
            "_test_components",
            os.path.join(PYREVIT_ROOT, "extensions", "components.py"),
        )
        preflight = _load_module(
            "_test_preflight", os.path.join(PYREVIT_ROOT, "preflight", "__init__.py")
        )
    return components, preflight


class SysModulesIsolatedTestCase(unittest.TestCase):
    """Restores ``sys.modules`` after each test so loaded checks never leak."""

    def setUp(self):
        """Snapshot ``sys.modules`` and restore it on cleanup."""
        patcher = patch.dict(sys.modules)
        patcher.start()
        self.addCleanup(patcher.stop)


class PreflightCheckDiscoveryTests(unittest.TestCase):
    """Only ``*_check.py`` files in ``checks/`` are checks, named without the postfix."""

    @classmethod
    def setUpClass(cls):
        """Load production modules with only host dependencies replaced."""
        cls.components, cls.preflight = _load_production_modules()

    def _discover(self, *file_names):
        with tempfile.TemporaryDirectory() as checks_dir:
            for file_name in file_names:
                open(os.path.join(checks_dir, file_name), "w").close()
            extension = self.components.Extension.__new__(self.components.Extension)
            extension.checks_path = checks_dir
            return sorted(os.path.basename(path) for path in extension.get_checks())

    def test_helper_modules_are_not_checks(self):
        """A shared helper beside the checks is never returned for loading."""
        self.assertEqual(
            ["levels_check.py"],
            self._discover("levels_check.py", "helpers.py", "check_utils.py"),
        )

    def test_postfix_match_ignores_case(self):
        """``Foo_CHECK.PY`` is a check, like ``Foo_Command.PY`` is a command."""
        self.assertEqual(["Foo_CHECK.PY"], self._discover("Foo_CHECK.PY"))

    def test_non_python_files_are_not_checks(self):
        """Compiled or data files that merely look like checks are skipped."""
        self.assertEqual(
            [],
            self._discover("levels_check.pyc", "levels_check.py.bak", "levels_check"),
        )

    def test_extension_without_checks_folder_has_no_checks(self):
        """A missing ``checks/`` folder yields an empty list."""
        extension = self.components.Extension.__new__(self.components.Extension)
        extension.checks_path = None
        self.assertEqual([], extension.get_checks())

    def test_check_name_drops_only_the_trailing_postfix(self):
        """``_check`` inside the name stays; only the postfix is removed."""
        get_name = self.preflight._get_check_name
        self.assertEqual("levels", get_name("checks/levels_check.py"))
        self.assertEqual("my_check_helper", get_name("checks/my_check_helper_check.py"))
        self.assertEqual(
            "modelchecker_Warnings", get_name("modelchecker_Warnings_check.py")
        )
        self.assertEqual("Foo", get_name("Foo_CHECK.PY"))
        self.assertEqual("coord.v2", get_name("coord.v2_check.py"))
        self.assertEqual("helpers", get_name("helpers.py"))


class Python3CompatibilityTests(SysModulesIsolatedTestCase):
    """Regressions for CPython 3 failures in extension hashing and check loading (#4043)."""

    @classmethod
    def setUpClass(cls):
        """Load production modules with only host dependencies replaced."""
        cls.components, cls.preflight = _load_production_modules()

    def _extension_hash_patterns(self):
        ui = MagicMock()
        ui.get_current_theme.return_value = "light"
        revit = types.ModuleType("pyrevit.revit")
        revit.ui = ui
        extension = self.components.Extension.__new__(self.components.Extension)
        extension.directory = "unused"
        with patch.object(
            self.components.coreutils, "calculate_dir_hash", return_value=""
        ) as calculate:
            with patch.dict(
                sys.modules, {"pyrevit.revit": revit, "pyrevit.revit.ui": ui}
            ):
                extension._calculate_extension_dir_hash()
        return calculate.call_args[0][1:]

    def test_extension_dir_hash_patterns_compile(self):
        """The directory and file filters handed to the hash are valid regexes."""
        dir_pat, file_pat = self._extension_hash_patterns()
        self.assertTrue(re.search(dir_pat, "lib"))
        self.assertTrue(re.search(dir_pat, "hooks"))
        self.assertTrue(re.search(dir_pat, "My.pushbutton"))
        self.assertTrue(re.search(file_pat, "script.py"))

    def test_extension_dir_hash_patterns_escape_postfix_dots(self):
        """A postfix dot is literal, and ``lib``/``hooks`` keep substring matching."""
        dir_pat, file_pat = self._extension_hash_patterns()
        self.assertIsNone(re.search(dir_pat, "xpushbutton"))
        self.assertIsNone(re.search(file_pat, "xpy"))
        self.assertTrue(re.search(dir_pat, "mylib"))
        self.assertTrue(re.search(dir_pat, "hooks_old"))

    def _legacy_python27_patterns(self):
        exts = self.components.exts
        backslash = chr(92)

        def build(names):
            return "|".join("(" + backslash + name + ")" for name in names)

        dir_names = (
            exts.TAB_POSTFIX,
            exts.PANEL_POSTFIX,
            exts.PULLDOWN_BUTTON_POSTFIX,
            exts.SPLIT_BUTTON_POSTFIX,
            exts.SPLITPUSH_BUTTON_POSTFIX,
            exts.STACK_BUTTON_POSTFIX,
            exts.PUSH_BUTTON_POSTFIX,
            exts.SMART_BUTTON_POSTFIX,
            exts.LINK_BUTTON_POSTFIX,
            exts.PANEL_PUSH_BUTTON_POSTFIX,
            exts.PANEL_PUSH_BUTTON_POSTFIX,
            exts.CONTENT_BUTTON_POSTFIX,
            exts.COMBOBOX_POSTFIX,
            exts.CHECKBOX_POSTFIX,
            exts.COMP_LIBRARY_DIR_NAME,
            exts.COMP_HOOKS_DIR_NAME,
        )
        file_names = (
            exts.PYTHON_SCRIPT_FILE_FORMAT,
            exts.CSHARP_SCRIPT_FILE_FORMAT,
            exts.VB_SCRIPT_FILE_FORMAT,
            exts.RUBY_SCRIPT_FILE_FORMAT,
            exts.DYNAMO_SCRIPT_FILE_FORMAT,
            exts.GRASSHOPPER_SCRIPT_FILE_FORMAT,
            exts.GRASSHOPPERX_SCRIPT_FILE_FORMAT,
            exts.CONTENT_FILE_FORMAT,
            exts.YAML_FILE_FORMAT,
            exts.JSON_FILE_FORMAT,
        )

        def as_python27_sees_it(pattern):
            return re.sub(re.escape(backslash) + "([a-zA-Z])", r"\1", pattern)

        return (
            as_python27_sees_it(build(dir_names)),
            as_python27_sees_it(build(file_names)),
        )

    def test_hash_filters_match_the_same_names_as_before_on_python27(self):
        """On IronPython 2.7 the new filters select exactly the old names.

        Python 2.7 reads a backslash before ``l`` or ``h`` as the plain letter, so the old
        pattern matched ``lib`` and ``hooks`` as substrings and escaped every
        postfix dot. The new pattern gives the same match set, so the stored
        2.7 extension hashes stay valid and no cache invalidation happens.
        """
        old_dir, old_file = self._legacy_python27_patterns()
        new_dir, new_file = self._extension_hash_patterns()
        directory_names = [
            "lib",
            "hooks",
            "mylib",
            "hooks_old",
            "Library",
            "My.pushbutton",
            "Tab.TAB",
            "A.Panel",
            "Tools.pulldown",
            "X.splitbutton",
            "X.splitpushbutton",
            "X.stack",
            "X.smartbutton",
            "X.linkbutton",
            "X.panelbutton",
            "X.content",
            "X.combobox",
            "X.checkbox",
            "pushbutton",
            "xpushbutton",
            "X.urlbutton",
            "X.invokebutton",
            "X.nobutton",
            "checks",
            "bin",
            "images",
            "",
        ]
        file_names = [
            "script.py",
            "SCRIPT.PY",
            "a.cs",
            "a.vb",
            "a.rb",
            "a.dyn",
            "a.gh",
            "a.ghx",
            "a.rfa",
            "bundle.yaml",
            "config.json",
            "icon.png",
            "xpy",
            "pyc",
            "script.pyc",
            "notes.txt",
            "",
        ]
        for name in directory_names:
            self.assertEqual(
                bool(re.search(old_dir, name, flags=re.IGNORECASE)),
                bool(re.search(new_dir, name, flags=re.IGNORECASE)),
                name,
            )
        for name in file_names:
            self.assertEqual(
                bool(re.search(old_file, name, flags=re.IGNORECASE)),
                bool(re.search(new_file, name, flags=re.IGNORECASE)),
                name,
            )

    def test_legacy_pattern_is_invalid_on_python3(self):
        """Documents the original failure: the old backslash-l escape does not compile."""
        old_dir = "|".join(
            "(" + chr(92) + name + ")"
            for name in (
                self.components.exts.COMP_LIBRARY_DIR_NAME,
                self.components.exts.COMP_HOOKS_DIR_NAME,
            )
        )
        with self.assertRaises(re.error):
            re.compile(old_dir)

    def test_real_dir_hash_accepts_extension_patterns(self):
        """The real ``calculate_dir_hash`` runs with the extension patterns."""
        with open(
            os.path.join(PYREVIT_ROOT, "coreutils", "__init__.py"), encoding="utf-8"
        ) as source:
            tree = ast.parse(source.read())
        node = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "calculate_dir_hash"
        )
        namespace = {
            "os": os,
            "re": re,
            "op": os.path,
            "get_str_hash": lambda value: value,
            "safe_strtype": str,
        }
        exec(compile(ast.Module([node], []), "coreutils", "exec"), namespace)
        dir_pat, file_pat = self._extension_hash_patterns()
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "Tab.tab", "Btn.pushbutton"))
            with open(
                os.path.join(root, "Tab.tab", "Btn.pushbutton", "script.py"), "w"
            ):
                pass
            result = namespace["calculate_dir_hash"](root, dir_pat, file_pat)
        self.assertTrue(result)

    def test_check_module_loads_when_imp_is_unavailable(self):
        """A check script is loaded through importlib when ``imp`` is gone."""
        with tempfile.TemporaryDirectory() as checks_dir:
            script = os.path.join(checks_dir, "levels_check.py")
            with open(script, "w") as check_file:
                check_file.write("MARKER = 42" + chr(10))
            _, preflight = _load_production_modules(imp_available=False)
            module = preflight._load_check_module("levels", script)
        self.assertEqual(42, module.MARKER)

    def test_importlib_loads_check_with_uppercase_extension(self):
        """A check file whose suffix is ``.PY`` loads through importlib."""
        with tempfile.TemporaryDirectory() as checks_dir:
            script = os.path.join(checks_dir, "Foo_CHECK.PY")
            with open(script, "w") as check_file:
                check_file.write("MARKER = 7" + chr(10))
            _, preflight = _load_production_modules(imp_available=False)
            module = preflight._load_check_module("Foo", script)
            self.addCleanup(sys.modules.pop, module.__name__, None)
        self.assertEqual(7, module.MARKER)

    def test_importlib_check_module_does_not_shadow_stdlib(self):
        """Loading a check named like a stdlib module leaves ``sys.modules`` intact."""
        with tempfile.TemporaryDirectory() as checks_dir:
            script = os.path.join(checks_dir, "json_check.py")
            with open(script, "w") as check_file:
                check_file.write("MARKER = 1" + chr(10))
            _, preflight = _load_production_modules(imp_available=False)
            module = preflight._load_check_module("json", script)
            self.assertIs(json, sys.modules["json"])
        self.assertEqual(1, module.MARKER)

    def test_importlib_check_module_is_registered_under_a_private_name(self):
        """Check classes can resolve their module without touching bare names."""
        with tempfile.TemporaryDirectory() as checks_dir:
            script = os.path.join(checks_dir, "levels_check.py")
            with open(script, "w") as check_file:
                check_file.write("MARKER = 1" + chr(10))
            _, preflight = _load_production_modules(imp_available=False)
            module = preflight._load_check_module("levels", script)
            self.addCleanup(sys.modules.pop, module.__name__, None)
            self.assertIs(module, sys.modules[module.__name__])
        self.assertNotIn("levels", sys.modules)

    def test_importlib_failure_leaves_no_module_registered(self):
        """A check script that raises is not left in ``sys.modules``."""
        with tempfile.TemporaryDirectory() as checks_dir:
            script = os.path.join(checks_dir, "broken_check.py")
            with open(script, "w") as check_file:
                check_file.write("raise RuntimeError('boom')" + chr(10))
            _, preflight = _load_production_modules(imp_available=False)
            before = set(sys.modules)
            with self.assertRaises(RuntimeError):
                preflight._load_check_module("broken", script)
        self.assertEqual(before, set(sys.modules))

    def test_importlib_missing_spec_raises_import_error(self):
        """A script the loader cannot describe fails with ``ImportError``."""
        _, preflight = _load_production_modules(imp_available=False)
        with patch.object(importlib.util, "spec_from_file_location", return_value=None):
            with self.assertRaises(ImportError):
                preflight._load_check_module("levels", "levels_check.py")


def _make_fake_imp():
    """Mimic ``imp.load_source``: reuse a registered module, run into it, keep it on failure."""
    fake = types.ModuleType("imp")

    def load_source(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = sys.modules.get(name) or importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    fake.load_source = load_source
    return fake


CHECK_SOURCE = (
    "from pyrevit.preflight.case import PreflightTestCase"
    + chr(10)
    + "class LevelsCheck(PreflightTestCase):"
    + chr(10)
    + "    'Doc.'"
    + chr(10)
    + "    author = 'a'"
    + chr(10)
    + "    ORIGIN = %r"
    + chr(10)
)


class PrivateCheckModuleNameTests(SysModulesIsolatedTestCase):
    """Checks load under private names on both engines and never shadow modules (#4043)."""

    def _preflight(self, imp_available):
        _, preflight = _load_production_modules(imp_available=imp_available)
        if imp_available:
            preflight.imp = _make_fake_imp()
        return preflight

    def _discover(self, preflight, scripts_by_extension):
        extensions = []
        for index, scripts in enumerate(scripts_by_extension):
            extension = MagicMock()
            extension.name = "Ext%d" % index
            extension.get_checks.return_value = scripts
            extensions.append(extension)
        preflight.extensionmgr.get_installed_ui_extensions.return_value = extensions
        case = types.ModuleType("pyrevit.preflight.case")
        case.PreflightTestCase = preflight.PreflightTestCase
        with patch.dict(sys.modules, {"pyrevit.preflight.case": case}):
            checks = preflight.get_all_preflight_checks()
            self.json_after_discovery = sys.modules["json"]
        return checks

    def _write(self, root, folder, file_name, origin):
        os.makedirs(os.path.join(root, folder), exist_ok=True)
        path = os.path.join(root, folder, file_name)
        with open(path, "w") as check_file:
            check_file.write(CHECK_SOURCE % origin)
        return path

    def _assert_same_named_checks_both_load(self, imp_available):
        preflight = self._preflight(imp_available)
        with tempfile.TemporaryDirectory() as root:
            first = self._write(root, "a", "levels_check.py", "first")
            second = self._write(root, "b", "levels_check.py", "second")
            checks = self._discover(preflight, [[first], [second]])
        self.assertEqual(2, len(checks))
        self.assertEqual(
            ["first", "second"], sorted(c.check_case.ORIGIN for c in checks)
        )
        self.assertNotEqual(checks[0].check_case, checks[1].check_case)

    def test_importlib_same_named_checks_in_two_extensions_both_load(self):
        """Two ``levels_check.py`` files from different extensions are both returned."""
        self._assert_same_named_checks_both_load(imp_available=False)

    def test_imp_same_named_checks_in_two_extensions_both_load(self):
        """The legacy ``imp`` path keeps same-named checks apart too."""
        self._assert_same_named_checks_both_load(imp_available=True)

    def _assert_stdlib_named_check_leaves_stdlib(self, imp_available):
        preflight = self._preflight(imp_available)
        with tempfile.TemporaryDirectory() as root:
            script = self._write(root, "a", "json_check.py", "json")
            checks = self._discover(preflight, [[script]])
        self.assertIs(json, self.json_after_discovery)
        self.assertEqual("json", checks[0].name)

    def test_importlib_check_named_json_leaves_sys_modules_json(self):
        """``json_check.py`` on the importlib path keeps the real ``json`` module."""
        self._assert_stdlib_named_check_leaves_stdlib(imp_available=False)

    def test_imp_check_named_json_leaves_sys_modules_json(self):
        """``json_check.py`` on the ``imp`` path keeps the real ``json`` module."""
        self._assert_stdlib_named_check_leaves_stdlib(imp_available=True)

    def test_imp_loader_receives_prefixed_name_with_path_disambiguator(self):
        """The ``imp`` loader never sees the bare check name."""
        preflight = self._preflight(imp_available=True)
        seen = []
        real = preflight.imp.load_source
        preflight.imp.load_source = lambda name, path: (
            seen.append(name) or real(name, path)
        )
        with tempfile.TemporaryDirectory() as root:
            first = self._write(root, "a", "levels_check.py", "first")
            second = self._write(root, "b", "levels_check.py", "second")
            self._discover(preflight, [[first], [second]])
        self.assertEqual(2, len(set(seen)))
        for name in seen:
            self.assertTrue(name.startswith("pyrevit_preflight_check_levels"))

    def test_non_ascii_check_name_gives_ascii_identifier(self):
        """Python 3 and IronPython 2.7 must agree on an identifier-safe ASCII name."""
        name = self._preflight(imp_available=False)._private_module_name(
            "café_中", os.path.join("x", "café_check.py")
        )
        self.assertRegex(name, r"^pyrevit_preflight_check_[A-Za-z0-9_]+$")

    def test_module_name_does_not_use_hashlib(self):
        """FIPS hosts reject ``hashlib.md5``; the name must not depend on it."""
        import hashlib

        with patch.object(hashlib, "md5", side_effect=ValueError("fips")):
            name = self._preflight(imp_available=False)._private_module_name(
                "levels", os.path.join("a", "levels_check.py")
            )
        self.assertTrue(name.startswith("pyrevit_preflight_check_levels_"))

    def test_module_name_suffix_is_at_least_twelve_hex_chars(self):
        """The path suffix is long enough to be collision-safe in practice."""
        name = self._preflight(imp_available=False)._private_module_name(
            "levels", os.path.join("a", "levels_check.py")
        )
        suffix = name.rsplit("_", 1)[1]
        self.assertRegex(suffix, r"^[0-9a-f]{12,}$")

    def test_same_check_name_in_different_paths_gives_different_names(self):
        """Same file name under two extension folders never share a module name."""
        make = self._preflight(imp_available=False)._private_module_name
        self.assertNotEqual(
            make("levels", os.path.join("a", "levels_check.py")),
            make("levels", os.path.join("b", "levels_check.py")),
        )

    def _failing_script(self, root, source):
        path = os.path.join(root, "flaky_check.py")
        with open(path, "w") as check_file:
            check_file.write(source + chr(10))
        return path

    def _assert_failed_load_restores_previous_entry(self, imp_available):
        preflight = self._preflight(imp_available)
        with tempfile.TemporaryDirectory() as root:
            script = self._failing_script(root, "MARKER = 1")
            module = preflight._load_check_module("flaky", script)
            registered = module.__name__
            self._failing_script(root, "raise RuntimeError('boom')")
            with self.assertRaises(RuntimeError):
                preflight._load_check_module("flaky", script)
        self.assertIs(module, sys.modules[registered])

    def _assert_failed_first_load_registers_nothing(self, imp_available):
        preflight = self._preflight(imp_available)
        with tempfile.TemporaryDirectory() as root:
            script = self._failing_script(root, "raise RuntimeError('boom')")
            before = set(sys.modules)
            with self.assertRaises(RuntimeError):
                preflight._load_check_module("flaky", script)
        self.assertEqual(before, set(sys.modules))

    def test_importlib_failed_reload_restores_previous_module(self):
        """A failing reload does not drop a module that loaded fine before."""
        self._assert_failed_load_restores_previous_entry(imp_available=False)

    def test_imp_failed_reload_restores_previous_module(self):
        """The ``imp`` path restores the earlier entry as the importlib path does."""
        self._assert_failed_load_restores_previous_entry(imp_available=True)

    def test_imp_failed_first_load_registers_nothing(self):
        """A half-initialised module is not left behind on the ``imp`` path."""
        self._assert_failed_first_load_registers_nothing(imp_available=True)

    def test_importlib_failed_first_load_registers_nothing(self):
        """A failed first load leaves ``sys.modules`` untouched."""
        self._assert_failed_first_load_registers_nothing(imp_available=False)

    def test_dotted_check_name_gives_valid_module_name(self):
        """``coord.v2_check.py`` gets an identifier-safe module name."""
        preflight = self._preflight(imp_available=False)
        with tempfile.TemporaryDirectory() as root:
            script = self._write(root, "a", "coord.v2_check.py", "dotted")
            checks = self._discover(preflight, [[script]])
        self.assertEqual(1, len(checks))
        self.assertTrue(checks[0].check_case.__module__.isidentifier())


class BrokenCheckScriptTests(SysModulesIsolatedTestCase):
    """One unloadable check script must not hide the other checks (#4043)."""

    def _discover(self, imp_available):
        _, preflight = _load_production_modules(imp_available=imp_available)
        with tempfile.TemporaryDirectory() as checks_dir:
            broken = os.path.join(checks_dir, "broken_check.py")
            with open(broken, "w") as check_file:
                check_file.write("def (:" + chr(10))
            good = os.path.join(checks_dir, "good_check.py")
            with open(good, "w") as check_file:
                check_file.write("MARKER = 1" + chr(10))
            extension = MagicMock()
            extension.get_checks.return_value = [broken, good]
            preflight.extensionmgr.get_installed_ui_extensions.return_value = [
                extension
            ]
            loaded = []
            real_loader = preflight._load_check_module

            def recording_loader(name, path):
                module = real_loader(name, path)
                loaded.append(name)
                return module

            preflight._load_check_module = recording_loader
            with self.assertLogs(preflight.mlogger, level="ERROR") as logs:
                preflight.get_all_preflight_checks()
        return loaded, logs.output

    def test_importlib_path_skips_broken_script_and_logs(self):
        """A syntax error on the importlib path is logged and discovery goes on."""
        loaded, output = self._discover(imp_available=False)
        self.assertEqual(["good"], loaded)
        self.assertIn("broken_check.py", output[0])

    def test_imp_path_skips_failing_loader_and_logs(self):
        """A loader exception on the imp path is logged and discovery goes on."""
        _, preflight = _load_production_modules(imp_available=True)
        extension = MagicMock()
        extension.get_checks.return_value = ["a_check.py", "b_check.py"]
        preflight.extensionmgr.get_installed_ui_extensions.return_value = [extension]
        attempted = []

        def loader(name, path):
            attempted.append(name)
            raise SyntaxError("bad")

        preflight._load_check_module = loader
        with self.assertLogs(preflight.mlogger, level="ERROR"):
            self.assertEqual([], preflight.get_all_preflight_checks())
        self.assertEqual(["a", "b"], attempted)


if __name__ == "__main__":
    unittest.main()
