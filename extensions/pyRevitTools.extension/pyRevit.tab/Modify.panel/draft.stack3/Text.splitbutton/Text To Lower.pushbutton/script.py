"""Converts the select text note element into lowercase text."""

from revitutils import doc, selection, Action

with Action('to Lower'):
    for el in selection.elements:
        el.Text = el.Text.lower()
