"""Overrides graphics of groups instances on selected views or
active view in such way, so each group type have certain color.
To color many views you should do it at once,
so select views in project browser before start.
"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script


__title__ = "Colorize Group Types"

logger = script.get_logger()


def colors(n):
    ret = []
    if not n:
        return ret
    r = int(0 * 256)
    g = int(0.33 * 256)
    b = int(0.66 * 256)
    step = 256 / n
    for i in range(n):
        r += step
        g += step
        b += step
        r = int(r) % 256
        g = int(g) % 256
        b = int(b) % 256
        ret.append((r, g, b))
    return ret


def blend_color(color, p=0.5):
    r = []
    for ch in color:
        delta = 256 - ch
        r.append(int(ch + delta*p))
    return (r[0], r[1], r[2])


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
            g_type = g.GetTypeId()
            if g_type not in groups_dict:
                groups_dict[g_type] = set()
            groups_dict[g_type].add(g.Id)
    return groups_dict


def prepare_colors(groups_dict):
    groups_colors = {}
    count_1 = 0
    count_n = 0
    for k in groups_dict.keys():
        if len(groups_dict[k]) == 1:
            # one instance of a group
            count_1 += 1
        else:
            # several instances
            count_n += 1

    colors_all = colors(count_1 + count_n)
    _colors_1 = [blend_color(x) for x in colors_all[:count_1]]
    _colors_n = colors_all[count_1:]
    colors_1 = [DB.Color(x[0], x[1], x[2]) for x in _colors_1]
    colors_n = [DB.Color(x[0], x[1], x[2]) for x in _colors_n]

    i = 0
    j = 0
    for k in groups_dict.keys():
        if len(groups_dict[k]) == 1:
            logger.debug("len(groups_dict[k]) == 1")
            color = colors_1[i]
            i += 1
        else:
            color = colors_n[j]
            j += 1
        groups_colors[k] = \
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
        if not element.GroupId \
                or element.GroupId == DB.ElementId.InvalidElementId:
            view.SetElementOverrides(element.Id, override_empty)
        else:
            group_type_id = revit.doc.GetElement(element.GroupId).GetTypeId()
            view.SetElementOverrides(element.Id, groups_colors[group_type_id])


def colorize_grouptypes_in_views(views):
    view_names = [x.Name for x in views]
    text = \
        "Do you want to override colors on these views:\n" \
        + "\n".join(view_names)

    if not forms.alert(text, yes=True, cancel=True, no=False):
        return

    groups_dict = collect_groups(views)
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
