"""Exercise extension load-state resolution without a Revit host."""

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Integration"


import importlib.util
import json
import logging
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = str(Path(__file__).resolve().parents[4])
PYREVIT_ROOT = os.path.join(REPO_ROOT, "pyrevitlib", "pyrevit")


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Configuration:
    def __init__(self):
        self.sections = {}

    def HasSection(self, name):
        return name in self.sections

    def AddSection(self, name):
        self.sections.setdefault(name, {})

    def HasSectionKey(self, name, key):
        return key in self.sections[name]

    def GetRawValueOrDefault(self, name, key, default=None):
        return self.sections[name].get(key, default)

    def SetRawValue(self, name, key, value):
        self.sections[name][key] = value


def _load_extpackages():
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.PyRevitException = Exception
    pyrevit.HOST_APP = types.SimpleNamespace(username="test-user")
    pyrevit.labs = types.ModuleType("pyrevit.labs")
    coreutils = types.ModuleType("pyrevit.coreutils")
    coreutils.git = types.SimpleNamespace()
    coreutils.fully_remove_dir = lambda path: None
    logger = types.ModuleType("pyrevit.coreutils.logger")
    logger.get_logger = logging.getLogger
    compat = types.ModuleType("pyrevit.compat")
    compat.safe_strtype = str
    extensions = types.ModuleType("pyrevit.extensions")
    ui_extension = types.SimpleNamespace(ID="extension", POSTFIX=".extension")
    lib_extension = types.SimpleNamespace(ID="lib", POSTFIX=".lib")
    extensions.ExtensionTypes = types.SimpleNamespace(
        UI_EXTENSION=ui_extension,
        get_ext_types=lambda: [ui_extension, lib_extension],
    )
    extensions.JSON_FILE_FORMAT = ".json"
    pyrevit.extensions = extensions
    userconfig = types.ModuleType("pyrevit.userconfig")
    userconfig.user_config = None
    modules = {
        "pyrevit": pyrevit,
        "pyrevit.compat": compat,
        "pyrevit.coreutils": coreutils,
        "pyrevit.coreutils.logger": logger,
        "pyrevit.extensions": extensions,
        "pyrevit.userconfig": userconfig,
    }
    with patch.dict(sys.modules, modules):
        configparser = _load_module(
            "_test_configparser",
            os.path.join(PYREVIT_ROOT, "coreutils", "configparser.py"),
        )
        extpackages = _load_module(
            "_test_extpackages",
            os.path.join(PYREVIT_ROOT, "extensions", "extpackages.py"),
        )
    return extpackages, configparser


class ExtensionPackageLoadStateTests(unittest.TestCase):
    """Load state resolves the manifest default when no choice is stored."""

    @classmethod
    def setUpClass(cls):
        """Load production modules with only host dependencies replaced."""
        cls.extpackages, cls.configparser = _load_extpackages()

    def setUp(self):
        """Isolate settings and capture snapshots at each persistence boundary."""
        self.backend = _Configuration()
        self.sections = self.configparser.ConfigSections(
            types.SimpleNamespace(Configuration=self.backend)
        )
        self.saved = []
        user_config = types.SimpleNamespace(
            has_section=self.sections.has_section,
            get_section=self.sections.get_section,
            add_section=self.sections.add_section,
            save_changes=lambda: self.saved.append(
                json.loads(json.dumps(self.backend.sections))
            ),
            get_ext_root_dirs=lambda: [],
        )
        self.config_patch = patch.object(self.extpackages, "user_config", user_config)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.package = self.extpackages.ExtensionPackage(
            {"name": "Example", "url": "https://example.com/example.git"}
        )

    def _assert_nothing_written(self, before):
        self.assertEqual([], self.saved)
        self.assertEqual(before, self.backend.sections)

    def _credential_only_section(self):
        config = self.sections.add_section("Example.extension")
        config.credential = "sealed-test-credential"
        return json.loads(json.dumps(self.backend.sections))

    def test_absent_section_uses_manifest_default(self):
        """No section at all: the manifest default decides and nothing is created."""
        self.assertTrue(self.package.is_enabled)
        self.package.default_enabled = False
        self.assertFalse(self.package.is_enabled)

        self._assert_nothing_written({})

    def test_credential_only_section_honours_opt_out_manifest(self):
        """A section created by storing a credential is not an explicit enable."""
        before = self._credential_only_section()
        self.package.default_enabled = False

        self.assertFalse(self.package.is_enabled)
        self._assert_nothing_written(before)

    def test_credential_only_section_honours_default_manifest(self):
        """Reading the load state must not raise when the key is absent."""
        before = self._credential_only_section()

        self.assertTrue(self.package.is_enabled)
        self._assert_nothing_written(before)

    def test_explicit_disable_wins_over_manifest(self):
        """An explicit disabled=true is honoured regardless of the manifest."""
        self.sections.add_section("Example.extension").disabled = True
        before = json.loads(json.dumps(self.backend.sections))

        self.assertFalse(self.package.is_enabled)
        self._assert_nothing_written(before)

    def test_explicit_enable_wins_over_manifest(self):
        """An explicit disabled=false is honoured regardless of the manifest."""
        self.sections.add_section("Example.extension").disabled = False
        before = json.loads(json.dumps(self.backend.sections))
        self.package.default_enabled = False

        self.assertTrue(self.package.is_enabled)
        self._assert_nothing_written(before)

    def test_config_access_seeds_nothing(self):
        """The write path creates the section but persists no defaults."""
        self.package.default_enabled = False
        self.package.builtin = True

        config = self.package.config

        self.assertFalse(config.has_option("disabled"))
        self.assertFalse(config.has_option("private_repo"))
        self.assertEqual([], self.saved)

    def test_toggle_from_manifest_default_stores_explicit_choice(self):
        """Toggling an opt-out package with no stored choice enables it."""
        before = self._credential_only_section()
        self.package.default_enabled = False

        self.package.toggle_package()

        section = self.backend.sections["Example.extension"]
        self.assertEqual("false", section["disabled"])
        self.assertEqual(
            before["Example.extension"]["credential"], section["credential"]
        )
        self.assertNotIn("private_repo", section)
        self.assertTrue(self.package.is_enabled)
        self.assertEqual(1, len(self.saved))


if __name__ == "__main__":
    unittest.main()
