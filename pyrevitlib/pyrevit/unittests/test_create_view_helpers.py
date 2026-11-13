# -*- coding: utf-8 -*-
"""Revit-hosted tests for the view helpers in pyrevit.revit.db.create.

Run from Revit via the pyRevit DevTools "Create View Helpers Tests" button
(doc-project context). Every test rolls back its changes.
"""

import unittest

from pyrevit import DB, revit
from pyrevit.revit.db import create, query, update

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


class CropViewToElementsTests(RolledBackTestCase):
    """Regression tests for #4022."""

    def _view_with_scope_box(self):
        for view in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewPlan):
            parameter = view.get_Parameter(
                DB.BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP
            )
            if (
                not view.IsTemplate
                and parameter is not None
                and parameter.AsElementId() != DB.ElementId.InvalidElementId
            ):
                return view
        self.skipTest("No plan view with a scope box in the document")

    def test_crop_applies_on_a_view_with_a_scope_box(self):
        """The crop box is set even though the view had a scope box."""
        view = self._view_with_scope_box()
        elements = query.get_model_elements()
        if not elements:
            self.skipTest("No model elements to crop to")
        before = view.CropBox.Max.X - view.CropBox.Min.X
        update.crop_view_to_elements(view, elements, padding=1.0)
        after = view.CropBox.Max.X - view.CropBox.Min.X
        self.assertNotAlmostEqual(before, after)
        self.assertTrue(view.CropBoxActive)


class CreateModel3dViewTests(RolledBackTestCase):
    """Regression tests for #4023."""

    def test_section_box_hugs_the_model(self):
        """The default section box is the model's extents plus padding."""
        elements = query.get_model_elements()
        if not elements:
            self.skipTest("No model elements to frame")
        extents = query.get_elements_bounding_box(elements)
        view = create.create_model_3d_view()
        box = view.GetSectionBox()
        for axis in ("X", "Y", "Z"):
            model_size = getattr(extents.Max, axis) - getattr(extents.Min, axis)
            box_size = getattr(box.Max, axis) - getattr(box.Min, axis)
            self.assertLess(box_size, model_size + 10.0)
