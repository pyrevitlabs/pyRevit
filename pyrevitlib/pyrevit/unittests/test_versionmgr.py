# -*- coding: utf-8 -*-
"""Hosted unit tests for the pyrevit.versionmgr module.

Run from Revit via the DevTools "Run All Tests" button, which discovers every
``test_*`` module in this package. The tests pin the contract the reported
version depends on: the build the session loaded wins over the clone's version
file, an unresolvable session value degrades to the version file instead of
leaking "Unknown" into the About window, and both feed the same formatter.
"""

import unittest

from pyrevit import versionmgr
from pyrevit.coreutils import envvars


class ParseVersionStringTests(unittest.TestCase):
    """Parsing of a build version into its parts."""

    def test_build_metadata_is_split_off(self):
        """The build number and time stay in the metadata slot."""
        self.assertEqual(
            (7, 0, 0, "26273+1554"), versionmgr.parse_version_string("7.0.0.26273+1554")
        )

    def test_non_zero_patch_is_kept(self):
        """A patch release keeps its patch component."""
        self.assertEqual(
            (7, 0, 1, "26250+1610"), versionmgr.parse_version_string("7.0.1.26250+1610")
        )

    def test_channel_suffix_stays_in_metadata(self):
        """A channel suffix is part of the reported version, not dropped."""
        self.assertEqual(
            (7, 0, 0, "26273-wip+1554"),
            versionmgr.parse_version_string("7.0.0.26273-wip+1554"),
        )

    def test_version_without_metadata(self):
        """A bare three-part version parses with empty metadata."""
        self.assertEqual((7, 0, 0, ""), versionmgr.parse_version_string("7.0.0"))

    def test_surrounding_whitespace(self):
        """The value read back from the env dict may carry whitespace."""
        self.assertEqual(
            (7, 0, 0, "26273+1554"),
            versionmgr.parse_version_string("  7.0.0.26273+1554\r\n"),
        )

    def test_unusable_values(self):
        """Anything that is not a version parses to None."""
        for value in ("Unknown", "", "   ", None):
            self.assertIsNone(
                versionmgr.parse_version_string(value), "value=%r" % (value,)
            )

    def test_a_version_embedded_in_junk_is_rejected(self):
        """A version behind leading text must not be extracted.

        The metadata slot stays permissive on purpose - it has to carry both
        the ``yyDDD+HHmm`` build number and the ``-wip`` channel suffix - so
        only the anchoring of the version itself is asserted here.
        """
        for value in ("pyRevit 7.0.0.26273+1554", "v7.0.0", "PYREVIT_VERSION=7.0.0.1"):
            self.assertIsNone(
                versionmgr.parse_version_string(value), "value=%r" % (value,)
            )


class LoadedBuildVersionTests(unittest.TestCase):
    """The loaded build outranks the clone's version file."""

    def setUp(self):
        """Preserve the value the running session seeded."""
        self._seeded = envvars.get_pyrevit_env_var(envvars.VERSION_ENVVAR)

    def tearDown(self):
        """Leave the session env dict as it was found."""
        envvars.set_pyrevit_env_var(envvars.VERSION_ENVVAR, self._seeded)

    def test_seeded_build_is_reported(self):
        """A session-seeded build is what the About window shows.

        The sentinel differs from every real version on this machine, so this
        fails against a formatter that reads the clone's version file instead.
        """
        envvars.set_pyrevit_env_var(envvars.VERSION_ENVVAR, "9.9.9.99999+9999")
        self.assertEqual(
            "9.9.9.99999+9999", versionmgr.get_pyrevit_version().get_formatted()
        )

    def test_strict_drops_only_the_build(self):
        """Strict reporting drops the build without dropping the release line."""
        envvars.set_pyrevit_env_var(envvars.VERSION_ENVVAR, "9.9.9.99999+9999")
        self.assertEqual(
            "9.9.9", versionmgr.get_pyrevit_version().get_formatted(strict=True)
        )

    def test_extended_keeps_the_commit_signature(self):
        """Extended reporting still appends the commit the clone sits on."""
        envvars.set_pyrevit_env_var(envvars.VERSION_ENVVAR, "9.9.9.99999+9999")
        formatted = versionmgr.get_pyrevit_version().get_formatted(extended=True)
        self.assertTrue(formatted.startswith("9.9.9.99999+9999:"))
        self.assertEqual(len(formatted.rsplit(":", 1)[1]), 7)

    def test_unresolvable_session_value_degrades_to_the_version_file(self):
        """An unresolvable seed must not reach the user-facing string."""
        envvars.set_pyrevit_env_var(envvars.VERSION_ENVVAR, "Unknown")
        reported = versionmgr.get_pyrevit_version().get_formatted()
        self.assertNotEqual("Unknown", reported)
        self.assertIsNotNone(versionmgr.parse_version_string(reported))
        self.assertEqual(reported, versionmgr._PyRevitVersion("").get_formatted())

    def test_int_tuple_carries_the_patch(self):
        """The integer tuple reports the patch its docstring promises."""
        envvars.set_pyrevit_env_var(envvars.VERSION_ENVVAR, "7.0.1.26250+1610")
        major, minor, patch = versionmgr.get_pyrevit_version().as_int_tuple()
        self.assertEqual((7, 0, 1), (major, minor, patch))

    def test_int_tuple_keeps_a_two_digit_patch_decimal(self):
        """A two-digit patch is not reinterpreted with a base."""
        envvars.set_pyrevit_env_var(envvars.VERSION_ENVVAR, "7.0.10.26250+1610")
        self.assertEqual((7, 0, 10), versionmgr.get_pyrevit_version().as_int_tuple())

    def test_str_tuple_carries_the_patch(self):
        """The string tuple reports the patch as written."""
        envvars.set_pyrevit_env_var(envvars.VERSION_ENVVAR, "7.0.1.26250+1610")
        self.assertEqual(
            ("7", "0", "1"), versionmgr.get_pyrevit_version().as_str_tuple()
        )
