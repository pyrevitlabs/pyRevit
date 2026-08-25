# -*- coding: utf-8 -*-
"""Hosted unit tests for the output window API.

Run from Revit via the DevTools "Output Window Tests" button (zero-doc
context) or the "Run All Tests" aggregator. The tests exercise window
metadata, buffered printing, progress bar control, and chart factory
methods without requiring a document.

Visual correctness (styling, ordering, emoji rendering) is covered by
the print-based regression buttons under Log Output Tests and by the
"Test Output Stream" button; this suite only asserts programmatic
behavior.
"""

import unittest


class OutputWindowMetadataTests(unittest.TestCase):
    """Window identity, title, size, and debug-mode handling."""

    def setUp(self):
        """Grab the shared output window instance."""
        from pyrevit import script

        self.output = script.get_output()

    def test_output_is_singleton(self):
        """Repeated get_output calls return the same output window."""
        from pyrevit import script

        self.assertEqual(self.output.output_id, script.get_output().output_id)

    def test_output_uniqueid(self):
        """Output window exposes a non-empty unique id."""
        self.assertTrue(self.output.output_uniqueid)

    def test_title_round_trip(self):
        """A stored title is retrievable via get_title."""
        self.output.set_title("pyRevit Output Window Tests")
        self.assertEqual("pyRevit Output Window Tests", self.output.get_title())

    def test_width_round_trip(self):
        """A stored width is retrievable via get_width."""
        original_width = self.output.get_width()
        self.output.set_width(600)
        try:
            self.assertEqual(600, self.output.get_width())
        finally:
            self.output.set_width(original_width)

    def test_debug_mode_round_trip(self):
        """Debug mode toggles are reflected by the getter."""
        original_state = self.output.debug_mode
        try:
            self.output.debug_mode = True
            self.assertTrue(self.output.debug_mode)
            self.output.debug_mode = False
            self.assertFalse(self.output.debug_mode)
        finally:
            self.output.debug_mode = original_state

    def test_get_head_html_returns_string(self):
        """Head html getter returns a string."""
        self.assertIsInstance(self.output.get_head_html(), str)

    def test_is_closed_by_user_returns_bool(self):
        """Open windows report False for user-closed state."""
        self.assertFalse(self.output.is_closed_by_user())


class OutputWindowPrintTests(unittest.TestCase):
    """Buffered printing methods complete without error."""

    def setUp(self):
        """Grab the shared output window instance."""
        from pyrevit import script

        self.output = script.get_output()

    def test_print_md(self):
        """Markdown printing completes without error."""
        self.assertIsNone(self.output.print_md("**bold** _italic_"))

    def test_print_html(self):
        """Raw html printing completes without error."""
        self.assertIsNone(self.output.print_html('<div style="color:red">html</div>'))

    def test_print_code(self):
        """Code block printing completes without error."""
        self.assertIsNone(self.output.print_code("print('hello')"))

    def test_print_table(self):
        """Tabular data printing accepts columns and formats."""
        self.assertIsNone(
            self.output.print_table(
                [[1, 2, 3], [4, 5, 6]],
                columns=["C1", "C2", "C3"],
                formats=["{}", "{}", "{}%"],
                title="Output Window Tests Table",
            )
        )

    def test_insert_divider(self):
        """Divider insertion completes without error."""
        self.assertIsNone(self.output.insert_divider())

    def test_linkify_returns_html_str(self):
        """Linkified element ids render as clickable html anchors."""
        from pyrevit import DB
        from pyrevit.output.linkmaker import PROTOCOL_NAME

        link = self.output.linkify(DB.ElementId(123))
        self.assertIsInstance(link, str)
        self.assertIn(PROTOCOL_NAME, link)
        self.assertIn("element[]=123", link)


class OutputWindowProgressTests(unittest.TestCase):
    """Progress bar control methods complete without error."""

    def setUp(self):
        """Grab the shared output window instance."""
        from pyrevit import script

        self.output = script.get_output()

    def test_update_progress(self):
        """Progress updates accept current and max values."""
        self.assertIsNone(self.output.update_progress(50, 100))

    def test_indeterminate_progress(self):
        """Indeterminate progress state toggles without error."""
        self.assertIsNone(self.output.indeterminate_progress(True))
        self.assertIsNone(self.output.indeterminate_progress(False))

    def test_hide_unhide_reset_progress(self):
        """Hide/unhide/reset progress cycle without error."""
        self.assertIsNone(self.output.hide_progress())
        self.assertIsNone(self.output.unhide_progress())
        self.assertIsNone(self.output.reset_progress())


class OutputWindowLogPanelTests(unittest.TestCase):
    """Log panel and styled log record methods complete without error."""

    def setUp(self):
        """Grab the shared output window instance."""
        from pyrevit import script

        self.output = script.get_output()

    def test_show_hide_logpanel(self):
        """Show/hide log panel cycle without error."""
        self.assertIsNone(self.output.show_logpanel())
        self.assertIsNone(self.output.hide_logpanel())

    def test_log_levels(self):
        """All styled log record levels render without error."""
        self.assertIsNone(self.output.log_debug("test debug"))
        self.assertIsNone(self.output.log_info("test info"))
        self.assertIsNone(self.output.log_success("test success"))
        self.assertIsNone(self.output.log_warning("test warning"))
        self.assertIsNone(self.output.log_error("test error"))


class OutputWindowChartFactoryTests(unittest.TestCase):
    """Chart factory methods produce configurable chart objects."""

    def setUp(self):
        """Grab the shared output window instance."""
        from pyrevit import script

        self.output = script.get_output()

    def test_make_chart(self):
        """Generic charts expose data, options, and draw."""
        chart = self.output.make_chart()
        self.assertIsNotNone(chart)
        self.assertIsNotNone(chart.data)
        self.assertIsNotNone(chart.options)
        self.assertTrue(callable(chart.draw))

    def test_make_line_chart(self):
        """Line charts are created with the line chart type."""
        from pyrevit.coreutils.charts import LINE_CHART

        chart = self.output.make_line_chart()
        self.assertIsNotNone(chart)
        self.assertEqual(LINE_CHART, chart.type)
