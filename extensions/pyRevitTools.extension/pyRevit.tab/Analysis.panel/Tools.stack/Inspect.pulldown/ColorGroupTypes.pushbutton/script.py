__title__ = "Color Group types"
__doc__ = """Overrides graphics of groups instances on selected views or active view in such way, so each group type have certain color.
To color many views you should do it at once, so select views in project browser before start.
"""

from pyrevit import script, revit, forms, revit
from Autodesk.Revit.DB import FilteredElementCollector, Group, OverrideGraphicSettings, Color, View

logger = script.get_logger()
doc = __revit__.ActiveUIDocument.Document

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
        cl = FilteredElementCollector(doc, view_id)
    else:
        cl = FilteredElementCollector(doc)
    elements = cl.OfClass(Group).WhereElementIsNotElementType()

    if ids:
        return elements.ToElementIds()
    else:
        return elements.ToElements()


def get_all_on_view(view_id, ids=False):
    elements = FilteredElementCollector(doc, view_id).WhereElementIsNotElementType()
    if ids:
        return elements.ToElementIds()
    else:
        return elements.ToElements()


def collect_groups(views):
    groups_dict = {}
    for v in views:
        groups = get_groups(v.Id)
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
    _colors_1 = map(lambda c: blend_color(c), colors_all[:count_1])
    _colors_n = colors_all[count_1:]
    colors_1 = map(lambda c: Color(c[0], c[1], c[2]), _colors_1)
    colors_n = map(lambda c: Color(c[0], c[1], c[2]), _colors_n)

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
        groups_colors[k] = OverrideGraphicSettings().SetProjectionLineColor(color) \
            .SetProjectionLineWeight(6).SetCutLineColor(color).SetCutLineWeight(6) \
            .SetCutFillColor(color).SetProjectionFillColor(color)

    return groups_colors


def run_view(v, groups_colors):
    all = get_all_on_view(v.Id)
    override_empty = OverrideGraphicSettings()

    for e in all:
        if not e.GroupId or e.GroupId.IntegerValue == -1:
            v.SetElementOverrides(e.Id, override_empty)
        else:
            group_type_id = doc.GetElement(e.GroupId).GetTypeId()
            v.SetElementOverrides(e.Id, groups_colors[group_type_id])


def run(views):
    view_names = map(lambda v: v.Name, views)
    text = "Do you want to override colors on these views:\n" + "\n".join(view_names)

    if not forms.alert(text, yes=True, cancel=True, no=False):
        return

    groups_dict = collect_groups(views)
    logger.debug(groups_dict)
    # prepare colors across selected views
    groups_colors = prepare_colors(groups_dict)
    logger.debug(groups_colors)

    with revit.Transaction(__title__ + ""):
        for v in views:
            # apply overrides to each view
            run_view(v, groups_colors)


sel = revit.get_selection().elements
if len(sel) == 0:
    sel = [revit.active_view]
views = filter(lambda e: issubclass(type(e), View), sel)
if len(views) == 0:
    forms.alert("No views were selected")
else:
    run(views)
