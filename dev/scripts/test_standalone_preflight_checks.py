"""Exercise preflight check discovery and naming without a Revit host (#4014)."""

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


class Python3CompatibilityTests(unittest.TestCase):
    """Regressions for CPython 3 failures in extension hashing and check loading (#4043)."""

    @classmethod
    def setUpClass(cls):
        """Load production modules with only host dependencies replaced."""
        cls.components, cls.preflight = _load_production_modules()

    def test_extension_dir_hash_patterns_compile(self):
        """The directory and file filters handed to the hash are valid regexes."""
        captured = []
        self.components.coreutils.calculate_dir_hash = (
            lambda directory, dir_pat, file_pat: (
                captured.append((dir_pat, file_pat)) or ""
            )
        )
        ui = MagicMock()
        ui.get_current_theme.return_value = "light"
        revit = types.ModuleType("pyrevit.revit")
        revit.ui = ui
        extension = self.components.Extension.__new__(self.components.Extension)
        extension.directory = "unused"
        with patch.dict(sys.modules, {"pyrevit.revit": revit, "pyrevit.revit.ui": ui}):
            extension._calculate_extension_dir_hash()
        dir_pat, file_pat = captured[0]
        self.assertTrue(re.search(dir_pat, "lib"))
        self.assertTrue(re.search(dir_pat, "hooks"))
        self.assertTrue(re.search(dir_pat, "My.pushbutton"))
        self.assertTrue(re.search(file_pat, "script.py"))

    def test_check_module_loads_when_imp_is_unavailable(self):
        """A check script is loaded through importlib when ``imp`` is gone."""
        with tempfile.TemporaryDirectory() as checks_dir:
            script = os.path.join(checks_dir, "levels_check.py")
            with open(script, "w") as check_file:
                check_file.write("MARKER = 42" + chr(10))
            _, preflight = _load_production_modules(imp_available=False)
            module = preflight._load_check_module("levels", script)
        self.assertEqual(42, module.MARKER)

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


if __name__ == "__main__":
    unittest.main()
