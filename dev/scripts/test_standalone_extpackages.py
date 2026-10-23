"""Exercise extension config initialization without a Revit host."""

import importlib.util
import json
import logging
import os
import sys
import types
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
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


class ExtensionPackageConfigTests(unittest.TestCase):
    """Protect package state when another subsystem creates its section first."""

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

    def test_new_section_persists_defaults(self):
        """Keep the non-credential installation path unchanged."""
        config = self.package.config

        self.assertFalse(config.disabled)
        self.assertFalse(config.private_repo)
        self.assertEqual(1, len(self.saved))
        self.assertEqual("false", self.saved[-1]["Example.extension"]["disabled"])

    def test_credential_created_section_persists_missing_defaults(self):
        """Token-first installation must persist load state without losing auth."""
        config = self.sections.add_section("Example.extension")
        config.credential = "sealed-test-credential"
        config.private_repo = True

        self.assertTrue(self.package.is_enabled)

        self.assertFalse(config.disabled)
        self.assertTrue(config.private_repo)
        self.assertEqual("sealed-test-credential", config.credential)
        self.assertEqual(1, len(self.saved))
        self.assertEqual("false", self.saved[-1]["Example.extension"]["disabled"])
        self.assertEqual(
            '"sealed-test-credential"',
            self.saved[-1]["Example.extension"]["credential"],
        )

    def test_credential_only_section_initializes_both_defaults(self):
        """Honor manifest defaults even when credentials precede package state."""
        config = self.sections.add_section("Example.extension")
        config.credential = "sealed-test-credential"
        self.package.default_enabled = False
        self.package.builtin = True

        self.assertFalse(self.package.is_enabled)

        self.assertTrue(config.disabled)
        self.assertTrue(config.private_repo)
        self.assertEqual("sealed-test-credential", config.credential)

    def test_partial_section_preserves_disabled_state(self):
        """Repairing unrelated defaults must not re-enable a disabled package."""
        config = self.sections.add_section("Example.extension")
        config.disabled = True

        self.assertFalse(self.package.is_enabled)

        self.assertTrue(config.disabled)
        self.assertFalse(config.private_repo)
        self.assertEqual(1, len(self.saved))

    def test_complete_section_is_not_overwritten_or_saved(self):
        """Explicit user choices take precedence over changed manifest defaults."""
        config = self.sections.add_section("Example.extension")
        config.disabled = False
        config.private_repo = False
        self.package.default_enabled = False
        self.package.builtin = True

        self.assertTrue(self.package.is_enabled)
        self.assertFalse(self.package.config.private_repo)
        self.assertEqual([], self.saved)

    def test_repeated_access_does_not_save_again(self):
        """Normal package reads must not repeatedly write the configuration."""
        self.package.config
        self.package.config

        self.assertEqual(1, len(self.saved))

    def test_config_read_errors_are_not_treated_as_missing_sections(self):
        """A backend failure must not reset existing package state."""
        self.sections.add_section("Example.extension")
        with patch.object(
            self.extpackages.user_config,
            "get_section",
            side_effect=RuntimeError("Config read failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Config read failed"):
                self.package.config


if __name__ == "__main__":
    unittest.main()
