# -*- coding: utf-8 -*-
"""Revit-hosted tests for the view helpers in pyrevit.revit.db.create.

Run from Revit via the pyRevit DevTools "Create View Helpers Tests" button
(doc-project context). Every test rolls back its changes.
"""

import unittest

from pyrevit import DB, PyRevitException, revit
from pyrevit.revit.db import create, query, update

TEST_LEVEL = "Integration"
TEST_ENVIRONMENT = "Revit"
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

    PADDING = 1.0

    def _first_scope_box(self):
        scope_boxes = (
            DB.FilteredElementCollector(revit.doc)
            .OfCategory(DB.BuiltInCategory.OST_VolumeOfInterest)
            .WhereElementIsNotElementType()
            .ToElements()
        )
        if not scope_boxes:
            self.skipTest("No scope box in the document to assign")
        return scope_boxes[0]

    def _plan_view_with_scope_box(self, scope_box):
        level = DB.Level.Create(revit.doc, 0.0)
        plan_type = next(
            vft
            for vft in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType)
            if vft.ViewFamily == DB.ViewFamily.FloorPlan
        )
        view = DB.ViewPlan.Create(revit.doc, plan_type.Id, level.Id)
        parameter = view.get_Parameter(
            DB.BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP
        )
        parameter.Set(scope_box.Id)
        revit.doc.Regenerate()
        return view, level

    def _wall_wider_than(self, level, width):
        line = DB.Line.CreateBound(
            DB.XYZ(0.0, 0.0, 0.0), DB.XYZ(width + 20.0, 0.0, 0.0)
        )
        return DB.Wall.Create(revit.doc, line, level.Id, False)

    def test_crop_applies_on_a_view_with_a_scope_box(self):
        """The crop box matches the elements even though the view had a scope box."""
        view, level = self._plan_view_with_scope_box(self._first_scope_box())
        scope_width = view.CropBox.Max.X - view.CropBox.Min.X
        wall = self._wall_wider_than(level, scope_width)
        revit.doc.Regenerate()
        extents = query.get_elements_bounding_box([wall])
        expected_width = extents.Max.X - extents.Min.X + 2 * self.PADDING
        self.assertNotAlmostEqual(scope_width, expected_width)
        update.crop_view_to_elements(view, [wall], padding=self.PADDING)
        revit.doc.Regenerate()
        self.assertTrue(view.CropBoxActive)
        self.assertAlmostEqual(
            view.CropBox.Max.X - view.CropBox.Min.X, expected_width, delta=1e-3
        )


class CreateModel3dViewTests(RolledBackTestCase):
    """Regression tests for #4023."""

    def _create_sheet_and_camera(self):
        DB.ViewSheet.Create(revit.doc, DB.ElementId.InvalidElementId)
        view3d_type = next(
            vft
            for vft in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType)
            if vft.ViewFamily == DB.ViewFamily.ThreeDimensional
        )
        DB.View3D.CreatePerspective(revit.doc, view3d_type.Id)
        revit.doc.Regenerate()

    def test_model_elements_leave_out_sheets_and_cameras(self):
        """Sheets and cameras have extents far beyond the building."""
        self._create_sheet_and_camera()
        excluded_ids = [
            DB.ElementId(DB.BuiltInCategory.OST_Sheets),
            DB.ElementId(DB.BuiltInCategory.OST_Cameras),
        ]
        existing = [
            element
            for element in DB.FilteredElementCollector(
                revit.doc
            ).WhereElementIsNotElementType()
            if element.Category is not None and element.Category.Id in excluded_ids
        ]
        found_categories = set(element.Category.Id for element in existing)
        self.assertEqual(
            len(found_categories),
            len(excluded_ids),
            "fixtures must create both a sheet and a camera",
        )
        leaked = [
            element
            for element in query.get_model_elements()
            if element.Category.Id in excluded_ids
        ]
        self.assertEqual(leaked, [])

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


class PlaceOnSheetTests(RolledBackTestCase):
    """Regression tests for #4024."""

    def test_a_sheet_is_rejected_as_a_view(self):
        """Passing a sheet names it as a sheet instead of blaming the sheet it is on."""
        sheet = DB.ViewSheet.CreatePlaceholder(revit.doc)
        other = DB.ViewSheet.CreatePlaceholder(revit.doc)
        with self.assertRaises(PyRevitException) as caught:
            create.place_on_sheet(sheet, other)
        self.assertIn("not a view", str(caught.exception))
