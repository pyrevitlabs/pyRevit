"""Exercise preflight check discovery and naming without a Revit host (#4014)."""

import importlib.util
import logging
import os
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


def _load_production_modules():
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
        "imp": MagicMock(),
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


if __name__ == "__main__":
    unittest.main()
