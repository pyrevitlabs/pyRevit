"""Tests for config upgrade helpers."""

import glob
import json
import os
import sys
import tempfile
import types
import unittest

try:
    import importlib.util as importlib_util
except ImportError:  # IronPython 2 / Python 2.7
    importlib_util = None


class _DummyLogger(object):
    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def _load_upgrade_module():
    module_names = (
        'pyrevit',
        'pyrevit.coreutils',
        'pyrevit.coreutils.appdata',
        'pyrevit.coreutils.logger',
    )
    previous = {name: sys.modules.get(name) for name in module_names}

    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        pyrevit_root = os.path.join(repo_root, 'pyrevit')
        coreutils_root = os.path.join(pyrevit_root, 'coreutils')

        appdata_module = types.ModuleType('pyrevit.coreutils.appdata')
        logger_module = types.ModuleType('pyrevit.coreutils.logger')
        logger_module.get_logger = lambda name: _DummyLogger()

        coreutils_module = types.ModuleType('pyrevit.coreutils')
        coreutils_module.__path__ = [coreutils_root]
        coreutils_module.appdata = appdata_module
        coreutils_module.logger = logger_module

        pyrevit_module = types.ModuleType('pyrevit')
        pyrevit_module.__path__ = [pyrevit_root]
        pyrevit_module.coreutils = coreutils_module

        sys.modules['pyrevit'] = pyrevit_module
        sys.modules['pyrevit.coreutils'] = coreutils_module
        sys.modules['pyrevit.coreutils.appdata'] = appdata_module
        sys.modules['pyrevit.coreutils.logger'] = logger_module

        module_path = os.path.join(pyrevit_root, 'versionmgr', 'upgrade.py')
        if importlib_util is None:
            raise unittest.SkipTest('importlib.util is required to load upgrade.py')
        spec = importlib_util.spec_from_file_location(
            'pyrevit_upgrade_test', module_path)
        module = importlib_util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, original in previous.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


upgrade = None


class _FakeTelemetryParser(object):
    def __init__(self, values):
        self._values = values

    def get(self, section_name, field_name):
        return self._values[field_name]


class _FakeTelemetrySection(object):
    def __init__(self, values):
        self._values = values
        self._parser = _FakeTelemetryParser(values)
        self._section_name = 'telemetry'

    def has_option(self, field_name):
        return field_name in self._values

    def __getattr__(self, field_name):
        if field_name in self._values:
            return self._values[field_name]
        raise AttributeError(field_name)

    def __setattr__(self, field_name, value):
        if field_name in ('_values', '_parser', '_section_name'):
            object.__setattr__(self, field_name, value)
        else:
            self._values[field_name] = value


class _FakeUserConfig(object):
    def __init__(self, values, config_file):
        self.telemetry = _FakeTelemetrySection(values)
        self.config_file = config_file

    def has_section(self, section_name):
        return section_name == 'telemetry'


class HealBloatedTelemetryFieldsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Load the upgrade module under test, skipping when unavailable."""
        global upgrade
        try:
            upgrade = _load_upgrade_module()
        except unittest.SkipTest:
            raise
        except Exception as load_err:
            raise unittest.SkipTest(
                'Failed to load upgrade.py: {}'.format(load_err)
            )

    def _make_config(self, values):
        tempdir = tempfile.mkdtemp()
        config_file = os.path.join(tempdir, 'pyrevit_config.ini')
        with open(config_file, 'w') as cfg_file:
            cfg_file.write('[telemetry]\n')
        return _FakeUserConfig(values, config_file), tempdir

    def test_heals_realistically_corrupted_empty_values(self):
        values = {
            'telemetry_file_dir': '"\\"\\"\\""',
            'telemetry_server_url': '"\\"\\"\\"/"/"',
            'apptelemetry_server_url': '"\\"\\"\\"/"/"',
        }
        user_config, tempdir = self._make_config(values)

        healed = upgrade.heal_bloated_telemetry_fields(user_config)

        self.assertEqual(sorted(values), sorted(healed))
        self.assertEqual('', values['telemetry_file_dir'])
        self.assertEqual('', values['telemetry_server_url'])
        self.assertEqual('', values['apptelemetry_server_url'])
        self.assertEqual(
            1,
            len(glob.glob(
                os.path.join(tempdir, 'pyrevit_config.ini.bloated.*.bak'))),
        )

    def test_preserves_valid_below_threshold_values(self):
        values = {
            'telemetry_file_dir': json.dumps(
                'C:\\logs', separators=(',', ':'), ensure_ascii=False),
            'telemetry_server_url': json.dumps(
                'https://telem.example.com',
                separators=(',', ':'),
                ensure_ascii=False),
            'apptelemetry_server_url': json.dumps(
                'https://apptelm.example.com',
                separators=(',', ':'),
                ensure_ascii=False),
        }
        user_config, tempdir = self._make_config(values)

        healed = upgrade.heal_bloated_telemetry_fields(user_config)

        self.assertEqual([], healed)
        self.assertEqual(values['telemetry_file_dir'],
                         json.dumps('C:\\logs',
                                    separators=(',', ':'),
                                    ensure_ascii=False))
        self.assertEqual(
            values['telemetry_server_url'],
            json.dumps('https://telem.example.com',
                       separators=(',', ':'),
                       ensure_ascii=False))
        self.assertEqual(
            values['apptelemetry_server_url'],
            json.dumps('https://apptelm.example.com',
                       separators=(',', ':'),
                       ensure_ascii=False))
        self.assertEqual(
            [],
            glob.glob(
                os.path.join(tempdir, 'pyrevit_config.ini.bloated.*.bak')),
        )

    def test_preserves_empty_values(self):
        values = {
            'telemetry_file_dir': '',
            'telemetry_server_url': '""',
            'apptelemetry_server_url': '',
        }
        user_config, _ = self._make_config(values)

        healed = upgrade.heal_bloated_telemetry_fields(user_config)

        self.assertEqual([], healed)

    def test_heals_oversized_values_by_length(self):
        oversized_value = 'x' * (upgrade.TELEMETRY_FIELD_MAX_LEN + 1)
        values = {'telemetry_server_url': oversized_value}
        user_config, _ = self._make_config(values)

        healed = upgrade.heal_bloated_telemetry_fields(user_config)

        self.assertEqual(['telemetry_server_url'], healed)
        self.assertEqual('', values['telemetry_server_url'])


class RemoveLeftoverTempFilesTests(unittest.TestCase):
    def test_removes_leftover_bak_files_from_universal_data_dir(self):
        with tempfile.TemporaryDirectory() as tempdir:
            keep_file = os.path.join(tempdir, 'keep.txt')
            stale_file = os.path.join(tempdir, 'stale..bak')
            original_get_universal = upgrade.appdata.get_universal_data_file
            original_garbage = getattr(upgrade.appdata, 'garbage_data_file', None)
            try:
                with open(keep_file, 'w') as keep:
                    keep.write('keep me')
                with open(stale_file, 'w') as stale:
                    stale.write('remove me')

                upgrade.appdata.get_universal_data_file = (
                    lambda file_id, file_ext: os.path.join(
                        tempdir, 'X.{}'.format(file_ext)
                    )
                )
                upgrade.appdata.garbage_data_file = os.remove

                upgrade.remove_leftover_temp_files()

                self.assertTrue(os.path.exists(keep_file))
                self.assertFalse(os.path.exists(stale_file))
            finally:
                upgrade.appdata.get_universal_data_file = original_get_universal
                if original_garbage is None:
                    delattr(upgrade.appdata, 'garbage_data_file')
                else:
                    upgrade.appdata.garbage_data_file = original_garbage
