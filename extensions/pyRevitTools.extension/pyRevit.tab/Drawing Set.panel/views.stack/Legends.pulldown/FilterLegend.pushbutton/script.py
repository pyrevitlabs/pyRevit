# -*- coding: utf-8 -*-
"""Create a Legend view listing a view's (or several views')
applied filters as rows of:

    [color swatch] [Filter Name] [Parameter] [Value]

Only filters that resolve to a single, simple "equals" rule (via
match.filter_utils.dissect_parameter_filter) show a real parameter/value.
Compound filters (multi-rule, AND/OR, non-equals evaluators) still get a
name + color swatch, but show N/A for parameter/value.

How-to:
-> Click the button
-> Pick one or more views / view templates that have filters assigned
-> A new Legend view is created per selected view

Button's config-click action to adjust text type, row/column sizing,
sort order, and auto-open behavior -- see config.py.
"""

from pyrevit import revit, forms, script, op
from pyrevit import DB
from pyrevit.coreutils.configparser import open_config_file
from pyrevit.coreutils import appdata

from match.filter_utils import (
    dissect_parameter_filter,
    ogs_has_overrides,
)

from legend.drawing import clear_legend_view
from legend.table import (
    LegendLayout,
    LegendRow,
    create_legend_view,
    draw_legend_table,
)
from legend_storage import (
    save_link,
    get_linked_legend,
    save_managed_elements,
    get_managed_elements,
)
from legend_cfg import (
    INI,
    DEFAULTS_BOOL,
    resx as _t,
    get_text_type_options,
    get_length_unit,
    display_defaults,
)

# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------
logger = script.get_logger()

doc = revit.doc
uidoc = revit.uidoc

NA_TEXT = _t("Value_NA", "N/A")

# ---------------------------------------------------------------------------
# GATHER VIEWS / TEMPLATES WITH FILTERS ASSIGNED
# ---------------------------------------------------------------------------
all_views = (
    DB.FilteredElementCollector(doc)
    .OfCategory(DB.BuiltInCategory.OST_Views)
    .WhereElementIsNotElementType()
    .ToElements()
)

views_with_filters = []
for v in all_views:
    if not isinstance(v, DB.View):
        continue
    try:
        if v.AreGraphicsOverridesAllowed() and v.GetFilters():
            views_with_filters.append(v)
    except Exception:
        # Some view types (schedules, sheets, legends themselves, etc.)
        # raise on AreGraphicsOverridesAllowed / GetFilters -- skip those.
        continue

if not views_with_filters:
    forms.alert(
        _t(
            "Msg_NoViewsWithFilters",
            "There are no views or view templates with filters assigned.\n"
            "Please add a filter to a view and try again.",
        ),
        exitscript=True,
    )

template_suffix = "  [{0}]".format(_t("Label_Template", "Template"))
view_dict = {}
for v in views_with_filters:
    label = v.Name + (template_suffix if v.IsTemplate else "")
    view_dict[label] = v

selected_labels = forms.SelectFromList.show(
    sorted(view_dict.keys()),
    title=_t("SelectViews_Title", "Select Views / Templates"),
    button_name=_t("SelectViews_Button", "Continue"),
    multiselect=True,
)

if not selected_labels:
    script.exit()

selected_views = [view_dict[lbl] for lbl in selected_labels]

# ---------------------------------------------------------------------------
# TEXT NOTE TYPES
# ---------------------------------------------------------------------------
text_type_names, text_type_by_name = get_text_type_options(doc)
if not text_type_names:
    forms.alert(
        _t("Msg_NoTextTypes", "No Text Note Types found in the project."),
        exitscript=True,
    )

# ---------------------------------------------------------------------------
# READ SETTINGS (configured separately via config.py -- see its
# "Configure" bundle action; sensible defaults apply if never run)
# ---------------------------------------------------------------------------
CONFIG_FILE = appdata.get_universal_data_file(file_id=INI, file_ext="ini")
if not op.exists(CONFIG_FILE):
    open(CONFIG_FILE, "w").close()
configparser = open_config_file(CONFIG_FILE)
try:
    cfg = configparser.get_section(doc.Title)
except AttributeError:
    cfg = configparser.add_section(doc.Title)

selected_text_type_name = cfg.get_option("text_type", text_type_names[0])
text_type = text_type_by_name.get(
    selected_text_type_name, text_type_by_name[text_type_names[0]]
)


# Length settings are stored/entered in whatever unit this project uses
display_unit, is_metric = get_length_unit(doc)
defaults = display_defaults(doc)


