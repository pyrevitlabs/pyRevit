"""Host-free tests for the Section Box Navigator's view range reading and editing.

Loads ``sectionbox_viewrange_rules.py``, which imports nothing from Revit, and
``sectionbox_viewrange.py`` with a stubbed ``pyrevit`` module. The fake view
range keeps what Revit was measured to do: it does not move the Bottom plane of
a ceiling plan with the cut plane.
"""

import importlib.util
import pathlib
import sys
import types
import unittest

import pytest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

BUNDLE = (
    pathlib.Path(__file__).resolve().parents[4]
    / "extensions"
    / "pyRevitTools.extension"
    / "pyRevit.tab"
    / "Modify.panel"
    / "3D.pulldown"
    / "Section Box Navigator.pushbutton"
)

UNLIMITED, LEVEL_ABOVE, CURRENT, LEVEL_BELOW = -1, -2, -3, -4


class Level:
    def __init__(self, name, elevation):
        self.Name = name
        self.ProjectElevation = elevation


class FakeViewRange:
    def __init__(self, planes):
        self.planes = dict((name, list(value)) for name, value in planes.items())

    def GetLevelId(self, plane):
        return self.planes[plane][0]

    def GetOffset(self, plane):
        return self.planes[plane][1]

    def SetOffset(self, plane, offset):
        self.planes[plane][1] = offset


class FakeDocument:
    def __init__(self, elements):
        self.elements = elements

    def GetElement(self, element_id):
        return self.elements.get(element_id)


class FakeView:
    def __init__(self, view_type, planes, template=None):
        self.ViewType = view_type
        self.GenLevel = Level("L2", 10.0)
        self.planes = planes
        elements = {1: self.GenLevel, 2: Level("L3", 20.0)}
        self.ViewTemplateId = -1
        if template is not None:
            self.ViewTemplateId = 99
            elements[99] = template
        self.Document = FakeDocument(elements)

    def GetViewRange(self):
        return FakeViewRange(self.planes)


def make_db():
    db = types.SimpleNamespace()
    db.Level = Level
    db.ElementId = lambda value: value
    db.ElementId.InvalidElementId = -1
    db.BuiltInParameter = types.SimpleNamespace(PLAN_VIEW_RANGE="range")
    db.PlanViewPlane = types.SimpleNamespace(
        TopClipPlane="top",
        CutPlane="cut",
        BottomClipPlane="bottom",
        ViewDepthPlane="depth",
    )
    db.ViewType = types.SimpleNamespace(
        FloorPlan="floor", CeilingPlan="ceiling", EngineeringPlan="structural"
    )
    db.PlanViewRange = types.SimpleNamespace(
        Current=CURRENT, LevelAbove=LEVEL_ABOVE, LevelBelow=LEVEL_BELOW
    )
    return db


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_modules():
    stub = types.ModuleType("pyrevit")
    stub.DB = make_db()
    names = ("pyrevit", "sectionbox_viewrange_rules")
    previous = dict((name, sys.modules.get(name)) for name in names)
    rules = load_module(
        "sectionbox_viewrange_rules", BUNDLE / "sectionbox_viewrange_rules.py"
    )
    sys.modules["pyrevit"] = stub
    sys.modules["sectionbox_viewrange_rules"] = rules
    try:
        viewrange = load_module(
            "sectionbox_viewrange_under_test", BUNDLE / "sectionbox_viewrange.py"
        )
    finally:
        for name, module in previous.items():
            if module is None:
                del sys.modules[name]
            else:
                sys.modules[name] = module
    return rules, viewrange


def floor_planes():
    return {"top": [1, 8.0], "cut": [1, 4.0], "bottom": [1, 0.0], "depth": [1, 0.0]}


def ceiling_planes():
    return {"top": [2, 0.0], "cut": [1, 6.0], "bottom": [1, 6.0], "depth": [2, 3.0]}


class RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules, _ = load_modules()

    def violation(self, ceiling, **elevations):
        return self.rules.find_order_violation(elevations, ceiling)

    def test_plans_looking_down_keep_top_cut_bottom_and_view_depth_in_order(self):
        self.assertIsNone(self.violation(False, top=8, cut=8, bottom=0, depth=0))
        self.assertEqual(
            self.violation(False, top=8, cut=9, bottom=0, depth=0), ("top", "cut")
        )
        self.assertEqual(
            self.violation(False, top=8, cut=4, bottom=0, depth=1), ("bottom", "depth")
        )

    def test_ceiling_plans_put_view_depth_highest_and_ignore_bottom(self):
        self.assertIsNone(self.violation(True, depth=9, top=8, cut=4, bottom=7))
        self.assertEqual(self.violation(True, depth=7, top=8, cut=4), ("depth", "top"))
        self.assertEqual(self.violation(True, depth=9, top=3, cut=4), ("top", "cut"))

    def test_an_unlimited_plane_limits_no_other_plane(self):
        self.assertIsNone(self.violation(False, top=None, cut=40, bottom=0))
        self.assertEqual(
            self.violation(False, cut=4, depth=5, bottom=None), ("cut", "depth")
        )

    @pytest.mark.regression
    def test_aligning_to_a_box_gives_a_valid_order_for_both_directions(self):
        """Align with 3D View wrote the floor order on ceiling plans, which Revit rejects."""
        for ceiling in (False, True):
            aligned = self.rules.aligned_elevations(10.0, 20.0, ceiling)
            self.assertIsNone(self.rules.find_order_violation(aligned, ceiling))
        self.assertEqual(
            self.rules.aligned_elevations(10.0, 20.0, True),
            {"top": 20.0, "cut": 15.0, "depth": 23.0},
        )
        self.assertEqual(
            self.rules.aligned_elevations(10.0, 20.0, False),
            {"top": 20.0, "cut": 15.0, "bottom": 10.0, "depth": 7.0},
        )


class ViewRangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.viewrange = load_modules()

    def test_planes_are_read_with_project_elevations_highest_first(self):
        view = FakeView("floor", floor_planes())
        self.assertEqual(
            [(p["id"], p["elevation"]) for p in self.viewrange.read_planes(view)],
            [("top", 18.0), ("cut", 14.0), ("bottom", 10.0), ("depth", 10.0)],
        )

    def test_current_is_the_associated_level_and_relative_levels_have_no_height(self):
        planes = floor_planes()
        planes["top"] = [LEVEL_ABOVE, 1.0]
        planes["cut"] = [CURRENT, 4.0]
        planes["depth"] = [UNLIMITED, 0.0]
        view = FakeView("floor", planes)
        self.assertEqual(
            self.viewrange.plane_elevations(view), {"cut": 14.0, "bottom": 10.0}
        )
        self.assertEqual(self.viewrange.relative_level_planes(view), ["top"])
        with self.assertRaises(self.viewrange.ViewRangeError) as raised:
            self.viewrange.build_view_range(view, {"top": 19.0})
        self.assertEqual(raised.exception.reason, "unknown_plane")

    def test_only_the_offset_of_the_moved_plane_is_written(self):
        view = FakeView("floor", floor_planes())
        written = self.viewrange.build_view_range(view, {"cut": 12.5})
        self.assertEqual(
            written.planes,
            {"top": [1, 8.0], "cut": [1, 2.5], "bottom": [1, 0.0], "depth": [1, 0.0]},
        )

    @pytest.mark.regression
    def test_a_lowered_ceiling_cut_plane_takes_the_unused_bottom_along(self):
        view = FakeView("ceiling", ceiling_planes())
        written = self.viewrange.build_view_range(view, {"cut": 13.0})
        self.assertEqual(written.GetOffset("cut"), 3.0)
        self.assertEqual(written.GetOffset("bottom"), 3.0)
        self.assertEqual(
            [p["id"] for p in self.viewrange.read_planes(view)],
            ["depth", "top", "cut"],
        )

    def test_planes_out_of_order_are_not_written(self):
        view = FakeView("floor", floor_planes())
        with self.assertRaises(self.viewrange.ViewRangeError) as raised:
            self.viewrange.build_view_range(view, {"bottom": 5.0})
        self.assertEqual(raised.exception.reason, "order")
        self.assertEqual(raised.exception.planes, ("bottom", "depth"))

    def test_only_a_template_that_controls_the_view_range_is_named(self):
        def template(listed, free):
            return types.SimpleNamespace(
                Name="Plans",
                GetTemplateParameterIds=lambda: listed,
                GetNonControlledTemplateParameterIds=lambda: free,
            )

        named = self.viewrange.controlling_template_name
        self.assertIsNone(named(FakeView("floor", floor_planes())))
        cases = (
            (template(["range"], []), "Plans"),
            (template(["range"], ["range"]), None),
            (template([], []), None),
        )
        for case, expected in cases:
            self.assertEqual(
                named(FakeView("floor", floor_planes(), template=case)), expected
            )


if __name__ == "__main__":
    unittest.main()
