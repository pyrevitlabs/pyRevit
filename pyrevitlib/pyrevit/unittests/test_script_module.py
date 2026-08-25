# -*- coding: utf-8 -*-
"""Hosted unit tests for the pyrevit.script module.

Run from Revit via the DevTools "Script Module Tests" button (zero-doc
context) or the "Run All Tests" aggregator. The tests assert the
command-runtime contract: logger/output access, bundle file resolution,
data file helpers, and environment variable round trips.
"""

import os
import unittest


class ScriptInfoTests(unittest.TestCase):
    """Command metadata exposed to running scripts."""

    def setUp(self):
        """Resolve the running command info object."""
        from pyrevit import script

        self.info = script.get_info()

    def test_info_available(self):
        """Command info resolves for the running command."""
        self.assertIsNotNone(self.info)
        self.assertTrue(self.info.name)

    def test_unique_name_format(self):
        """Unique command name is lowercase with no whitespace."""
        unique_name = self.info.unique_name
        self.assertTrue(unique_name)
        self.assertEqual(unique_name.lower(), unique_name)
        self.assertNotIn(" ", unique_name)

    def test_script_file_exists(self):
        """Resolved script file exists inside the bundle."""
        self.assertIsNotNone(self.info.script_file)
        self.assertTrue(os.path.isfile(self.info.script_file))


class ScriptLoggerTests(unittest.TestCase):
    """Logger wrapper exposes the extended level methods."""

    def setUp(self):
        """Grab the pyRevit logger wrapper."""
        from pyrevit import script

        self.logger = script.get_logger()

    def test_standard_levels(self):
        """Standard logging levels are callable."""
        for level in ("debug", "info", "warning", "error", "critical"):
            self.assertTrue(callable(getattr(self.logger, level)))

    def test_extended_levels(self):
        """pyRevit-specific levels are callable."""
        for level in ("success", "deprecate", "dev_log"):
            self.assertTrue(callable(getattr(self.logger, level)))


class BundleFileTests(unittest.TestCase):
    """Bundle resource resolution relative to the command bundle."""

    def setUp(self):
        """Grab the script module helpers."""
        from pyrevit import script

        self.script = script

    def test_get_bundle_file_missing_returns_none(self):
        """Missing resources resolve to None."""
        self.assertIsNone(
            self.script.get_bundle_file("definitely_missing_resource.xyz")
        )

    def test_get_bundle_files_missing_returns_none(self):
        """Missing sub-paths resolve to a falsy result."""
        self.assertFalse(self.script.get_bundle_files("definitely_missing_folder/"))

    def test_get_bundle_file_existing(self):
        """Bundle metadata file resolves to an existing path."""
        filepath = self.script.get_bundle_file("bundle.yaml")
        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.isfile(filepath))

    def test_bundle_directory_exists(self):
        """The resolved bundle directory exists on disk."""
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
        self.assertTrue(os.path.isdir(bundle_dir))


class DataFileTests(unittest.TestCase):
    """Data file helpers create, read, and remove slot files."""

    def setUp(self):
        """Grab the script module helpers and reset the probe path."""
        from pyrevit import script

        self.script = script
        self.filepath = None

    def tearDown(self):
        """Remove any data file created by the test."""
        if self.filepath and os.path.isfile(self.filepath):
            self.script.remove_data_file(self.filepath)

    def test_instance_data_file_round_trip(self):
        """Instance data files persist content between calls in a session."""
        filepath = self.script.get_instance_data_file("unittest_probe")
        self.filepath = filepath
        with open(filepath, "w") as data_file:
            data_file.write("pyrevit")

        self.assertTrue(os.path.isfile(filepath))
        with open(filepath, "r") as data_file:
            self.assertEqual("pyrevit", data_file.read())


class EnvVarTests(unittest.TestCase):
    """Environment variable helpers round trip values."""

    def test_set_get_envvar(self):
        """Stored env var values are returned by the getter."""
        from pyrevit import script

        script.set_envvar("PYREVIT_UNITTEST_PROBE", "probe_value")
        self.assertEqual("probe_value", script.get_envvar("PYREVIT_UNITTEST_PROBE"))
