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

from pyrevit import revit, forms, script
from pyrevit import DB
from pyrevit.coreutils.configparser import PyRevitConfigParser
from pyrevit.coreutils import appdata

from match.filter_utils import (
    dissect_parameter_filter,
    ogs_has_overrides,
)

from legend_utils import (
    create_legend_row,
    unique_view_name,
)
from legend_config import (
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
CONFIG_FILE = appdata.get_universal_data_file(file_id=INI, file_ext='ini')
if not op.exists(CONFIG_FILE):
    open(CONFIG_FILE, "w").close()
configparser = PyRevitConfigParser(cfg_file_path=CONFIG_FILE)
try:
    cfg = configparser.get_section(doc.Title)
except AttributeError:
    cfg = configparser.add_section(doc.Title)

selected_text_type_name = cfg.get_option("text_type", text_type_names[0])
text_type = text_type_by_name.get(
    selected_text_type_name, text_type_by_name[text_type_names[0]]
)

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

# Column X offsets (relative to swatch's right edge)
COL_NAME_X = swatch_width + col_width * 0.05
COL_PARAM_X = swatch_width + col_width * 1.05
COL_VALUE_X = swatch_width + col_width * 2.05

# ---------------------------------------------------------------------------
# LEGEND CREATION
# ---------------------------------------------------------------------------
created_legends = []
existing_view_names = set(v.Name for v in all_views)

base_legend = revit.query.find_first_legend(doc=doc)

if not base_legend:
    forms.alert("At least one Legend view must exist in the model.", exitscript=True)

with revit.TransactionGroup("Create Filter Legend(s)"):
    for src_view in selected_views:
        try:
            with revit.Transaction("Create Filter Legend - {0}".format(src_view.Name)):
                legend_view = doc.GetElement(
                    base_legend.Duplicate(DB.ViewDuplicateOption.Duplicate)
                )
                legend_view.Scale = 1

                legend_name = unique_view_name(
                    doc,
                    "Legend_Filters_{0}".format(src_view.Name),
                    existing_names=existing_view_names,
                )
                legend_view.Name = legend_name
                existing_view_names.add(legend_name)

                filter_ids = list(src_view.GetFilters())
                filter_elems = []
                for fid in filter_ids:
                    f = doc.GetElement(fid)
                    if f:
                        filter_elems.append(f)

                if sort_alpha:
                    filter_elems.sort(key=lambda f: f.Name)

                y = 0.0

                # -- header row --
                # Row height/next-row offset is measured from the actual
                # created TextNotes' bounding boxes (see create_legend_row),
                # not assumed equal to the configured row_height -- that's
                # what keeps rows from overlapping/misaligning regardless
                # of which TextNoteType/font size a given project uses.
                _, _, header_height = create_legend_row(
                    doc,
                    legend_view,
                    y,
                    text_type.Id,
                    columns=[
                        (COL_NAME_X, _t("Header_FilterName", "Filter Name")),
                        (COL_PARAM_X, _t("Header_Parameter", "Parameter")),
                        (COL_VALUE_X, _t("Header_Value", "Value")),
                    ],
                    min_row_height=row_height,
                )
                y -= header_height + row_spacing

                # -- data rows --
                for f in filter_elems:
                    try:
                        ogs = src_view.GetFilterOverrides(f.Id)

                        info = dissect_parameter_filter(doc, f)
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

                        _, region, row_advance = create_legend_row(
                            doc,
                            legend_view,
                            y,
                            text_type.Id,
                            columns=[
                                (COL_NAME_X, f.Name),
                                (COL_PARAM_X, param_name),
                                (COL_VALUE_X, value_text),
                            ],
                            swatch_col_width=swatch_width,
                            swatch_height=row_height,
                            min_row_height=row_height,
                        )
                        if ogs and region and ogs_has_overrides(ogs):
                            legend_view.SetElementOverrides(region.Id, ogs)

                    except Exception:
                        logger.exception(
                            "Failed to process filter '%s' on view '%s'",
                            f.Name,
                            src_view.Name,
                        )
                        row_advance = row_height

                    y -= row_advance + row_spacing

                created_legends.append(legend_view)

        except Exception:
            logger.exception("Failed to create legend for view '%s'", src_view.Name)

revit.uidoc.RefreshActiveView()

# ---------------------------------------------------------------------------
# WRAP UP
# ---------------------------------------------------------------------------
if created_legends:
    if open_last:
        uidoc.ActiveView = created_legends[-1]
    forms.alert(
        _t("Msg_Done", "Created {0} legend view(s).").format(len(created_legends))
    )
else:
    forms.alert(
        _t(
            "Msg_Failed",
            "No legend views could be created. Check the log for details.",
        )
    )
