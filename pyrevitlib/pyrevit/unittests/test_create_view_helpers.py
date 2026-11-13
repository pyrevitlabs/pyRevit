# -*- coding: utf-8 -*-
"""Revit-hosted tests for the view helpers in pyrevit.revit.db.create.

Run from Revit via the pyRevit DevTools "Create View Helpers Tests" button
(doc-project context). Every test rolls back its changes.
"""

import unittest

from pyrevit import DB, revit
from pyrevit.revit.db import create

TEST_LEVEL = "Integration"
TOLERANCE = 1e-6


class RolledBackTestCase(unittest.TestCase):
    """Runs each test inside a transaction that is rolled back."""

    def setUp(self):
        """Skip family documents and open the transaction."""
        if revit.doc.IsFamilyDocument:
            self.skipTest("Requires model document, not family document")
        self.transaction = DB.Transaction(revit.doc, "create view helpers test")
        self.transaction.Start()

    def tearDown(self):
        """Roll back the transaction."""
        self.transaction.RollBack()


class CreateSectionViewTests(RolledBackTestCase):
    """Regression tests for #4017."""

    def _assert_section(self, start, end, looks_toward):
        view = create.create_section_view(start, end, depth=20)
        looking = view.ViewDirection.Negate()
        self.assertTrue(
            looking.IsAlmostEqualTo(DB.XYZ(*looks_toward)),
            "section looks {}, expected {}".format(looking, looks_toward),
        )
        along = DB.XYZ(end[0] - start[0], end[1] - start[1], 0.0).Normalize()
        offset = DB.XYZ(view.Origin.X - start[0], view.Origin.Y - start[1], 0.0)
        self.assertLess(abs(offset.CrossProduct(along).Z), TOLERANCE)

    def test_west_to_east_looks_north_and_cuts_on_the_line(self):
        """A line drawn west to east cuts on the line and looks north."""
        self._assert_section((-6, 16), (36, 16), (0, 1, 0))

    def test_south_to_north_looks_west_and_cuts_on_the_line(self):
        """A line drawn south to north cuts on the line and looks west."""
        self._assert_section((14.25, -12), (14.25, 36), (-1, 0, 0))
