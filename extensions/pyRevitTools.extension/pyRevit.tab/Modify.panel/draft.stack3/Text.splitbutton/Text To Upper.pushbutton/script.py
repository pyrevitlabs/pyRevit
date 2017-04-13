"""Converts the select text note element into UPPERCASE text."""

from revitutils import doc, selection, Action

with Action('to Upper'):
    for el in selection.elements:
        el.Text = el.Text.upper()
