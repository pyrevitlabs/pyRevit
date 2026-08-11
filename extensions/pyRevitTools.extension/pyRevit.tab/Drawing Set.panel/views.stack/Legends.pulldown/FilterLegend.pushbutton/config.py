# -*- coding: utf-8 -*-
from pyrevit import revit, forms
from pyrevit.forms import settings_window

from legend_config import INI, resx, get_text_type_options, build_settings_schema

doc = revit.doc

text_type_names, _ = get_text_type_options(doc)


if not text_type_names:
    forms.alert(
        resx("Msg_NoTextTypes", "No Text Note Types found in the project."),
        exitscript=True,
    )

schema = build_settings_schema(doc, text_type_names)

settings_window.show_settings(
    schema,
    section=doc.Title,
    title=resx("Settings_Title", "Filter Legend Settings"),
    custom_config=INI,
)
