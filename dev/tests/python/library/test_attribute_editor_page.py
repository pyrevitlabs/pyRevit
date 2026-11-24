"""Host-free tests for the Attribute Editor bundle.

Loads the bundle's real ``attribute_grid_core.js`` and ``attribute_grid.js`` in a
headless Chromium-based browser through
``fixtures/attribute_grid_page/harness.html``, with a stubbed WebView2 bridge and
a scripted backend, and asserts on what each scenario leaves in the page. No
Revit is involved. Also checks that the 8 locale dictionaries and
``bundle.yaml`` stay complete and consistent with the strings the code uses.

A missing browser fails the browser tests on CI and skips them elsewhere, so a
runner without Edge or Chrome cannot pass silently.
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
import xml.etree.ElementTree as ET

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Integration"

REPO = pathlib.Path(__file__).resolve().parents[4]
BUNDLE = (
    REPO
    / "extensions"
    / "pyRevitTools.extension"
    / "pyRevit.tab"
    / "Modify.panel"
    / "edit3.stack"
    / "Edit.pulldown"
    / "Attribute Editor.pushbutton"
)
HARNESS = (
    pathlib.Path(__file__).parent / "fixtures" / "attribute_grid_page" / "harness.html"
)
LOCALES = ("en_us", "de_de", "fr_fr", "es_es", "pt_br", "ru", "chinese_s", "ko")
BROWSER_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)
RESULT = re.compile(r'<pre id="out"[^>]*>RESULT (.*?)</pre>', re.DOTALL)
XAML_KEY = "{http://schemas.microsoft.com/winfx/2006/xaml}Key"
XAML_STRING = "{clr-namespace:System;assembly=mscorlib}String"


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
                "--window-size=1400,900",
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
    if match is None or completed.returncode != 0:
        raise AssertionError(
            "scenario {} did not finish cleanly (exit {}): {}".format(
                name, completed.returncode, dom[-400:]
            )
        )
    return json.loads(html.unescape(match.group(1)))


def read_locale(locale):
    root = ET.parse(
        BUNDLE / "resources.ResourceDictionary.{}.xaml".format(locale)
    ).getroot()
    return {element.get(XAML_KEY): element.text for element in root.iter(XAML_STRING)}


def keys_used_by_the_code():
    used = set()
    script = (BUNDLE / "attribute_grid.js").read_text(encoding="utf-8")
    used |= {"ui_" + key for key in re.findall(r'this\.S\("([a-z_0-9]+)"', script)}
    for prefix in ("unit", "theme"):
        used.discard("ui_{}_".format(prefix))
    for mode in ("display", "number", "internal"):
        used |= {"ui_unit_" + mode, "ui_unit_{}_hint".format(mode)}
    used |= {"ui_theme_" + mode for mode in ("auto", "light", "dark")}
    for path in BUNDLE.glob("*.py"):
        used |= set(
            re.findall(
                r'\b(?:t|token_set|translations)\("([a-z_0-9]+)"\)',
                path.read_text(encoding="utf-8"),
            )
        )
    return used


class LocaleTests(unittest.TestCase):
    def test_every_locale_defines_the_same_keys_as_english(self):
        english = read_locale("en_us")
        for locale in LOCALES:
            self.assertEqual(set(read_locale(locale)), set(english), locale)

    def test_placeholders_match_english_in_every_locale(self):
        english = read_locale("en_us")
        for locale in LOCALES:
            for key, text in read_locale(locale).items():
                self.assertEqual(
                    sorted(re.findall(r"\{\d\}", text)),
                    sorted(re.findall(r"\{\d\}", english[key])),
                    "{} / {}".format(locale, key),
                )

    def test_no_string_is_empty(self):
        for locale in LOCALES:
            for key, text in read_locale(locale).items():
                self.assertTrue(text and text.strip(), "{} / {}".format(locale, key))

    def test_every_string_the_code_asks_for_exists(self):
        self.assertEqual(keys_used_by_the_code() - set(read_locale("en_us")), set())

    def test_no_string_is_left_unused(self):
        self.assertEqual(set(read_locale("en_us")) - keys_used_by_the_code(), set())


class BundleMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import yaml

        cls.meta = yaml.safe_load((BUNDLE / "bundle.yaml").read_text(encoding="utf-8"))

    def test_title_and_tooltip_cover_all_locales(self):
        for field in ("title", "tooltip"):
            self.assertEqual(set(self.meta[field]), set(LOCALES), field)

    def test_every_title_carries_the_alternate_mode_dot(self):
        for locale, title in self.meta["title"].items():
            self.assertTrue(title.endswith(" \u25cf"), locale)

    def test_every_tooltip_has_a_shift_click_block(self):
        for locale, tooltip in self.meta["tooltip"].items():
            paragraphs = tooltip.split("\n\n")
            self.assertEqual(len(paragraphs), 2, locale)
            self.assertEqual(len(paragraphs[1].splitlines()), 2, locale)

    def test_the_persistent_engine_outlives_the_page_handlers_it_hosts(self):
        self.assertEqual(self.meta["engine"], {"persistent": True})
        script = (BUNDLE / "script.py").read_text(encoding="utf-8")
        self.assertIn("script.set_envvar(SESSION_KEY, session)", script)
        self.assertIn("script.get_envvar(SESSION_KEY)", script)

    def test_runs_in_a_project_from_revit_2022(self):
        self.assertEqual(self.meta["context"], "doc-project")
        self.assertEqual(self.meta["min_revit_version"], 2022)

    def test_the_button_links_to_its_documentation_page(self):
        self.assertEqual(
            self.meta["help_url"], "https://docs.pyrevitlabs.io/tools/attribute-editor/"
        )
        self.assertTrue((REPO / "docs" / "tools" / "attribute-editor.md").is_file())

    def test_icons_exist_in_both_themes(self):
        self.assertTrue((BUNDLE / "icon.png").is_file())
        self.assertTrue((BUNDLE / "icon.dark.png").is_file())


class AttributeGridPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = find_browser()
        if cls.browser is None:
            message = "no Edge or Chrome found for the Attribute Editor page tests"
            if os.environ.get("CI"):
                raise AssertionError(message)
            raise unittest.SkipTest(message)

    def scenario(self, name):
        result = run_scenario(self.browser, name)
        self.assertNotIn("exception", result, result.get("exception"))
        self.assertEqual(result["errors"], [])
        return result

    def test_tsv_parsing_follows_what_excel_writes(self):
        result = self.scenario("core_tsv")
        self.assertEqual(result["simple"], [["a", "b"], ["c", "d"]])
        self.assertEqual(result["quoted"], [["x\ty", "line1\nline2", 'say "hi"']])
        self.assertEqual(result["crlf"], [["a", "b"], ["c", "d"]])
        self.assertEqual(result["single"], [["5"]])
        self.assertEqual(result["empty_cell"], [["", ""]])
        self.assertEqual(result["nothing"], [])
        self.assertEqual(result["round_trip"], [["a b", 'q"q', "t\tt", "n\nn", ""]])
        self.assertEqual(result["formatted"], 'plain\ttwo words\n"q"""\t"x\ty"')

    def test_fill_series_follows_excel(self):
        result = self.scenario("core_fill")
        self.assertEqual(result["copy_single_number"], ["5", "5", "5"])
        self.assertEqual(result["copy_single_text"], ["abc", "abc"])
        self.assertEqual(
            result["increment_text_number"], ["Door 2", "Door 3", "Door 4"]
        )
        self.assertEqual(result["increment_padded"], ["D-008", "D-009", "D-010"])
        self.assertEqual(result["invert_number"], ["6", "7", "8"])
        self.assertEqual(result["invert_text_number_copies"], ["Door 1", "Door 1"])
        self.assertEqual(result["linear"], ["5", "7", "9"])
        self.assertEqual(result["linear_units"], ["200 mm", "250 mm"])
        self.assertEqual(result["decimals"], ["2.5", "3.0"])
        self.assertEqual(result["comma_decimals"], ["2,5", "3,0"])
        self.assertEqual(result["backward"], ["0", "-10"])
        self.assertEqual(result["cycle"], ["a", "b", "a", "b", "a"])
        self.assertEqual(result["cycle_backward"], ["b", "a", "b"])
        self.assertEqual(result["mixed"], ["A1", "B2"])
        self.assertEqual(result["negative"], ["-5", "-7"])
        self.assertEqual(result["hyphen_id"], ["A-6", "A-7"])

    def test_merge_keeps_unsent_edits_and_flags_conflicts(self):
        result = self.scenario("core_merge")
        self.assertEqual(result["cur"], [["a-edit", "x"], ["b", "y-edit"], ["d", "w"]])
        self.assertEqual(result["base"], [["a", "x"], ["b", "y-revit"], ["d", "w"]])
        self.assertEqual(result["conflict_cells"], [[], [[1, "y-revit"]], []])
        self.assertEqual(result["conflicts"], 1)
        self.assertEqual(result["dropped"], 1)
        self.assertEqual(result["dropped_with_column_removed"], 2)

    def test_schedule_loads_into_a_grid(self):
        result = self.scenario("grid_load")
        self.assertEqual(result["rows"], 5)
        self.assertEqual(result["headings"], ["Mark", "Width", "Fire Rating", "Level"])
        self.assertEqual(result["first_row"], ["D1", "900 mm", "30", "L1"])
        self.assertEqual(result["locked_count"], 5)
        self.assertEqual(result["type_badges"], 1)
        self.assertEqual(result["sent_actions"], ["schedules", "load", "available"])
        self.assertIsNone(result["load_columns_default"])
        self.assertEqual(result["select_options"], ["ui_new_grid", "Doors", "Walls"])

    def test_theme_follows_revit_until_the_user_chooses(self):
        result = self.scenario("grid_theme")
        self.assertEqual(result["auto_follows_revit"], "dark")
        self.assertEqual(result["forced_light"], "light")
        self.assertEqual(result["saved"], ["light"])
        self.assertEqual(result["forced_dark"], "dark")

    def test_paste_from_excel_fills_a_block_and_respects_locked_cells(self):
        result = self.scenario("grid_paste")
        self.assertEqual(
            result["after_block"],
            [
                ["D1", "900 mm"],
                ["X1", "800"],
                ["X2", "850"],
                ["D4", "1000 mm"],
                ["D5", "1000 mm"],
            ],
        )
        self.assertEqual(result["dirty"], 4)
        self.assertIn("Push (4)", result["push_label"])
        self.assertEqual(result["fill_all_selected"], [["fill", "fill"]] * 3)
        self.assertEqual(result["locked_unchanged"], "L1")

    def test_type_parameter_edits_mirror_across_the_type_and_undo_together(self):
        result = self.scenario("grid_type_mirror")
        self.assertEqual(result["col2"], ["30", "30", "90", "90", "90"])
        self.assertEqual(result["dirty"], 3)
        self.assertEqual(result["after_undo"], ["30", "30", "60", "60", "60"])
        self.assertEqual(result["after_redo"], ["30", "30", "90", "90", "90"])

    def test_keyboard_editing(self):
        result = self.scenario("grid_edit_keyboard")
        self.assertTrue(result["editor_open"])
        self.assertEqual(result["editor_value"], "x")
        self.assertEqual(result["committed"], "Zed")
        self.assertEqual(result["moved_down"], "1")
        self.assertEqual(result["cleared"], "")
        self.assertEqual(result["undone"], "D2")
        self.assertEqual(result["escape_keeps"], "Zed")
        self.assertEqual(result["arrow_target"], ["1", "1"])

    def test_copy_writes_tsv(self):
        result = self.scenario("grid_copy")
        self.assertEqual(result["copied"], "D1\t900 mm\nD2\t900 mm")

    def test_fill_handle_increments_text_with_a_trailing_number(self):
        result = self.scenario("grid_fill_handle")
        self.assertTrue(result["handle_visible"])
        self.assertEqual(result["preview_cells"], 3)
        self.assertEqual(
            result["single_text_number_filled"],
            ["Door 1", "Door 2", "Door 3", "Door 4"],
        )
        self.assertEqual(result["seed_set"], "100 mm")

    def test_fill_handle_continues_a_two_cell_series(self):
        result = self.scenario("grid_fill_series_two")
        self.assertEqual(result["series"], ["1", "3", "5", "7", "9"])
        self.assertEqual(
            result["after_fill_down_only_selection"], ["1", "1", "1", "1", "1"]
        )

    def test_push_results_mark_errors_and_conflicts_and_normalise_values(self):
        result = self.scenario("grid_push_results")
        self.assertEqual(
            result["payload"],
            [
                [101, "bip|-1|i", "N1", "D1"],
                [102, "bip|-1|i", "N2", "D2"],
                [103, "bip|-1|i", "N3", "D3"],
            ],
        )
        self.assertFalse(result["force"])
        self.assertEqual(result["normalized"], "N1 normalized")
        self.assertEqual(result["error_cells"], 1)
        self.assertEqual(result["conflict_cells"], 1)
        self.assertTrue(result["conflict_bar_visible"])
        self.assertEqual(result["error_tip"], "Revit rejected the value.")
        self.assertEqual(result["conflict_tip"], "Revit now has: Changed in Revit")
        self.assertEqual(result["dirty_left"], 2)
        self.assertEqual(result["after_use_revit"], "Changed in Revit")
        self.assertFalse(result["conflict_bar_after"])

    def test_a_type_edit_is_sent_once_and_clears_the_whole_type(self):
        result = self.scenario("grid_push_type_once")
        self.assertEqual(result["edits_sent"], 1)
        self.assertEqual(result["col2"], ["30", "30", "90 min", "90 min", "90 min"])
        self.assertEqual(result["dirty_left"], 0)

    def test_sort_and_quick_filter(self):
        result = self.scenario("grid_sort_filter")
        self.assertEqual(result["desc"], ["D5", "D4", "D3", "D2", "D1"])
        self.assertEqual(result["filtered"], ["D5", "D4", "D3"])
        self.assertIn("3 of 5 rows", result["status"])

    def test_find_and_replace_all(self):
        result = self.scenario("grid_find_replace")
        self.assertTrue(result["find_open"])
        self.assertEqual(
            result["replaced"], ["Door-1", "Door-2", "Door-3", "Door-4", "Door-5"]
        )

    def test_a_new_grid_starts_without_columns_and_loads_what_was_chosen(self):
        result = self.scenario("grid_scratch_switch")
        self.assertEqual(result["plan_before"], 4)
        self.assertEqual(result["plan_after"], 0)
        self.assertEqual(result["columns_after"], 0)
        self.assertEqual(result["rows_after"], 0)
        self.assertTrue(result["panel_open"])
        self.assertEqual(result["categories"], ["Structural Columns74"])
        self.assertEqual(result["empty_note"], "ui_empty_scratch")
        self.assertEqual(
            result["load_source"],
            {
                "kind": "scratch",
                "categories": [-2001330],
                "scope": "model",
                "types": False,
            },
        )
        self.assertEqual(result["load_columns"], ["bip|-9|i"])
        self.assertEqual(result["rows_loaded"], 1)

    def test_a_conflicted_cell_is_not_pushed_until_the_user_decides(self):
        result = self.scenario("grid_conflict_not_pushed")
        self.assertEqual(result["conflict_cells"], 1)
        self.assertEqual(result["cell_text"], "N1")
        self.assertEqual(result["pushes"], 0)
        self.assertEqual(result["toast"], "ui_push_conflicts")
        self.assertEqual(result["pushes_after_keep_mine"], 1)
        self.assertEqual(result["sent_base"], "Changed in Revit")

    def test_text_typed_while_a_push_is_running_is_kept(self):
        result = self.scenario("grid_edit_during_push")
        self.assertEqual(result["cell_after"], "N2")
        self.assertTrue(result["dirty"])
        self.assertEqual(result["base"], "N1 normalized")

    def test_pull_keeps_conflicts_until_resolved_and_reports_dropped_edits(self):
        result = self.scenario("core_merge_pulls")
        self.assertEqual(result["first"], ["B", "C", 1, [[0, "C"]]])
        self.assertEqual(result["second"], ["B", "C", 1, [[0, "C"]]])
        self.assertEqual(result["revit_now_matches"], ["B", "B", 0])
        self.assertEqual(result["locked"], ["A", 1])
        self.assertEqual(result["type_moved"], ["A", 1])
        self.assertEqual(result["instance_kept"], ["B", 0])
        self.assertEqual(result["type_followed"], [["A", "B"], 0, 0])
        self.assertEqual(result["type_conflict_counted_once"], [1, [1, 1]])

    def test_undo_and_redo_survive_a_filter_that_hides_the_edited_row(self):
        result = self.scenario("grid_undo_in_filtered_view")
        self.assertEqual(result["rows_visible"], 0)
        self.assertTrue(result["toolbar_rendered"])
        self.assertTrue(result["anchor_valid"])
        self.assertEqual(result["ids"], [])

    def test_a_push_reply_for_a_replaced_grid_is_not_applied(self):
        result = self.scenario("grid_stale_push_reply")
        self.assertEqual(result["columns_after"], 0)
        self.assertEqual(result["toasts"], ["1 written"])

    def test_opening_and_confirming_a_multiline_cell_stages_no_edit(self):
        result = self.scenario("grid_f2_on_multiline_cell")
        self.assertEqual(result["dirty_after_enter"], 0)
        self.assertEqual(result["dirty_after_change"], 1)

    def test_changing_the_scratch_source_asks_before_dropping_pending_edits(self):
        result = self.scenario("grid_scratch_source_change_prompt")
        self.assertEqual(result["dirty_before"], 1)
        self.assertTrue(result["dialog_shown"])
        self.assertEqual(result["loads_while_asking"], 0)
        self.assertEqual(result["dirty_after_cancel"], 1)
        self.assertEqual(result["loads_after_cancel"], 0)
        self.assertEqual(result["dirty_after_discard"], 0)
        self.assertEqual(result["loads_after_discard"], 1)

    def test_a_conflict_survives_later_edits_and_undo_until_resolved(self):
        result = self.scenario("grid_conflict_survives_edit_and_undo")
        self.assertEqual(result["conflict_after_pull"], 1)
        self.assertEqual(result["conflict_after_edit"], 1)
        self.assertEqual(result["cell_after_undo"], "N1")
        self.assertEqual(result["conflict_after_undo"], 1)
        self.assertEqual(result["pushes"], 0)
        self.assertEqual(result["conflict_when_equal_to_revit"], 0)
        self.assertEqual(result["dirty_when_equal_to_revit"], 0)

    def test_selection_follows_its_row_when_undo_or_redo_changes_the_filtered_view(
        self,
    ):
        result = self.scenario("grid_undo_selection_follows_the_row")
        self.assertEqual(result["rows_with_x_hidden"], 4)
        self.assertEqual(result["rows_after_undo"], 5)
        self.assertEqual(result["selected_before_redo"], "D2")
        self.assertEqual(result["rows_after_redo"], 4)
        self.assertEqual(result["selected_after_redo"], "D2")

    def test_changing_columns_keeps_the_selection_the_grid_was_built_from(self):
        result = self.scenario("grid_show_grid_keeps_the_pinned_selection")
        self.assertEqual(result["dirty_before"], 1)
        self.assertFalse(result["first_load_has_selection"])
        self.assertEqual(result["second_load_selection"], [1, 2])
        self.assertEqual(result["dirty_after"], 1)
        self.assertFalse(result["dialog_shown"])

    def test_a_reordered_category_set_keeps_pending_edits_without_asking(self):
        result = self.scenario("grid_scratch_reordered_categories_merge")
        self.assertEqual(result["dirty_before"], 1)
        self.assertFalse(result["dialog_shown"])
        self.assertEqual(result["loads"], 1)
        self.assertEqual(result["dirty_after"], 1)
        self.assertEqual(result["cell_after"], "EDIT")

    def test_finding_parameters_does_not_change_the_source_a_pull_reloads(self):
        result = self.scenario("grid_find_parameters_keeps_the_grid_source")
        self.assertEqual(result["pull_source"], [[-1]])
        self.assertEqual(result["dirty_after_pull"], 1)
        self.assertEqual(result["cell_after_pull"], "EDIT")

    def test_a_schedule_reply_arriving_after_switching_to_a_new_grid_is_ignored(self):
        result = self.scenario("grid_late_load_reply_is_ignored")
        self.assertEqual(result["source_kind"], "scratch")
        self.assertEqual(result["columns"], 0)
        self.assertEqual(result["rows"], 0)
        self.assertEqual(result["title"], "")
        self.assertEqual(result["select_value"], "__scratch__")

    def test_a_failed_switch_goes_back_to_the_grid_on_screen_and_pull_keeps_edits(self):
        result = self.scenario("grid_failed_switch_restores_the_displayed_source")
        self.assertEqual(result["source_id"], 1)
        self.assertEqual(result["loaded_id"], 1)
        self.assertEqual(result["select_value"], "1")
        self.assertEqual(result["pull_source_ids"], [1])
        self.assertEqual(result["dirty_after_pull"], 1)
        self.assertEqual(result["cell_after_pull"], "N1")

    def test_typing_the_value_revit_now_has_leaves_nothing_pending(self):
        result = self.scenario("grid_typing_the_value_revit_now_has_is_not_pending")
        self.assertEqual(result["conflict_after_push"], 1)
        self.assertEqual(result["pending_before"], 1)
        self.assertEqual(result["conflict_when_typed"], 0)
        self.assertEqual(result["dirty_when_typed"], 0)
        self.assertEqual(result["pending_when_typed"], 0)
        self.assertTrue(result["bar_hidden"])
        self.assertEqual(result["pushes_for_matching_text"], 0)
        self.assertEqual(result["conflict_when_other_text"], 1)
        self.assertEqual(result["pending_when_other_text"], 1)

    def test_a_quote_only_quotes_a_field_when_it_closes_before_a_delimiter(self):
        result = self.scenario("core_quotes")
        self.assertEqual(result["excel_quoted"], [["a\tb", 'c "q" d']])
        self.assertEqual(
            result["unclosed_is_literal"], [['"unclosed', "b"], ["c", "d"]]
        )
        self.assertEqual(result["inner_quote_is_literal"], [['say "hi"', "x"]])
        self.assertEqual(
            result["text_after_closing_quote_is_literal"], [['"a" b', "c"]]
        )
        self.assertEqual(result["empty_quoted"], [["", "x"]])

    def test_numbers_compare_by_value_and_ties_fall_back_to_text(self):
        result = self.scenario("core_numeric")
        self.assertEqual(result["order"], ["0.25", "0.5", "9", "10"])
        self.assertEqual(result["text_order_is_natural"], ["a", "b2", "b10"])
        self.assertEqual(result["dot_grouping"], 1250)
        self.assertEqual(result["comma_grouping"], 1250.5)
        self.assertEqual(result["comma_decimal"], 1.5)
        self.assertEqual(result["negative"], -3.5)
        self.assertIsNone(result["not_a_number"])
        self.assertEqual(result["ties_fall_back_to_text"], ["1'-3", "1'-6"])

    def test_a_series_behind_a_separator_does_not_turn_negative(self):
        result = self.scenario("core_fill")
        self.assertEqual(
            result["separator_prefix_stays_positive"], ["A-1", "A-0", "A-0"]
        )

    def test_number_columns_sort_by_value(self):
        result = self.scenario("grid_sorts_numbers_by_value")
        self.assertEqual(result["ascending"], ["", "0.25", "0.5", "9", "10"])
        self.assertEqual(result["descending"], ["10", "9", "0.5", "0.25", ""])

    def test_a_load_that_ends_while_a_cell_is_open_keeps_what_was_typed(self):
        result = self.scenario("grid_load_while_editing")
        self.assertTrue(result["editor_hidden"])
        self.assertEqual(result["cell"], "Typed")
        self.assertEqual(result["dirty"], 1)

    def test_undo_brings_back_the_error_marker_of_the_cell(self):
        result = self.scenario("grid_undo_restores_the_error_marker")
        self.assertEqual(result["errors_after_push"], 1)
        self.assertEqual(result["errors_after_edit"], 0)
        self.assertEqual(result["errors_after_undo"], 1)
        self.assertEqual(result["tip_after_undo"], "No good.")
        self.assertEqual(result["errors_after_redo"], 0)

    def test_the_page_tells_python_how_many_edits_are_unsent(self):
        result = self.scenario("grid_reports_pending_edits")
        self.assertEqual(result["before_edit"], 0)
        self.assertEqual(result["after_edit"], [1])
        self.assertEqual(result["after_undo"], [1, 0])

    def test_multiline_text_keeps_its_line_breaks_while_editing(self):
        result = self.scenario("grid_edits_multiline_text")
        self.assertEqual(result["editor_value"], "line1\nline2")
        self.assertEqual(result["editor_height"], "52px")
        self.assertEqual(result["after_alt_enter"], "line1\nline2\n")
        self.assertEqual(result["height_after_alt_enter"], "78px")
        self.assertEqual(result["committed"], "line1\nline2\nline3")
        self.assertEqual(result["dirty"], 1)

    def test_the_unit_label_is_only_shown_where_the_numbers_are_in_that_unit(self):
        result = self.scenario("grid_unit_label_follows_the_unit_mode")
        self.assertEqual(result["display"], "Width")
        self.assertEqual(result["number"], "Width [mm]")
        self.assertEqual(result["internal"], "Width")

    def test_the_confirm_dialog_is_modal_and_closes_on_escape(self):
        result = self.scenario("grid_confirm_closes_on_escape")
        self.assertTrue(result["shown"])
        self.assertEqual(result["role"], "alertdialog")
        self.assertTrue(result["focus_on_accept"])
        self.assertTrue(result["tab_moves_to_cancel"])
        self.assertTrue(result["closed"])
        self.assertEqual(result["dirty_kept"], 1)
        self.assertEqual(result["loads_started"], 0)

    def test_rebuilding_the_toolbar_keeps_the_open_dropdown_element(self):
        result = self.scenario("grid_toolbar_keeps_its_elements")
        self.assertTrue(result["same_select"])
        self.assertEqual(result["options"], 3)

    def test_the_grid_exposes_aria_roles(self):
        result = self.scenario("grid_exposes_grid_roles")
        self.assertEqual(result["grid"], 1)
        self.assertEqual(result["rows"], 5)
        self.assertEqual(result["cells"], 20)
        self.assertEqual(result["headers"], 4)
        self.assertEqual(result["rowcount"], "5")
        self.assertEqual(result["selected"], 1)

    def test_large_grids_render_only_the_visible_rows(self):
        result = self.scenario("grid_virtualised")
        self.assertLess(result["rendered_rows"], 60)
        self.assertEqual(result["body_height"], "130000px")
        self.assertEqual(result["first_after_scroll"], "M3994")
        self.assertTrue(result["last_row_available"])


if __name__ == "__main__":
    unittest.main()
