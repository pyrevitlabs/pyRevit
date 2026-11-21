"""Host-free tests for the Section Box Navigator preview's Revit-free helpers.

Loads the bundle's ``sectionbox_guides.py`` and ``sectionbox_settings.py``, which
import nothing from Revit. The first decides which linked levels and grids count
as repeating a listed one, the second validates the remembered display settings.
"""

import importlib.util
import pathlib
import unittest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

GUIDES = (
    pathlib.Path(__file__).resolve().parents[2]
    / "extensions"
    / "pyRevitTools.extension"
    / "pyRevit.tab"
    / "Modify.panel"
    / "3D.pulldown"
    / "Section Box Navigator.pushbutton"
    / "sectionbox_guides.py"
)


SETTINGS = GUIDES.with_name("sectionbox_settings.py")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_guides():
    return load_module("sectionbox_guides_under_test", GUIDES)


def level(name, z, link=False):
    return {"name": name, "z": z, "elevation": z + 100, "link": link}


def grid(name, x1, y1, x2, y2, link=False):
    return {"name": name, "link": link, "segs": [[x1, y1, x2, y2]]}


class RepeatedLevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guides = load_guides()

    def names(self, entries):
        return [entry["name"] for entry in self.guides.drop_repeated_levels(entries)]

    def test_a_linked_level_at_a_host_elevation_is_left_out_whatever_its_name(self):
        entries = [level("L1", 0), level("Floor 1 TOS", 0.004, True), level("L2", 12)]
        self.assertEqual(self.names(entries), ["L1", "L2"])

    def test_the_host_level_wins_even_when_the_linked_one_comes_first(self):
        entries = [level("Link L1", 0, True), level("Host L1", 0)]
        self.assertEqual(self.names(entries), ["Host L1"])

    def test_linked_levels_at_other_elevations_stay_and_repeats_keep_the_first(self):
        entries = [
            level("L1", 0),
            level("A", 6, True),
            level("B", 6.005, True),
            level("C", 9, True),
        ]
        self.assertEqual(self.names(entries), ["L1", "A", "C"])

    def test_elevations_further_apart_than_the_tolerance_are_different_levels(self):
        entries = [level("L1", 0), level("L1 offset", 0.05, True)]
        self.assertEqual(self.names(entries), ["L1", "L1 offset"])

    def test_host_levels_are_never_merged(self):
        entries = [level("A", 0), level("B", 0)]
        self.assertEqual(self.names(entries), ["A", "B"])


class RepeatedGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guides = load_guides()

    def names(self, entries):
        return [entry["name"] for entry in self.guides.drop_repeated_grids(entries)]

    def test_a_linked_grid_on_the_line_of_a_host_grid_is_left_out(self):
        entries = [
            grid("1", 0, -50, 0, 50),
            grid("Axis 1", 0.01, -80, 0.01, 20, link=True),
        ]
        self.assertEqual(self.names(entries), ["1"])

    def test_the_same_name_tolerates_a_larger_offset_than_different_names(self):
        host = grid("1", 0, -50, 0, 50)
        self.assertEqual(self.names([host, grid("1", 0.5, -50, 0.5, 50, True)]), ["1"])
        self.assertEqual(
            self.names([host, grid("X", 0.5, -50, 0.5, 50, True)]), ["1", "X"]
        )

    def test_grids_that_are_not_parallel_or_far_apart_stay(self):
        host = grid("A", -50, 0, 50, 0)
        entries = [
            host,
            grid("A", -50, 0, 50, 5, True),
            grid("B", -50, 12, 50, 12, True),
        ]
        self.assertEqual(self.names(entries), ["A", "A", "B"])

    def test_a_long_grid_drifting_away_at_a_small_angle_is_not_a_repeat(self):
        host = grid("A", 0, 0, 1000, 0)
        drifting = grid("A", 0, 0, 1000, 7, True)
        shifted_end = grid("B", 0, 0, 1000, 0.02, True)
        self.assertEqual(self.names([host, drifting]), ["A", "A"])
        self.assertEqual(self.names([host, shifted_end]), ["A"])

    def test_endpoint_order_does_not_change_whether_grids_repeat(self):
        link = grid("A", 0, 0, 1000, 0, True)
        forward = grid("B", 0, 0, 1000, 8)
        reversed_ends = grid("B", 1000, 8, 0, 0)
        self.assertEqual(self.names([forward, link]), ["B", "A"])
        self.assertEqual(self.names([reversed_ends, link]), ["B", "A"])

    def test_a_short_linked_grid_along_a_long_host_grid_is_a_repeat(self):
        host = grid("A", 0, 0, 1000, 0)
        self.assertEqual(
            self.names([host, grid("A", 200, 0.01, 300, 0.01, True)]), ["A"]
        )

    def test_curved_and_empty_grids_are_never_compared(self):
        arc = {"name": "R", "link": True, "segs": [[0, 0, 1, 1], [1, 1, 2, 3]]}
        point = grid("P", 3, 3, 3, 3, True)
        host = grid("R", 0, 0, 1, 1)
        self.assertEqual(self.names([host, arc, point]), ["R", "R", "P"])

    def test_linked_repeats_keep_the_first_and_the_original_order(self):
        entries = [
            grid("L1", 0, 0, 0, 10, True),
            grid("H", 20, 0, 20, 10),
            grid("L2", 0.01, 0, 0.01, 10, True),
        ]
        self.assertEqual(self.names(entries), ["L1", "H"])


class RememberedSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_module("sectionbox_settings_under_test", SETTINGS)

    def test_valid_entries_survive_a_round_trip(self):
        data = {"model": False, "snap": True, "cut": "hide", "ghost": 0.3}
        text = self.settings.dump_settings(data)
        self.assertEqual(self.settings.parse_settings(text), data)

    def test_unknown_keys_and_wrong_types_are_dropped(self):
        data = {
            "model": "yes",
            "levels": 1,
            "junk": True,
            "cut": "sideways",
            "snap": False,
        }
        self.assertEqual(self.settings.clean_settings(data), {"snap": False})

    def test_ghost_strength_is_clamped_to_the_slider_range(self):
        clean = self.settings.clean_settings
        self.assertEqual(clean({"ghost": 5}), {"ghost": 0.6})
        self.assertEqual(clean({"ghost": -1}), {"ghost": 0.02})
        self.assertEqual(clean({"ghost": float("nan")}), {})
        self.assertEqual(clean({"ghost": True}), {})

    def test_side_panel_width_is_a_clamped_number(self):
        clean = self.settings.clean_settings
        self.assertEqual(clean({"sideWidth": 320}), {"sideWidth": 320.0})
        self.assertEqual(clean({"sideWidth": 5}), {"sideWidth": 160.0})
        self.assertEqual(clean({"sideWidth": 99999}), {"sideWidth": 1200.0})
        self.assertEqual(clean({"sideWidth": "wide"}), {})
        self.assertEqual(clean({"sideWidth": None}), {})

    def test_values_the_config_reader_returns_as_non_text_are_ignored(self):
        for stored in (True, False, 5, {"model": False}, ["x"]):
            self.assertEqual(self.settings.parse_settings(stored), {})

    def test_missing_or_broken_config_text_gives_no_settings(self):
        for text in ("", None, "{broken", "[1, 2]", "42"):
            self.assertEqual(self.settings.parse_settings(text), {})
        self.assertEqual(self.settings.clean_settings(None), {})


if __name__ == "__main__":
    unittest.main()
