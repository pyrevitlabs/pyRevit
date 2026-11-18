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
        self.assertEqual(result["groups"], ["Walls"])
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
        self.assertEqual(result["truncated_status"], "PreviewTruncated")
        self.assertEqual(result["loaded_status"], "PreviewLoaded")

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
