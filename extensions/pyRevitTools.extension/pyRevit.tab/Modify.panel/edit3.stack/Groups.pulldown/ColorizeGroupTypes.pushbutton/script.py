"""Overrides graphics of groups instances on selected views or
active view in such way, so each group type have certain color.
To color many views you should do it at once,
so select views in project browser before start.

Groups with only 1 instance on views will be colored in gray.
"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script
import itertools

__title__ = "Colorize Group Types"

logger = script.get_logger()

def arange_int(start, end, count):
    multipliers = [float(x) / (count - 1) for x in range(count)]
    for m in multipliers:
        yield int((end - start) * m + start)

def generate_colors(n):
    i = 3
    result_colors = [col for col in itertools.product([0, 255], repeat=3)
                     if sum(col) > 0 and sum(col) < 255 * 3]
    # iterate to produce colors closest to clean one
    while len(result_colors) < n:
        channel_values = list(arange_int(0, 255, i))
        # first add colors closest to clean one
        for col in itertools.permutations(channel_values, 3):
            if col not in result_colors:
                result_colors.append(col)
        # in the second stem add more mixed colors
        for col in itertools.product(channel_values, repeat=3):
            # excluding too dark and too bright
            if col not in result_colors and sum(col) > 20 and sum(col) < 600:
                result_colors.append(col)
        # repeat with more tones if necessary
        i += 1
    return list(result_colors)[:n]


def get_groups(view_id=None, ids=False):
    if view_id:
        cl = DB.FilteredElementCollector(revit.doc, view_id)
    else:
        cl = DB.FilteredElementCollector(revit.doc)
    elements = cl.OfClass(DB.Group).WhereElementIsNotElementType()

    if ids:
        return elements.ToElementIds()
    else:
        return elements.ToElements()


def get_all_view_elements(view_id, ids=False):
    elements = \
        DB.FilteredElementCollector(revit.doc, view_id).WhereElementIsNotElementType()
    if ids:
        return elements.ToElementIds()
    else:
        return elements.ToElements()


def collect_groups(views):
    groups_dict = {}
    for view in views:
        groups = get_groups(view.Id)
        for g in groups:
            gt_id = g.GetTypeId()
            if gt_id not in groups_dict:
                groups_dict[gt_id] = set()
            groups_dict[gt_id].add(g.Id)
    return groups_dict

def filter_group_types(groups_dict):
    keys_map = {"%s <%d>" % (revit.query.get_name(revit.doc.GetElement(gt_id)),
                                                   len(groups_dict[gt_id])):
                gt_id
                for gt_id in groups_dict.keys()}
    picked_group_types = forms.SelectFromList.show(sorted(keys_map.keys()),
        multiselect=True,
        button_name='Select group types')
    if not picked_group_types:
        forms.alert("Cancelled!", exitscript=True)
    picked_group_type_ids = [keys_map[group_name]
                             for group_name in picked_group_types]
    return {k:v for k,v in groups_dict.items()
            if k in picked_group_type_ids}

def prepare_colors(groups_dict):
    groups_colors = {}
    count = sum([len(groups) for groups in groups_dict.values()
                 if len(groups)>1])
    colors = [DB.Color(x[0], x[1], x[2]) for x in generate_colors(count)]
    color_gray = DB.Color(128, 128, 128)
    j = 0
    for gt_id in groups_dict.keys():
        if len(groups_dict[gt_id]) == 1:
            color = color_gray
        else:
            color = colors[j]
            j += 1
        groups_colors[gt_id] = \
            DB.OverrideGraphicSettings() \
              .SetProjectionLineColor(color) \
              .SetProjectionLineWeight(6) \
              .SetCutLineColor(color) \
              .SetCutLineWeight(6) \
              .SetCutFillColor(color) \
              .SetProjectionFillColor(color)

    return groups_colors


def colorize_grouptypes_in_view(view, groups_colors):
    override_empty = DB.OverrideGraphicSettings()
    for element in get_all_view_elements(view.Id):
        element_override = override_empty
        if element.GroupId and\
                element.GroupId != DB.ElementId.InvalidElementId:
            group_type_id = revit.doc.GetElement(element.GroupId).GetTypeId()
            if group_type_id and group_type_id in groups_colors.keys():
                element_override = groups_colors[group_type_id]
        view.SetElementOverrides(element.Id, element_override)


def colorize_grouptypes_in_views(views):
    view_names = [x.Name for x in views]
    text = \
        "Do you want to override colors on these views:\n" \
        + "\n".join(view_names)

    if not forms.alert(text, yes=True, cancel=True, no=False):
        return

    groups_dict = collect_groups(views)
    groups_dict = filter_group_types(groups_dict)
    logger.debug(groups_dict)
    # prepare colors across selected views
    groups_colors = prepare_colors(groups_dict)
    logger.debug(groups_colors)

    with revit.Transaction(__title__ + ""):
        for view in views:
            # apply overrides to each view
            colorize_grouptypes_in_view(view, groups_colors)


selected_views = revit.get_selection().elements
if not selected_views:
    selected_views = [revit.active_view]

target_views = [v for v in selected_views if isinstance(v, DB.View)]
if not target_views:
    forms.alert("No views were selected")
else:
    colorize_grouptypes_in_views(target_views)
