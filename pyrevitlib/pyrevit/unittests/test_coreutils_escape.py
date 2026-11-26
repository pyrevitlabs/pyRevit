# -*- coding: utf-8 -*-
"""Hosted unit tests for pyrevit.coreutils.escape_for_output.

Run from Revit via the DevTools "Run All Tests" button, which discovers every
``test_*`` module in this package. The tests pin how model text is encoded for
output window tables and headings. Ampersands must be encoded before angle
brackets, otherwise the entities written for ``<`` and ``>`` would be escaped
again and show up as literal ``&lt;`` text.
"""

TEST_ENVIRONMENT = "Revit"
TEST_LEVEL = "Unit"

import unittest

from pyrevit.coreutils import escape_for_output


class EscapeForOutputTests(unittest.TestCase):
    """Literal rendering of model text in tables and headings."""

    def test_plain_text_is_unchanged(self):
        """Names without special characters pass through."""
        self.assertEqual("Level 1 - Parking", escape_for_output("Level 1 - Parking"))

    def test_pipe_is_encoded(self):
        """A pipe would otherwise split a table cell."""
        self.assertEqual("A&#124;B", escape_for_output("A|B"))

    def test_markdown_characters_are_encoded(self):
        """Emphasis, code and link openers render literally."""
        self.assertEqual(
            "&#42;a&#42; &#95;b&#95; &#96;c&#96; &#91;d]",
            escape_for_output("*a* _b_ `c` [d]"),
        )

    def test_angle_brackets_are_encoded_once(self):
        """Brackets become entities that are not escaped a second time."""
        self.assertEqual("&lt;Unnamed&gt;", escape_for_output("<Unnamed>"))

    def test_ampersand_is_not_read_as_entity(self):
        """A name such as "&copy;" shows its characters, not a copyright sign."""
        self.assertEqual("&#38;copy;", escape_for_output("&copy;"))

    def test_line_breaks_become_spaces(self):
        """A name stays on one table row."""
        self.assertEqual("A B C D", escape_for_output("A\nB\r\nC\rD"))

    def test_empty_text(self):
        """Empty names stay empty."""
        self.assertEqual("", escape_for_output(""))
