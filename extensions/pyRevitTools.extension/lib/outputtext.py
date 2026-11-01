# -*- coding: utf-8 -*-
"""Text helpers for the output window shared by the pyRevit Tools buttons."""

from pyrevit.coreutils import escape_for_html

MARKDOWN_SPECIAL_CHARACTERS = "|*_`["


def escape_for_output(text):
    """Make model text render literally in print_table cells and print_md headings.

    print_table splits cells on pipes and renders Markdown, so pipes, emphasis and
    link characters are encoded as entities. Ampersands are encoded so names such
    as "&copy;" are not read as entities, and line breaks become spaces so a name
    stays on one table row.

    Args:
        text (str): Text taken from the model, such as an element or type name.

    Returns:
        str: Text safe to embed in Markdown or table cells.
    """
    escaped = escape_for_html(" ".join(text.splitlines()).replace("&", "&#38;"))
    for character in MARKDOWN_SPECIAL_CHARACTERS:
        escaped = escaped.replace(character, "&#{};".format(ord(character)))
    return escaped