def _cfg_length(option_name):
    value = float(cfg.get_option(option_name, defaults[option_name]))
    return DB.UnitUtils.ConvertToInternalUnits(value, display_unit)


row_height = _cfg_length("row_height")
row_spacing = _cfg_length("row_spacing")
swatch_width = _cfg_length("swatch_width")
col_width = _cfg_length("text_column_width")

sort_alpha = bool(
    cfg.get_option("sort_alphabetically", DEFAULTS_BOOL["sort_alphabetically"])
)
open_last = bool(cfg.get_option("open_last_legend", DEFAULTS_BOOL["open_last_legend"]))
track_links = bool(
    cfg.get_option("track_legend_updates", DEFAULTS_BOOL["track_legend_updates"])
)

layout = LegendLayout(text_type.Id, row_height, row_spacing, swatch_width, col_width)
header = [
    _t("Header_FilterName", "Filter Name"),
    _t("Header_Parameter", "Parameter"),
    _t("Header_Value", "Value"),
]


def build_filter_row(src_view, view_filter):
    """Describe one filter of ``src_view`` as a legend row.

    The swatch only gets the filter's overrides when it has any, so
    filters without graphics keep the swatch's plain look.
    """
    info = dissect_parameter_filter(doc, view_filter)
    if info:
        param_name = info.get("parameter_name") or NA_TEXT
        display_val = info.get("display_value")
        if display_val:
            value_text = display_val
        elif info.get("value") is not None:
            value_text = str(info.get("value"))
        else:
            value_text = NA_TEXT
    else:
        param_name = NA_TEXT
        value_text = NA_TEXT

    ogs = src_view.GetFilterOverrides(view_filter.Id)
    overrides = ogs if ogs and ogs_has_overrides(ogs) else None
    return LegendRow([view_filter.Name, param_name, value_text], overrides)


# ---------------------------------------------------------------------------
# LEGEND CREATION
# ---------------------------------------------------------------------------
created_legends = []
new_count = 0
updated_count = 0
existing_view_names = set(v.Name for v in all_views)

base_legend = revit.query.find_first_legend(doc=doc)

if not base_legend:
    forms.alert("At least one Legend view must exist in the model.", exitscript=True)

with revit.TransactionGroup("Create Filter Legend(s)"):
    for src_view in selected_views:
        try:
            with revit.Transaction("Create Filter Legend - {0}".format(src_view.Name)):
                existing_legend = (
                    get_linked_legend(doc, src_view) if track_links else None
                )

                if existing_legend is not None:
                    legend_view = existing_legend
                    tracked_ids = get_managed_elements(legend_view)
                    clear_legend_view(doc, legend_view, tracked_ids)
                else:
                    legend_view = create_legend_view(
                        doc,
                        base_legend,
                        "Legend_Filters_{0}".format(src_view.Name),
                        existing_view_names,
                    )

                filter_elems = revit.query.get_view_filters(src_view)

                if sort_alpha:
                    filter_elems.sort(key=lambda f: f.Name)

                rows = []
                for f in filter_elems:
                    try:
                        rows.append(build_filter_row(src_view, f))
                    except Exception:
                        logger.exception(
                            "Failed to process filter '%s' on view '%s'",
                            f.Name,
                            src_view.Name,
                        )
                        raise

                managed_ids = draw_legend_table(doc, legend_view, layout, header, rows)

                if track_links:
                    save_link(src_view, legend_view)
                    save_managed_elements(legend_view, managed_ids)

                if existing_legend is not None:
                    updated_count += 1
                else:
                    new_count += 1

                created_legends.append(legend_view)

        except Exception:
            logger.exception("Failed to create legend for view '%s'", src_view.Name)

uidoc.RefreshActiveView()

# ---------------------------------------------------------------------------
# WRAP UP
# ---------------------------------------------------------------------------
if created_legends:
    if open_last:
        uidoc.ActiveView = created_legends[-1]
    if new_count and updated_count:
        message = _t(
            "Msg_DoneMixed", "Created {0} legend view(s), updated {1}."
        ).format(new_count, updated_count)
    elif updated_count:
        message = _t("Msg_Updated", "Updated {0} legend view(s).").format(updated_count)
    else:
        message = _t("Msg_Done", "Created {0} legend view(s).").format(new_count)
    forms.alert(message)
else:
    forms.alert(
        _t(
            "Msg_Failed",
            "No legend views could be created. Check the log for details.",
        )
    )
