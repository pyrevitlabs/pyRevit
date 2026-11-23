"""Host-free regression tests for the Diagnose Invisibility report page.

Loads the bundle's real ``report.js`` and ``viewer3d.js`` in a headless
Chromium-based browser through ``fixtures/diagnose_invisibility_page/harness.html``,
with a stubbed WebView2 bridge, and asserts on what each scenario leaves in the
page. No Revit is involved. Regression reference: pull request 4085, the
reveal-hidden inspector (stale inspect answers, selection pruning, the level
filter and row multi-selection).

A missing browser fails the test on CI and skips it elsewhere, so a runner
without Edge or Chrome cannot pass silently.
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
    / "diagnose_invisibility_page"
    / "harness.html"
)
BROWSER_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)
RESULT = re.compile(r'<pre id="out">RESULT (.*?)</pre>', re.DOTALL)


def find_browser():
    configured = os.environ.get("PYREVIT_TEST_BROWSER")
    candidates = [configured] if configured else []
    candidates += [shutil.which("msedge"), shutil.which("chrome")]
    candidates += list(BROWSER_CANDIDATES)
    return next((path for path in candidates if path and os.path.isfile(path)), None)


def run_scenario(browser, name):
    url = "{}?scenario={}".format(HARNESS.as_uri(), name)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        completed = subprocess.run(
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
            timeout=120,
            check=False,
        )
    dom = completed.stdout.decode("utf-8", "replace")
    match = RESULT.search(dom)
    if match is None:
        raise AssertionError(
            "scenario {} left no result (exit {}): {}".format(
                name, completed.returncode, dom[-400:]
            )
        )
    return json.loads(html.unescape(match.group(1)))


class DiagnoseInvisibilityPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = find_browser()
        if cls.browser is None:
            message = "no Edge or Chrome found for the report page tests"
            if os.environ.get("CI"):
                raise AssertionError(message)
            raise unittest.SkipTest(message)

    def scenario(self, name):
        result = run_scenario(self.browser, name)
        self.assertNotIn("exception", result, result.get("exception"))
        self.assertEqual(result["errors"], [])
        return result

    def test_inspect_answers_match_the_newest_request(self):
        result = self.scenario("inspect_tokens")
        self.assertTrue(result["wrong_token_ignored"])
        self.assertEqual(result["requested_row_shown"], "Wall (id 101)")
        self.assertTrue(result["closed"])
        self.assertTrue(result["after_close_ignored"])
        self.assertTrue(result["late_older_ignored"])
        self.assertEqual(result["newest_shown"], "Wall (id 103)")
        self.assertTrue(result["tokens_distinct"])

    def test_earlier_row_answer_cannot_win_over_add_revit_selection(self):
        result = self.scenario("inspect_tokens")
        self.assertTrue(result["earlier_row_answer_arriving_first_ignored"])
        self.assertEqual(result["selection_answer_shown"], "Wall (id 104)")

    def test_selection_pruning_keeps_inspected_elements(self):
        result = self.scenario("selection_pruning")
        self.assertEqual(result["selected_before"], [101, 103])
        self.assertTrue(result["inspected_kept_after_state"])
        self.assertTrue(result["removed_member_pruned"])
        self.assertTrue(result["inspected_still_kept"])

    def test_active_level_stays_in_the_dropdown(self):
        result = self.scenario("level_option_kept")
        self.assertEqual(result["rows_with_level"], 2)
        self.assertEqual(result["options"], ["", "L2", "L3"])
        self.assertEqual(result["select_value"], "L2")
        self.assertEqual(result["rows_after_rebuild"], 0)

    def test_rows_multi_select_with_shift_and_ctrl(self):
        result = self.scenario("multi_select")
        self.assertEqual(result["plain"], [0])
        self.assertEqual(result["shift_range"], [0, 1, 2, 3])
        self.assertIn("4 selected", result["bar"])
        self.assertEqual(result["ctrl_removes"], [0, 2, 3])
        self.assertEqual(result["ctrl_adds"], [0, 2, 3, 5])
        self.assertEqual(result["add_ids"], [[101, 104, 106]])
        self.assertEqual(result["select_ids"], [[101, 103, 104, 106]])
        self.assertEqual(result["plain_after_multi"], [4])
        self.assertEqual(result["shift_from_anchor"], [2, 3, 4])
        self.assertEqual(result["cleared"], [])
        self.assertTrue(result["card_hidden_after_clear"])


if __name__ == "__main__":
    unittest.main()
