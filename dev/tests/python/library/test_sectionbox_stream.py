"""Host-free tests for which elements the Section Box Navigator preview loads.

Loads ``sectionbox_scene.py`` with the Revit modules stubbed and feeds its
model stream fake elements whose geometry depends on the detail level, the way
Revit gives pipe fittings only center lines below Fine.
"""

import importlib.util
import pathlib
import sys
import types
import unittest

import pytest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

SCENE = (
    pathlib.Path(__file__).resolve().parents[4]
    / "extensions"
    / "pyRevitTools.extension"
    / "pyRevit.tab"
    / "Modify.panel"
    / "3D.pulldown"
    / "Section Box Navigator.pushbutton"
    / "sectionbox_scene.py"
)

COARSE, MEDIUM, FINE = "Coarse", "Medium", "Fine"
SOLID, LINES, NOTHING = "solid", "lines", "nothing"
FITTING = {COARSE: LINES, MEDIUM: LINES, FINE: SOLID}
PIPE = {COARSE: SOLID, MEDIUM: SOLID, FINE: SOLID}
REFERENCE_LINE = {COARSE: LINES, MEDIUM: LINES, FINE: NOTHING}


class Size:
    def __sub__(self, other):
        return self

    def GetLength(self):
        return 1.0


class Builder:
    def __init__(self, shape):
        self.indices = [0, 1, 2] if shape == SOLID else []
        self.edges = [0.0] * 6 if shape == LINES else []
        self.positions = [0.0] * 9 if shape == SOLID else []
        self.point_count = 3


class Element:
    IsValidObject = True

    def __init__(self, element_id, type_id, shapes):
        self.Id = element_id
        self.type_id = type_id
        self.shapes = shapes

    def GetTypeId(self):
        return self.type_id


def load_scene(reads):
    def module(name, **members):
        stub = types.ModuleType(name)
        stub.__dict__.update(members)
        return stub

    def tessellate_element(element, bbox, origin, budget, detail_level, **options):
        reads.append((element.Id, detail_level))
        return Builder(element.shapes[detail_level]), False

    unused = lambda *args, **kwargs: None
    db = types.SimpleNamespace(
        ViewDetailLevel=types.SimpleNamespace(Coarse=COARSE, Medium=MEDIUM, Fine=FINE)
    )
    stubs = {
        "pyrevit": module("pyrevit", DB=db),
        "pyrevit.compat": module(
            "pyrevit.compat", get_elementid_value_func=lambda: int
        ),
        "pyrevit.framework": module("pyrevit.framework", List=list),
        "pyrevit.revit": module("pyrevit.revit", units=None),
        "scene3d": module("scene3d"),
        "scene3d.meshing": module(
            "scene3d.meshing",
            BOX_POINT_COUNT=32,
            FloatArray=list,
            IntArray=list,
            tessellate_element=tessellate_element,
            box_corners=unused,
            element_bbox=unused,
            relative=unused,
            union_bbox=unused,
            vector=unused,
        ),
    }
    for name, members in (
        ("sectionbox_geometry", ("get_box_info", "get_crop_edit_blocker")),
        ("sectionbox_guides", ("drop_repeated_grids", "drop_repeated_levels")),
        ("sectionbox_sources", ("get_scope_boxes", "scope_box_to_bounding_box")),
        ("sectionbox_utils", ("is_2d_view",)),
        (
            "sectionbox_viewrange",
            ("is_ceiling_plan", "plane_elevations", "view_range_payload"),
        ),
        ("sectionbox_viewrange_rules", ("BOTTOM", "CUT", "TOP")),
    ):
        stubs[name] = module(name, **dict((member, unused) for member in members))
    previous = dict((name, sys.modules.get(name)) for name in stubs)
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location("scene_under_test", SCENE)
        scene = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scene)
    finally:
        for name, original in previous.items():
            if original is None:
                del sys.modules[name]
            else:
                sys.modules[name] = original
    return scene


class LoadOnRequestTests(unittest.TestCase):
    def stream(self, level, elements):
        self.reads = []
        scene = load_scene(self.reads)
        stream = scene.ModelStream(
            None,
            None,
            False,
            scene_filter=types.SimpleNamespace(detail_level=level),
        )
        bbox = types.SimpleNamespace(Min=Size(), Max=Size())
        stream._entries = [
            scene._Entry(element, bbox, None, None, 0, group, False, False)
            for group, element in elements
        ]
        return stream

    def drawn(self, stream):
        ids = []
        while True:
            chunk = stream.next_chunk(60)
            if chunk is None:
                return ids
            ids.extend(mesh["id"] for mesh in chunk["meshes"])

    def not_loaded(self, stream):
        return dict((g["group"], g["count"]) for g in stream.dropped_groups())

    def model(self):
        return [
            ("Pipes", Element(1, 100, PIPE)),
            ("Pipe Fittings", Element(2, 200, FITTING)),
            ("Pipe Fittings", Element(3, 200, FITTING)),
            ("Pipe Fittings", Element(4, 200, FITTING)),
            ("Structural Columns", Element(5, 300, REFERENCE_LINE)),
        ]

    @pytest.mark.regression
    def test_fittings_that_are_only_lines_are_listed_instead_of_vanishing(self):
        """Missing without a trace in the preview: discourse.pyrevitlabs.io/t/10788/7."""
        stream = self.stream(MEDIUM, self.model())
        self.assertEqual(self.drawn(stream), [1])
        self.assertEqual(self.not_loaded(stream), {"Pipe Fittings": 3})
        self.assertEqual(stream.truncated, 0)

    def test_fine_is_asked_once_per_type_while_nothing_was_requested(self):
        stream = self.stream(MEDIUM, self.model())
        self.drawn(stream)
        self.assertEqual(
            [element for element, level in self.reads if level == FINE], [2, 5]
        )

    def test_loading_a_category_draws_it_at_fine(self):
        stream = self.stream(MEDIUM, self.model())
        self.drawn(stream)
        del self.reads[:]
        self.assertEqual(stream.load_group(0, "Pipe Fittings"), 3)
        self.assertEqual(self.drawn(stream), [2, 3, 4])
        self.assertEqual(self.reads, [(2, FINE), (3, FINE), (4, FINE)])
        self.assertEqual(self.not_loaded(stream), {})
        self.assertTrue(stream.done)

    def test_lines_that_have_no_shape_at_fine_either_are_not_offered(self):
        stream = self.stream(COARSE, self.model()[-1:])
        self.assertEqual(self.drawn(stream), [])
        self.assertEqual(self.not_loaded(stream), {})

    def test_a_fine_view_draws_the_fittings_directly(self):
        stream = self.stream(FINE, self.model())
        self.assertEqual(self.drawn(stream), [1, 2, 3, 4])
        self.assertEqual(self.not_loaded(stream), {})

    def test_a_fitting_the_limit_left_out_needs_only_one_load(self):
        stream = self.stream(MEDIUM, self.model()[1:2])
        stream._points_limit = 0
        self.drawn(stream)
        self.assertEqual(
            (stream.truncated, self.not_loaded(stream)), (1, {"Pipe Fittings": 1})
        )
        stream.load_group(0, "Pipe Fittings")
        self.assertEqual(self.drawn(stream), [2])
        self.assertEqual(self.not_loaded(stream), {})


if __name__ == "__main__":
    unittest.main()
