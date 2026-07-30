# -*- coding: utf-8 -*-
"""Shared config schema, defaults, and localization for the Filter Legend
tool.

Used by both script.py (main command) and config.py (settings dialog,
opened via the button's "Configure" action) so the two never drift out
of sync -- there is exactly one place that knows the setting names,
defaults, and labels.
"""

from pyrevit import script
from pyrevit import DB
from pyrevit.revit.db.query import is_metric
from pyrevit.coreutils import applocales

INI = "filterlegend"

# Single source of truth for the *length* setting defaults, expressed in
# millimeters regardless of project units -- get_length_unit()/
# display_defaults() below convert this into whatever unit is actually
# shown to the user for a given project. Never read these directly for
# a UI label or a stored config value; go through display_defaults().
DEFAULTS_MM = {
    "row_height": 5.0,
    "row_spacing": 2.0,
    "swatch_width": 8.0,
    "text_column_width": 60.0,
}

# Non-length defaults are unit-independent.
DEFAULTS_BOOL = {
    "sort_alphabetically": True,
    "open_last_legend": True,
}


def get_length_unit(doc):
    """Decide which unit this tool should use for all user-facing length
    values (row height, spacing, swatch/column widths), based on the
    *project's own* Project Units setting.

    Args:
        doc: Document

    Returns:
        tuple: (unit_type_id, is_metric)
    """
    display_unit = DB.UnitTypeId.Millimeters if is_metric(doc) else DB.UnitTypeId.Inches
    return display_unit, is_metric(doc)


def get_length_unit_symbol(is_metric):
    """Short unit label for settings-dialog field captions."""
    return "mm" if is_metric else "in"


def display_defaults(doc):
    """DEFAULTS_MM converted into whichever unit get_length_unit() picks
    for this project, so defaults, stored config values, and dialog
    labels all speak the same unit.

    Args:
        doc: Document

    Returns:
        dict: {setting_name: value_in_display_unit}
    """
    display_unit, _ = get_length_unit(doc)
    converted = {}
    for key, mm_value in DEFAULTS_MM.items():
        internal_ft = DB.UnitUtils.ConvertToInternalUnits(
            mm_value, DB.UnitTypeId.Millimeters
        )
        converted[key] = DB.UnitUtils.ConvertFromInternalUnits(
            internal_ft, display_unit
        )
    return converted


# Nominal base path -- this file need not exist. applocales derives the
# sibling resource-dictionary filenames from it:
#   resources.ResourceDictionary.<locale>.xaml
_RESX_BASE = script.get_bundle_file("resources.xaml")


def resx(key, default=None):
    """Look up a localized UI string for the current pyRevit / Revit
    language, falling back to en_us and then to `default`.

    Args:
        key: resource key (x:Key in the ResourceDictionary files)
        default: value to use if the key isn't found in any locale file

    Returns:
        str: localized string, `default`, or `key` if no default given
    """
    result = applocales.get_locale_string_from_xaml(_RESX_BASE, key)
    if result == key and default is not None:
        return default
    return result


def get_text_type_options(doc):
    """Collect available TextNoteTypes in the document.

    Args:
        doc: Document

    Returns:
        tuple: (sorted list of type names, {name: TextNoteType} dict)
    """
    all_types = DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType).ToElements()
    by_name = {}
    for t in all_types:
        name_param = t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
        name = name_param.AsString() if name_param else t.Name
        by_name[name] = t
    return sorted(by_name.keys()), by_name


def build_settings_schema(doc, text_type_names):
    """Build the settings_window schema, with localized labels and
    length defaults/units matched to this project.

    Args:
        doc: Document (used to pick mm vs. inches and convert defaults)
        text_type_names: sorted list of available TextNoteType names

    Returns:
        list: schema consumable by
            pyrevit.forms.settings_window.show_settings
    """
    display_unit, is_metric = get_length_unit(doc)
    unit_symbol = get_length_unit_symbol(is_metric)
    defaults = display_defaults(doc)

    def length_label(key, fallback_text):
        template = resx(key, fallback_text + " ({0})")
        return template.format(unit_symbol)

    def mm(value):
        """Express a millimeter value in this project's display unit,
        for min/max bounds that should scale sensibly whether the field
        is showing mm or inches."""
        internal_ft = DB.UnitUtils.ConvertToInternalUnits(
            value, DB.UnitTypeId.Millimeters
        )
        return DB.UnitUtils.ConvertFromInternalUnits(internal_ft, display_unit)

    return [
        {
            "type": "section",
            "label": resx("Settings_Section_Layout", "Text & Layout"),
        },
        {
            "name": "text_type",
            "type": "choice",
            "label": resx("Settings_TextType", "Text Note Type"),
            "options": text_type_names,
            "default": text_type_names[0] if text_type_names else "",
        },
        {
            "name": "row_height",
            "type": "float",
            "label": length_label("Settings_RowHeight", "Row Height"),
            "default": defaults["row_height"],
            "min": mm(1.0),
            "max": mm(50.0),
        },
        {
            "name": "row_spacing",
            "type": "float",
            "label": length_label("Settings_RowSpacing", "Row Spacing"),
            "default": defaults["row_spacing"],
            "min": 0.0,
            "max": mm(50.0),
        },
        {
            "name": "swatch_width",
            "type": "float",
            "label": length_label("Settings_SwatchWidth", "Swatch Width"),
            "default": defaults["swatch_width"],
            "min": mm(2.0),
            "max": mm(50.0),
        },
        {
            "name": "text_column_width",
            "type": "float",
            "label": length_label("Settings_ColumnWidth", "Text Column Width"),
            "default": defaults["text_column_width"],
            "min": mm(10.0),
            "max": mm(200.0),
        },
        {
            "type": "section",
            "label": resx("Settings_Section_Behavior", "Behavior"),
        },
        {
            "name": "sort_alphabetically",
            "type": "bool",
            "label": resx("Settings_SortAlpha", "Sort Filters Alphabetically"),
            "default": DEFAULTS_BOOL["sort_alphabetically"],
        },
        {
            "name": "open_last_legend",
            "type": "bool",
            "label": resx("Settings_OpenLegend", "Open Last Created Legend"),
            "default": DEFAULTS_BOOL["open_last_legend"],
        },
    ]
