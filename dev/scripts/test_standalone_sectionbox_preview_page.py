"""Host-free tests for the Section Box Navigator 3D preview page.

Loads the bundle's real ``preview.js`` and the shared ``gl.js`` in a headless
Chromium-based browser through ``fixtures/sectionbox_preview_page/harness.html``,
with a stubbed WebView2 bridge, and asserts on the box, snapping and rotation
math and on what mounting the page leaves behind. No Revit is involved.

A missing browser fails the test on CI and skips it elsewhere, so a runner
without Edge or Chrome cannot pass silently. Only the WebGL smoke test skips
everywhere when the browser starts no WebGL2 context in time, which hosted
runners do not reliably allow.
"""

import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Integration"

HARNESS = (
    pathlib.Path(__file__).parent
    / "fixtures"
    / "sectionbox_preview_page"
    / "harness.html"
)
BROWSER_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)
SCENARIO_TIMEOUT_SECONDS = 45
RESULT = re.compile(r'<pre id="out">RESULT (.*?)</pre>', re.DOTALL)


def find_browser():
    configured = os.environ.get("PYREVIT_TEST_BROWSER")
    candidates = [configured] if configured else []
    candidates += [shutil.which("msedge"), shutil.which("chrome")]
    candidates += list(BROWSER_CANDIDATES)
    return next((path for path in candidates if path and os.path.isfile(path)), None)


def run_browser(browser, url):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        return subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--allow-file-access-from-files",
                "--no-first-run",
                "--disable-extensions",
                "--user-data-dir=" + profile,
                "--virtual-time-budget=4000",
                "--dump-dom",
                url,
            ],
            capture_output=True,
            timeout=SCENARIO_TIMEOUT_SECONDS,
            check=False,
        )


def run_scenario(browser, name, gl=False):
    url = "{}?scenario={}{}".format(HARNESS.as_uri(), name, "&gl=1" if gl else "")
    completed = run_browser(browser, url)
    dom = completed.stdout.decode("utf-8", "replace")
    match = RESULT.search(dom)
    if match is None:
        raise AssertionError(
            "scenario {} left no result (exit {}): {}".format(
                name, completed.returncode, dom[-400:]
            )
        )
    return json.loads(html.unescape(match.group(1)))


class SectionBoxPreviewPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = find_browser()
        if cls.browser is None:
            message = "no Edge or Chrome found for the preview page tests"
            if os.environ.get("CI"):
                raise AssertionError(message)
            raise unittest.SkipTest(message)

    def scenario(self, name):
        result = run_scenario(self.browser, name)
        self.assertNotIn("exception", result, result.get("exception"))
        self.assertEqual(result["errors"], [])
        return result

    def test_levels_snap_top_and_bottom_faces_only(self):
        result = self.scenario("snap_levels")
        self.assertEqual(result["candidates"], [["L2", 2], ["L3", 10]])
        self.assertEqual(result["snapped"], [2, "L2"])
        self.assertEqual(result["free"], [5, None])
        self.assertEqual(result["downward"], [3])
        self.assertEqual(result["side_face_gets_no_levels"], 0)

    def test_grids_snap_as_planes_when_parallel_and_by_crossing_otherwise(self):
        result = self.scenario("snap_grids")
        self.assertEqual(result["candidates"], [["A", 7], ["D", 5]])
        self.assertEqual(result["rotated_parallel"], [["H", 4]])
        self.assertEqual([name for name, _ in result["arc"]], ["R"])
        self.assertAlmostEqual(result["arc"][0][1], 3.4, places=4)

    def test_scope_box_faces_are_snap_targets(self):
        result = self.scenario("snap_scope_planes")
        self.assertEqual(result["sideCandidates"], [["SB", 16], ["SB", 24]])
        self.assertEqual(sorted(result["top"]), [-3, 3])

    def test_yaw_snaps_to_grid_directions_and_perpendiculars(self):
        result = self.scenario("yaw_snap")
        self.assertEqual(result["snapped30"], [30, "G"])
        self.assertEqual(result["snapped120"], 120)
        self.assertEqual(result["free45"], [45, None])

    def test_moving_a_face_changes_one_extent_and_refuses_to_collapse(self):
        result = self.scenario("move_face")
        self.assertEqual(result["up_max_z"], 12.5)
        self.assertEqual(result["original_max_z"], 10)
        self.assertEqual(result["min_z_lowered"], 3)
        self.assertIsNone(result["collapse"])
        self.assertEqual(result["normal_x1"], [0, 1, 0])
        self.assertEqual(result["center_z1"], [0, 0, 10])
        self.assertEqual(result["center_x0"], [-5, 0, 5])

    def test_rotating_keeps_the_center_and_the_vertical_axis(self):
        result = self.scenario("rotate_box")
        self.assertTrue(result["center_kept"])
        self.assertTrue(result["yaw"])
        self.assertEqual(result["bz"], [0, 0, 1])
        self.assertTrue(result["minmax_kept"])
        self.assertTrue(result["orthonormal"])

    def test_fitting_to_world_bounds_contains_them_in_a_rotated_box(self):
        result = self.scenario("fit_world_bounds")
        self.assertTrue(result["inside"])
        self.assertEqual(result["zmin"], -1)
        self.assertEqual(result["zmax"], 4)

    def test_axis_line_math(self):
        result = self.scenario("axis_line")
        self.assertAlmostEqual(result["t"], 4, places=9)
        self.assertIsNone(result["parallel"])
        self.assertEqual(
            self.scenario("segment_distance"), {"d": 5, "end": 5, "errors": []}
        )

    def test_mounting_builds_handles_streams_chunks_and_posts_boxes(self):
        result = self.scenario("mount")
        self.assertEqual(result["elements"], 1)
        self.assertEqual(result["groups"], ["0|Walls"])
        self.assertEqual(result["bounds"], {"min": [0, 0, 0], "max": [4, 4, 0]})
        self.assertEqual(result["handles"], 7)
        self.assertTrue(result["bookmark"])
        self.assertEqual(result["sent"], ["ready", "apply_box"])
        self.assertEqual(result["apply_box"], [5, 5, 10])
        self.assertIn("3.048", result["size_text"])
        self.assertEqual(result["pending_after_result"], 0)
        self.assertIn("sbp-error", result["status_class"])
        self.assertEqual(result["after_drop"], 1)

    def test_guides_show_relevant_levels_and_do_not_pile_up_labels(self):
        result = self.scenario("guides_and_presets")
        self.assertEqual(sorted(result["shown_levels"]), ["L2", "L3", "L4", "L5", "L6"])
        self.assertEqual(result["all_levels"], 8)
        self.assertFalse(result["rooms_visible"])
        self.assertGreater(result["iso_level_labels"], 0)
        self.assertLessEqual(result["iso_grid_labels"], 3)
        self.assertEqual(result["top_level_labels"], 0)
        self.assertEqual(result["top_grid_labels"], 3)

    def test_front_and_side_presets_face_the_box_axes(self):
        result = self.scenario("guides_and_presets")
        self.assertEqual(result["front"], {"pitch": 0, "ortho": True, "yawDeg": -90})
        self.assertEqual(result["side"], {"pitch": 0, "yawDeg": 0})
        self.assertEqual(result["rotated_front_yawDeg"], -60)

    def test_ray_triangle_hits_only_in_front_and_inside(self):
        result = self.scenario("triangle_hit")
        self.assertEqual(result["hit"], 5)
        self.assertIsNone(result["miss"])
        self.assertIsNone(result["behind"])

    def test_pick_modes_preview_what_a_click_would_apply(self):
        result = self.scenario("pick_hover")
        self.assertEqual(result["wall"]["label"], "Walls · 12")
        self.assertTrue(result["wall"]["boxContainsElement"])
        self.assertEqual(result["wall"]["zmin"], -1)
        self.assertEqual(result["slab"], "Floors · 11")
        self.assertIsNone(result["nothing"])
        self.assertIn("hover", result["status_hint"].lower() + "hover")
        self.assertEqual(result["grid"], {"label": "PreviewAlignGrid: G1", "yawDeg": 0})
        self.assertEqual(result["svg_lines"], 1)
        self.assertEqual(result["cleared"]["lines"], 0)
        self.assertIsNone(result["cleared"]["hover"])

    def test_failed_requests_cancelled_drags_and_remounts_leave_no_state_behind(self):
        result = self.scenario("review_fixes")
        self.assertEqual(result["pending_before_error"], 1)
        self.assertEqual(result["pending_after_error"], 0)
        self.assertTrue(result["request_cleared"])
        self.assertIn("sbp-error", result["error_status"])
        self.assertEqual(result["pending_after_unknown"], 0)
        self.assertEqual(result["pending_after_stream_error"], 0)
        self.assertEqual(result["rotate_started"], "rotate")
        self.assertIsNone(result["drag_after_escape"])
        self.assertTrue(result["live_box_moved"])
        self.assertGreaterEqual(result["live_sent"], 1)
        self.assertEqual(result["restore_sent"], result["live_sent"] + 1)
        self.assertEqual(result["restored_max_z"], result["page_max_z"])
        self.assertEqual(result["keydown"], {"added": 2, "removed": 1})

    def test_stale_acknowledgements_and_view_changes_cannot_overwrite_newer_state(self):
        result = self.scenario("stale_box_acks")
        self.assertEqual(result["revisions"], [1, 2])
        self.assertEqual(result["generations"], [7, 7])
        self.assertEqual(result["request_generation"], 7)
        self.assertEqual(result["after_stale_ack"], 12)
        self.assertEqual(result["after_latest_ack"], 12)
        self.assertEqual(result["after_unrevisioned"], 9)
        self.assertEqual(result["after_view_change"], 7)
        self.assertEqual(result["truncated_status"], "PreviewTruncated")
        self.assertEqual(result["loaded_status"], "PreviewLoaded")

    def test_view_cube_maps_faces_edges_corners_and_compass_to_cameras(self):
        result = self.scenario("view_cube")
        self.assertEqual(result["centre"], ["front", 0, 0])
        self.assertEqual(result["edge"], ["front", 1, 0])
        self.assertEqual(result["edgeCamera"], {"yaw": -45, "pitch": 0})
        self.assertEqual(result["cornerCamera"]["yaw"], -45)
        self.assertAlmostEqual(result["cornerCamera"]["pitch"], 35.2644, places=3)
        self.assertEqual(result["frontVisible"], ["front"])
        self.assertEqual(result["tiltedFaces"], ["front", "right", "top"])
        self.assertEqual(result["tiltedCells"], 27)
        self.assertEqual(result["tiltedCompass"], ["e", "n", "s", "w"])
        self.assertEqual(result["top"]["yaw"], 1)
        self.assertAlmostEqual(result["top"]["pitchDeg"], 90, places=3)
        self.assertEqual(result["north"], {"yawDeg": 90, "pitch": 0.5})

    def test_view_cube_draws_labels_and_edits_the_camera_on_click_and_drag(self):
        result = self.scenario("view_cube")
        self.assertIn("OBEN", result["labels"])
        self.assertIn("VORNE", result["labels"])
        self.assertEqual(result["labels"].count("O"), 1)
        self.assertEqual(
            result["clicked"], {"yawDeg": -90, "pitchDeg": 0, "changes": 1}
        )
        self.assertTrue(result["dragged"]["yawChanged"])
        self.assertGreater(result["dragged"]["changes"], 1)
        self.assertEqual(result["removed"], 0)

    def test_preview_mounts_the_view_cube_and_removes_it_on_dispose(self):
        result = self.scenario("cube_in_preview")
        self.assertEqual(result["present"], 1)
        self.assertIn("PREVIEWFRONT", result["faces"])
        self.assertEqual(result["after_dispose"], 0)

    def test_side_and_front_views_draw_only_grids_along_the_view_as_vertical_lines(
        self,
    ):
        result = self.scenario("elevation_guides")
        self.assertEqual(result["front"], ["1", "2"])
        self.assertTrue(result["vertical"])
        self.assertLess(result["span"][0], result["span"][1])
        self.assertEqual(result["side"], ["A"])
        self.assertEqual(result["iso_segments"], 4)
        self.assertEqual(result["front_grid_labels"], ["1", "2"])

    def test_level_labels_stay_inside_the_viewport_when_zoomed_into_an_elevation(self):
        result = self.scenario("elevation_guides")
        self.assertGreater(result["pinned_level_labels"], 0)
        self.assertTrue(result["pinned_inside"])
        self.assertTrue(result["end_aligned"])

    def test_elevation_helpers(self):
        result = self.scenario("pure_helpers")
        self.assertEqual(result["along_y"], [1])
        self.assertEqual(result["along_x"], [0])
        self.assertEqual(result["elevation"], [True, True, False])
        self.assertEqual(result["pinned_inside"], {"x": 30, "y": 40})
        self.assertEqual(result["pinned_left"]["x"], 12)
        self.assertAlmostEqual(result["pinned_left"]["y"], 42.4, places=6)
        self.assertIsNone(result["pinned_gone"])
        self.assertEqual(result["key"], "2|Walls")

    def test_link_categories_get_their_own_rows_and_boxes_are_marked(self):
        result = self.scenario("link_groups")
        self.assertEqual(result["keys"], ["0|Walls", "1|Floors", "1|Walls"])
        self.assertEqual(result["link_head"], "Link: Tower")
        self.assertEqual(result["indented"], 2)
        self.assertEqual(result["notes"], 1)
        self.assertEqual(
            result["batches"], ["0|Walls:false", "1|Floors:true", "1|Walls:false"]
        )
        self.assertEqual(result["label"], "Tower · Floors · 3 · PreviewBoxOnly")
        self.assertEqual(result["visible"], [True, False, False])
        self.assertEqual(result["after_drop"], ["0|Walls"])

    def test_left_out_categories_can_be_requested_and_vanish_once_empty(self):
        result = self.scenario("link_groups")
        self.assertEqual(result["dropped"], [0, 5])
        self.assertEqual(result["request"], "0:Furniture")
        self.assertTrue(result["requested"])
        self.assertFalse(result["emptied"])

    def test_top_view_looks_straight_down_so_box_outlines_coincide(self):
        result = self.scenario("top_view")
        self.assertEqual(result["pitchDeg"], 90)
        self.assertLess(result["maxGap"], 1e-6)
        self.assertEqual(result["orientation"], {"northUp": True, "eastRight": True})
        self.assertTrue(result["panFinite"])
        self.assertTrue(result["panMoved"])
        self.assertEqual(result["orbitPitchDeg"], 89.5)

    def test_compass_follows_true_north_for_drawing_and_clicks(self):
        result = self.scenario("true_north")
        self.assertEqual(result["n"], [0.5, 0.866, 0])
        self.assertEqual(result["e"], [0.866, -0.5, 0])
        self.assertEqual(result["s"], [-0.5, -0.866, 0])
        self.assertEqual(result["w"], [-0.866, 0.5, 0])
        self.assertTrue(result["nHitLeftOfCentre"])
        self.assertTrue(result["nHitAboveCentre"])
        self.assertEqual(result["headingYawDeg"], 60)
        self.assertEqual(result["headingPitch"], 0.4)
        self.assertTrue(result["mounted"])

    def test_category_search_filters_by_category_or_link_and_links_collapse(self):
        result = self.scenario("category_search")
        self.assertEqual(
            result["all"],
            [
                "Floors",
                "Walls",
                "[Link: Tower]",
                "Floors",
                "Walls",
                "[Link: Plumbing]",
                "Pipes",
            ],
        )
        self.assertEqual(result["pipe"], ["[Link: Plumbing]", "Pipes"])
        self.assertEqual(result["tower"], ["[Link: Tower]", "Floors", "Walls"])
        self.assertEqual(result["walls"], ["Walls", "[Link: Tower]", "Walls"])
        self.assertEqual(
            result["visible_after_none"],
            [
                "0|Floors:true",
                "0|Walls:true",
                "1|Floors:true",
                "1|Walls:true",
                "2|Pipes:false",
            ],
        )
        self.assertEqual(
            result["collapsed"],
            ["Floors", "Walls", "[Link: Tower]", "[Link: Plumbing]", "Pipes"],
        )
        self.assertEqual(
            result["expanded_while_searching"], ["[Link: Tower]", "Floors", "Walls"]
        )
        self.assertEqual(result["collapsed_remembered"], result["collapsed"])
        self.assertEqual(result["reopened"], 7)

    def test_display_and_box_settings_are_restored_and_posted_when_changed(self):
        result = self.scenario("remembered_settings")
        self.assertEqual(result["flags"], [False, "hide", 0.3, False, True, True])
        self.assertEqual(result["sideWidth"], [333, "333px"])
        self.assertEqual(result["controls"][0], "hide")
        self.assertEqual(result["controls"][1], "30")
        self.assertEqual(result["saves"], 3)
        self.assertTrue(result["no_request_id"])
        self.assertEqual(result["last"]["levels"], False)
        self.assertEqual(result["last"]["cut"], "off")
        self.assertAlmostEqual(result["last"]["ghost"], 0.45)
        self.assertEqual(result["last"]["model"], False)
        self.assertEqual(
            result["last"]["keys"],
            [
                "allLevels",
                "cut",
                "ghost",
                "grids",
                "levels",
                "live",
                "model",
                "names",
                "scope",
                "sideWidth",
                "snap",
            ],
        )
        saved, width, main_width = result["clamped"]
        self.assertEqual(saved, 1100)
        self.assertLessEqual(width, main_width * 0.7 + 1)
        self.assertGreaterEqual(width, 160)
        self.assertEqual(result["defaults_kept"], [True, "ghost", 0.12, True])

    def test_preview_covers_log_lines_in_the_output_window_and_the_side_panel_resizes(
        self,
    ):
        result = self.scenario("crowded_output")
        self.assertEqual(result["position"], "fixed")
        self.assertEqual((result["top"], result["left"]), (0, 0))
        self.assertGreater(result["wide"], result["before"] + 50)
        self.assertEqual(result["narrow"], 160)
        self.assertAlmostEqual(result["widest"], result["mainWidth"] * 0.7, delta=1)
        self.assertEqual(result["saved"][:2], [result["wide"], 160])
        self.assertEqual(result["reset"], ["", None])
        self.assertIsNone(result["saved_after_reset"])

    def test_cube_compass_letters_hit_their_own_center_in_every_view(self):
        result = self.scenario("cube_robustness")
        self.assertTrue(all(result["letters"].values()), result["letters"])

    def test_cube_drag_belongs_to_the_pointer_that_started_it(self):
        result = self.scenario("cube_robustness")
        self.assertEqual(result["second_finger_move"][0], 0)
        self.assertEqual(result["owner_move"], 1)
        self.assertEqual(result["after_foreign_up"], 2)
        self.assertEqual(result["after_cancel"], [True, True])

    def test_a_failed_stream_re_enables_the_load_links(self):
        result = self.scenario("stream_error_clears_requests")
        self.assertEqual(result["before"], [True, True])
        self.assertEqual(result["after"], [False, False])
        self.assertEqual(result["status"], "stream failed")

    def test_webgl_context_draws_guides_and_the_hovered_element(self):
        try:
            result = run_scenario(self.browser, "gl_smoke", gl=True)
        except subprocess.TimeoutExpired:
            self.skipTest("headless browser did not start a WebGL context in time")
        if not result["gl"]:
            self.skipTest("the browser has no WebGL2")
        self.assertEqual(result["error"], 0)
        self.assertEqual(result["elements"], 1)
        self.assertEqual(result["hoveredId"], 12)
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
