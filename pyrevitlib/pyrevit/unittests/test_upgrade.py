"""Tests for config upgrade helpers."""

import glob
import importlib.util
import os
import sys
import tempfile
import types
import unittest


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
    appdata_module = types.ModuleType('pyrevit.coreutils.appdata')
    logger_module = types.ModuleType('pyrevit.coreutils.logger')
    logger_module.get_logger = lambda name: _DummyLogger()

    coreutils_module = types.ModuleType('pyrevit.coreutils')
    coreutils_module.appdata = appdata_module

    pyrevit_module = types.ModuleType('pyrevit')
    pyrevit_module.coreutils = coreutils_module

    sys.modules['pyrevit'] = pyrevit_module
    sys.modules['pyrevit.coreutils'] = coreutils_module
    sys.modules['pyrevit.coreutils.appdata'] = appdata_module
    sys.modules['pyrevit.coreutils.logger'] = logger_module

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    module_path = os.path.join(repo_root, 'pyrevit', 'versionmgr', 'upgrade.py')
    spec = importlib.util.spec_from_file_location('pyrevit_upgrade_test', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


upgrade = _load_upgrade_module()


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
            len(glob.glob(os.path.join(tempdir, 'pyrevit_config.ini.bloated.*.bak'))),
        )

    def test_preserves_valid_below_threshold_values(self):
        values = {
            'telemetry_file_dir': 'C:\\logs',
            'telemetry_server_url': 'https://telem.example.com',
            'apptelemetry_server_url': 'https://apptelm.example.com',
        }
        user_config, tempdir = self._make_config(values)

        healed = upgrade.heal_bloated_telemetry_fields(user_config)

        self.assertEqual([], healed)
        self.assertEqual('C:\\logs', values['telemetry_file_dir'])
        self.assertEqual('https://telem.example.com', values['telemetry_server_url'])
        self.assertEqual(
            'https://apptelm.example.com',
            values['apptelemetry_server_url'],
        )
        self.assertEqual(
            [],
            glob.glob(os.path.join(tempdir, 'pyrevit_config.ini.bloated.*.bak')),
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
