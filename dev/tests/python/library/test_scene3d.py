"""Host-free tests for the shared scene3d meshing and packing helpers.

Loads ``lib/scene3d/meshing.py`` with a stubbed ``pyrevit`` module so no Revit
is involved, and checks the packed scene JSON round trip, the point budget, the
link transform, the detail level retries and non-ASCII text.
"""

import base64
import importlib.util
import json
import pathlib
import struct
import sys
import types
import unittest

import pytest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

MESHING = (
    pathlib.Path(__file__).resolve().parents[4]
    / "extensions"
    / "pyRevitTools.extension"
    / "lib"
    / "scene3d"
    / "meshing.py"
)


class Point:
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = x, y, z


class Shift:
    def OfPoint(self, point):
        return Point(point.X + 100, point.Y, point.Z)


def load_meshing():
    stub = types.ModuleType("pyrevit")
    stub.DB = types.SimpleNamespace(
        ViewDetailLevel=types.SimpleNamespace(Coarse=1, Medium=2, Fine=3),
        XYZ=Point,
    )
    previous = sys.modules.get("pyrevit")
    sys.modules["pyrevit"] = stub
    try:
        spec = importlib.util.spec_from_file_location(
            "scene3d_meshing_under_test", MESHING
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            del sys.modules["pyrevit"]
        else:
            sys.modules["pyrevit"] = previous
    return module


def unpack(text, fmt):
    raw = base64.b64decode(text)
    return list(struct.unpack("<{}{}".format(len(raw) // 4, fmt), raw))


class MeshingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meshing = load_meshing()

    def test_packed_arrays_round_trip_through_the_json(self):
        m = self.meshing
        scene = {
            "meshes": [
                {
                    "id": 7,
                    "positions": m.FloatArray([0.0, 1.5, -2.25, 3.0, 4.0, 5.0]),
                    "indices": m.IntArray([0, 1, 0]),
                }
            ],
            "origin": [1, 2, 3],
        }
        back = json.loads(m.scene_to_json(scene))
        mesh = back["meshes"][0]
        self.assertEqual(
            unpack(mesh["positions"], "f"), [0.0, 1.5, -2.25, 3.0, 4.0, 5.0]
        )
        self.assertEqual(unpack(mesh["indices"], "I"), [0, 1, 0])
        self.assertEqual(back["origin"], [1, 2, 3])

    def test_mixed_cyrillic_and_latin1_text_is_kept_as_is(self):
        m = self.meshing
        label = "Уровень «1» Äü"
        text = m.scene_to_json({"label": label, "values": m.FloatArray([1.0])})
        self.assertIn(label, text)
        self.assertEqual(json.loads(text)["label"], label)

    def test_builder_subtracts_the_origin_and_applies_the_transform(self):
        m = self.meshing
        builder = m.MeshBuilder(Point(10, 0, 0), 100, Shift())
        builder.add_polyline([Point(1, 2, 3), Point(4, 5, 6)])
        self.assertEqual(builder.edges, [91, 2, 3, 94, 5, 6])

    def test_budget_counts_edge_endpoints_and_raises(self):
        m = self.meshing
        builder = m.MeshBuilder(Point(0, 0, 0), 3)
        builder.add_polyline([Point(0, 0, 0), Point(1, 0, 0)])
        with self.assertRaises(m.BudgetExceeded):
            builder.add_polyline([Point(1, 0, 0), Point(2, 0, 0)])

    def test_box_corner_order_matches_the_edge_table(self):
        m = self.meshing
        corners = m.box_corners(Point(0, 0, 0), Point(1, 2, 3))
        self.assertEqual(len(corners), 8)
        self.assertEqual((corners[1].X, corners[2].Y, corners[4].Z), (1, 2, 3))
        for a, b in m.BOX_EDGES:
            differing = sum(
                (
                    corners[a].X != corners[b].X,
                    corners[a].Y != corners[b].Y,
                    corners[a].Z != corners[b].Z,
                )
            )
            self.assertEqual(differing, 1)

    def tessellate_exhausted(self, geometry_walk, box_when_empty):
        m = self.meshing
        m.element_geometry = lambda element, detail_level: []
        m.walk_geometry = geometry_walk
        bbox = types.SimpleNamespace(Min=Point(0, 0, 0), Max=Point(1, 1, 1))
        return m.tessellate_element(
            object(), bbox, Point(0, 0, 0), 0, box_when_empty=box_when_empty
        )

    def test_exhausted_budget_keeps_geometryless_elements_out_when_asked(self):
        builder, approx = self.tessellate_exhausted(
            lambda geometry, builder, edges=True: None, box_when_empty=False
        )
        self.assertEqual((builder.indices, approx), ([], False))

    def test_exhausted_budget_boxes_elements_that_have_geometry(self):
        def one_segment(geometry, builder, edges=True):
            builder.add_polyline([Point(0, 0, 0), Point(1, 0, 0)])

        builder, approx = self.tessellate_exhausted(one_segment, box_when_empty=False)
        self.assertTrue(approx)
        self.assertEqual(len(builder.indices), 36)

    def test_exhausted_budget_boxes_geometryless_elements_by_default(self):
        builder, approx = self.tessellate_exhausted(
            lambda geometry, builder, edges=True: None, box_when_empty=True
        )
        self.assertTrue(approx)
        self.assertEqual(len(builder.indices), 36)

    def tessellate_over_budget(self, coarse_retry):
        m = self.meshing
        detail_levels = []
        original = m.element_geometry, m.walk_geometry

        def geometry(element, detail_level):
            detail_levels.append(detail_level)
            return []

        def walk(geometry_, builder, edges=True, level_of_detail=None):
            count = 40 if level_of_detail is None else self.coarse_points
            builder.add_polyline([Point(i, 0, 0) for i in range(count)])

        m.element_geometry, m.walk_geometry = geometry, walk
        try:
            bbox = types.SimpleNamespace(Min=Point(0, 0, 0), Max=Point(1, 1, 1))
            result = m.tessellate_element(
                object(), bbox, Point(0, 0, 0), 60, coarse_retry=coarse_retry
            )
        finally:
            m.element_geometry, m.walk_geometry = original
        return result, detail_levels

    def test_coarse_retry_keeps_the_shape_of_an_element_over_budget(self):
        self.coarse_points = 10
        (builder, approx), detail_levels = self.tessellate_over_budget(True)
        self.assertFalse(approx)
        self.assertEqual(len(builder.edges) // 3, 18)
        self.assertEqual(detail_levels, [2, 1])

    def test_coarse_retry_falls_back_to_the_box_when_still_over_budget(self):
        self.coarse_points = 40
        (builder, approx), detail_levels = self.tessellate_over_budget(True)
        self.assertTrue(approx)
        self.assertEqual(len(builder.indices), 36)
        self.assertEqual(detail_levels, [2, 1])

    def tessellate_fitting(
        self, fine_retry, fine_vertices=3, budget=200, medium_triangles=False
    ):
        """Tessellate an element that, like a pipe fitting, has triangles only at Fine."""
        m = self.meshing
        calls = []
        original = m.element_geometry, m.walk_geometry

        def walk(detail_level, builder, edges=True, level_of_detail=None):
            calls.append((detail_level, level_of_detail))
            has_triangles = detail_level == 3 or medium_triangles
            if not has_triangles:
                builder.add_polyline([Point(0, 0, 0), Point(1, 0, 0)])
                return
            if not fine_vertices:
                return
            builder._reserve(fine_vertices)
            builder.positions.extend([0.0] * (3 * fine_vertices))
            builder.indices.extend([0, 1, 2])

        m.element_geometry = lambda element, detail_level: detail_level
        m.walk_geometry = walk
        try:
            bbox = types.SimpleNamespace(Min=Point(0, 0, 0), Max=Point(1, 1, 1))
            builder, approx = m.tessellate_element(
                object(),
                bbox,
                Point(0, 0, 0),
                budget,
                edges=False,
                box_when_empty=False,
                coarse_retry=True,
                fine_retry=fine_retry,
            )
        finally:
            m.element_geometry, m.walk_geometry = original
        return builder, approx, calls

    @pytest.mark.regression
    def test_fine_retry_gives_a_pipe_fitting_that_draws_as_lines_a_shape(self):
        """Fittings were missing from the preview: discourse.pyrevitlabs.io/t/10788/7."""
        builder, approx, calls = self.tessellate_fitting(fine_retry=True)
        self.assertEqual((builder.indices, approx), ([0, 1, 2], False))
        self.assertEqual(
            calls, [(2, None), (3, self.meshing.FINE_RETRY_LEVEL_OF_DETAIL)]
        )

    def test_without_fine_retry_an_element_of_lines_has_no_triangles(self):
        builder, approx, calls = self.tessellate_fitting(fine_retry=False)
        self.assertEqual((builder.indices, approx), ([], False))
        self.assertEqual(calls, [(2, None)])

    def test_fine_retry_is_skipped_for_an_element_with_triangles(self):
        _, _, calls = self.tessellate_fitting(fine_retry=True, medium_triangles=True)
        self.assertEqual(calls, [(2, None)])

    def test_fine_retry_without_triangles_keeps_the_first_result(self):
        builder, approx, _ = self.tessellate_fitting(fine_retry=True, fine_vertices=0)
        self.assertEqual((builder.indices, len(builder.edges), approx), ([], 6, False))

    def test_a_fine_shape_over_budget_is_drawn_as_its_box(self):
        builder, approx, _ = self.tessellate_fitting(
            fine_retry=True, fine_vertices=100, budget=60
        )
        self.assertTrue(approx)
        self.assertEqual(len(builder.indices), 36)

    def tessellate_curves_only_at_coarse(self, edges):
        m = self.meshing
        original = m.element_geometry, m.walk_geometry

        def walk(geometry_, builder, edges_=True, level_of_detail=None):
            if level_of_detail is None:
                builder.add_polyline([Point(i, 0, 0) for i in range(40)])
            else:
                builder.add_polyline([Point(0, 0, 0), Point(1, 0, 0)])

        m.element_geometry, m.walk_geometry = (lambda element, detail: []), walk
        try:
            bbox = types.SimpleNamespace(Min=Point(0, 0, 0), Max=Point(1, 1, 1))
            return m.tessellate_element(
                object(), bbox, Point(0, 0, 0), 60, edges=edges, coarse_retry=True
            )
        finally:
            m.element_geometry, m.walk_geometry = original

    def test_coarse_retry_without_triangles_keeps_the_box_when_edges_are_not_wanted(
        self,
    ):
        builder, approx = self.tessellate_curves_only_at_coarse(edges=False)
        self.assertTrue(approx)
        self.assertEqual(len(builder.indices), 36)

    def test_coarse_retry_with_only_segments_is_kept_when_edges_are_wanted(self):
        builder, approx = self.tessellate_curves_only_at_coarse(edges=True)
        self.assertFalse(approx)
        self.assertEqual(len(builder.edges) // 3, 2)

    def test_without_coarse_retry_an_element_over_budget_becomes_a_box(self):
        self.coarse_points = 10
        (builder, approx), detail_levels = self.tessellate_over_budget(False)
        self.assertTrue(approx)
        self.assertEqual(len(builder.indices), 36)
        self.assertEqual(detail_levels, [2])


if __name__ == "__main__":
    unittest.main()
