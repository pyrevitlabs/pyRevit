# -*- coding: utf-8 -*-
"""Revit-hosted tests for pyrevit.revit.avf schema/unit handling.

Run from Revit via the pyRevit DevTools "AVF Module Tests" button
(doc-project context, with an AVF-capable active view such as a 3D view).

Regression coverage for the empty-unit trap: ``update_avf_values`` and
``display_avf_values_at_points`` must be safe to call as the *first* call on a
view (before ``display_avf_values`` has registered a schema, or after
``clear_avf_results``/on a fresh view). They must not register an AVF schema
with an empty unit name, which Revit's ``AnalysisResultSchema.SetUnits``
rejects with ``ArgumentsInconsistentException``.
"""

import time
import unittest

from pyrevit import DB, PyRevitException, revit
from pyrevit.revit import avf


def _unique_schema_name(prefix):
    """Return a schema name that won't collide with an existing one.

    Guarantees the ``_get_or_create_schema`` "register a new schema" branch
    is exercised (i.e. a genuine first call), rather than reusing a schema a
    previous run/tool already registered on the view.
    """
    return "{}_{}".format(prefix, int(time.time() * 1000))


class AvfSchemaUnitTests(unittest.TestCase):
    """Regression tests for AVF schema unit handling on first calls."""

    def setUp(self):
        if revit.doc.IsFamilyDocument:
            self.skipTest("Requires model document, not family document")
        self.view = revit.active_view

    def _run_or_skip_no_avf(self, func):
        """Run ``func`` but skip the test if the active view can't do AVF."""
        try:
            return func()
        except PyRevitException as ex:
            self.skipTest("Active view does not support AVF: {}".format(ex))

    def test_display_points_default_unit_first_call(self):
        """display_avf_values_at_points registers a schema on a first call.

        With the default unit this must not raise ArgumentsInconsistentException.
        """
        origin = DB.XYZ(0, 0, 0)
        sfp_ids = self._run_or_skip_no_avf(
            lambda: avf.display_avf_values_at_points(
                [(origin, 1.0)],
                self.view,
                schema_name=_unique_schema_name("pyRevitAVF_Test_Points"),
            )
        )
        self.assertEqual(len(sfp_ids), 1)

    def test_update_values_default_unit_first_call(self):
        """update_avf_values registers a schema on a first call.

        With the default unit this must not raise ArgumentsInconsistentException,
        even when there are no primitives/elements to update yet.
        """
        results = self._run_or_skip_no_avf(
            lambda: avf.update_avf_values(
                {},
                {},
                self.view,
                schema_name=_unique_schema_name("pyRevitAVF_Test_Update"),
            )
        )
        self.assertEqual(results, {})

    def test_explicit_empty_unit_is_sanitized(self):
        """An explicit empty unit is sanitized rather than raising."""
        origin = DB.XYZ(0, 0, 0)
        sfp_ids = self._run_or_skip_no_avf(
            lambda: avf.display_avf_values_at_points(
                [(origin, 1.0)],
                self.view,
                schema_name=_unique_schema_name("pyRevitAVF_Test_EmptyUnit"),
                unit="",
            )
        )
        self.assertEqual(len(sfp_ids), 1)

    def tearDown(self):
        # AVF results are session-only and not saved with the document, but
        # clear them anyway so repeated test runs start from a clean view.
        try:
            avf.clear_avf_results(self.view)
        except Exception:
            pass
