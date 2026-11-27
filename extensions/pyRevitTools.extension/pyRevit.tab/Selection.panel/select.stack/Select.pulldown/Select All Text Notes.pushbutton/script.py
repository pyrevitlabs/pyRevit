# -*- coding: utf-8 -*-
"""Select all text notes of the model."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


text_note_ids = [
    text_note.Id
    for text_note in revit.query.get_elements_by_class(DB.TextNote, doc=revit.doc)
]
if not text_note_ids:
    forms.alert(_t("no_text_notes"), exitscript=True)

revit.get_selection().set_to(text_note_ids)
