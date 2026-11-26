"""Local-only WebGL smoke test for the Section Box Navigator 3D preview page.

Draws the guides and the hovered element in a real WebGL2 context of a headless
Edge or Chrome. Hosted runners cannot start WebGL2 reliably, and a skipped test
fails the host-free selection, so this runs locally only.
"""

import subprocess
import unittest

from test_sectionbox_preview_page import find_browser, run_scenario

TEST_ENVIRONMENT = "Revit"
TEST_LEVEL = "Integration"


class SectionBoxPreviewWebGLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = find_browser()
        if cls.browser is None:
            raise unittest.SkipTest("no Edge or Chrome found for the WebGL test")

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
