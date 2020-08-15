"""Overrides graphics of groups instances on selected views or
active view in such way that all instances of the same group type
are marked with the same color. You can select multiple views before
running the tool to colorize the group types in all of them at once

Note:
Groups with only 1 instance on views will be colored in gray
"""
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import itertools
from collections import defaultdict

from pyrevit import HOST_APP
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script


__title__ = "Colorize Group Types"


logger = script.get_logger()


def _arange_int(start, end, count):
    multipliers = [float(x) / (count - 1) for x in range(count)]
    for m in multipliers:
        yield int((end - start) * m + start)


def generate_colors(n):
    """Generate a seried of colors to be used for colorizing group types"""
    i = 3
    result_colors = [
        col
        for col in itertools.product([0, 255], repeat=3)
        if sum(col) > 0 and sum(col) < 255 * 3
    ]
    # iterate to produce colors closest to clean one
    while len(result_colors) < n:
        channel_values = list(_arange_int(0, 255, i))
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


def get_groups(view=None, ids=False):
    """Get group elements in given view"""
    if view:
        cl = DB.FilteredElementCollector(revit.doc, view.Id)
    else:
        cl = DB.FilteredElementCollector(revit.doc)
    elements = cl.OfClass(DB.Group).WhereElementIsNotElementType()

    if ids:
        return elements.ToElementIds()
    else:
        return elements.ToElements()


def get_all_view_elements(view, ids=False):
    """Get all elements visible in a view"""
    elements = DB.FilteredElementCollector(
        revit.doc, view.Id
    ).WhereElementIsNotElementType()
    if ids:
        return elements.ToElementIds()
    else:
        return elements.ToElements()


def collect_groups(views):
    """Collect group elements in given view

    Returns:
        dict[DB.ElementId, DB.ElementId]: dict of group {type_id: element_id}
    """
    groups_dict = defaultdict(set)
    for view in views:
        groups = get_groups(view)
        for g in groups:
            groups_dict[g.GetTypeId()].add(g.Id)
    return groups_dict


def filter_group_types(groups_dict):
    """Create a dict of group types

    Returns:
        dict[DB.ElementId, DB.ElementId]: dict of group {type_id: element_id}
    """
    keys_map = {
        "%s (%d instances)"
        % (
            revit.query.get_name(revit.doc.GetElement(gt_id)),
            len(groups_dict[gt_id]),
        ): gt_id
        for gt_id in groups_dict.keys()
    }
    picked_group_types = forms.SelectFromList.show(
        sorted(keys_map.keys()),
        multiselect=True,
        button_name="Select Group Types",
    )
    if not picked_group_types:
        script.exit()
    picked_group_type_ids = [
        keys_map[group_name] for group_name in picked_group_types
    ]
    return {k: v for k, v in groups_dict.items() if k in picked_group_type_ids}


def prepare_colors(groups_dict):
    """Prepare a list of vg overrides for each group type"""
    groups_colors = {}
    count = sum(
        [len(groups) for groups in groups_dict.values() if len(groups) > 1]
    )
    colors = [DB.Color(x[0], x[1], x[2]) for x in generate_colors(count)]
    color_gray = DB.Color(128, 128, 128)
    j = 0
    for gt_id in groups_dict.keys():
        if len(groups_dict[gt_id]) == 1:
            color = color_gray
        else:
            color = colors[j]
            j += 1
        if HOST_APP.is_newer_than(2019, or_equal=True):
            groups_colors[gt_id] = (
                DB.OverrideGraphicSettings()
                .SetProjectionLineColor(color)
                .SetProjectionLineWeight(6)
                .SetSurfaceBackgroundPatternColor(color)
                .SetCutLineColor(color)
                .SetCutLineWeight(6)
                .SetCutBackgroundPatternColor(color)
            )
        else:
            groups_colors[gt_id] = (
                DB.OverrideGraphicSettings()
                .SetProjectionLineColor(color)
                .SetProjectionLineWeight(6)
                .SetProjectionFillColor(color)
                .SetCutLineColor(color)
                .SetCutLineWeight(6)
                .SetCutFillColor(color)
            )

    return groups_colors


def colorize_grouptypes_in_view(view, groups_colors):
    """Colorize groups by type in given view"""
    override_empty = DB.OverrideGraphicSettings()
    for element in get_all_view_elements(view):
        element_override = override_empty
        if element.GroupId and element.GroupId != DB.ElementId.InvalidElementId:
            group_type_id = revit.doc.GetElement(element.GroupId).GetTypeId()
            if group_type_id and group_type_id in groups_colors.keys():
                element_override = groups_colors[group_type_id]
        view.SetElementOverrides(element.Id, element_override)


def colorize_grouptypes_in_views(views):
    """Colorize groups by type in given views"""
    view_names = [x.Name for x in views]
    text = (
        "Do you want to colorize groups by type on these views:\n\n"
        + "\n".join(view_names)
    )

    if not forms.alert(text, yes=True, cancel=True, no=False):
        return

    groups_dict = collect_groups(views)
    groups_dict = filter_group_types(groups_dict)
    logger.debug(groups_dict)
    # prepare colors across selected views
    groups_colors = prepare_colors(groups_dict)
    logger.debug(groups_colors)

    with revit.Transaction(__title__):
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
