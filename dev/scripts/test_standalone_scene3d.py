"""Host-free tests for the shared scene3d meshing and packing helpers.

Loads ``lib/scene3d/meshing.py`` with a stubbed ``pyrevit`` module so no Revit
is involved, and checks the packed scene JSON round trip, the point budget, the
link transform and non-ASCII text.
"""

import base64
import importlib.util
import json
import pathlib
import struct
import sys
import types
import unittest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

MESHING = (
    pathlib.Path(__file__).resolve().parents[2]
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
        ViewDetailLevel=types.SimpleNamespace(Medium=2),
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


if __name__ == "__main__":
    unittest.main()
