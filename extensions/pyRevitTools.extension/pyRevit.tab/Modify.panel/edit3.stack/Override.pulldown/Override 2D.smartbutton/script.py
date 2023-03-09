from pyrevit import DB, script, revit
from pyrevit import forms
from time import sleep

op = script.get_output()
op.close_others()

doc = revit.doc
active_view = revit.active_view

SLEEP_TIME = 0.75


def set_override(r, g, b):
    src_style = DB.OverrideGraphicSettings()
    # constructing RGB value from list
    color = DB.Color(r, g, b)
    src_style.SetProjectionLineColor(color)
    return src_style


def override_projection_lines(elements_set, r=255, g=0, b=0):
    count = 0
    if len(elements_set) > 0:
        try:
            with revit.Transaction('Line Color'):
                src_style = set_override(r, g, b)
                for element in elements_set:
                    active_view.SetElementOverrides(element.Id, src_style)
                    count += 1
        except Exception as e:
            forms.alert('Error: {}'.format(e), exitscript=True)
        return str(count)
    else:
        forms.alert('No 2D elements in view', exitscript=True)
        return str(count)


def clear_overrides(elements_set):
    if len(elements_set) > 0:
        with revit.Transaction('Line Color'):
            # erase overrides
            src_style = DB.OverrideGraphicSettings().Dispose()
            # get clear graphics without overrides
            src_style = DB.OverrideGraphicSettings()
            for element in elements_set:
                revit.active_view.SetElementOverrides(element.Id, src_style)


def collect_view_specific_elements():
    elements_in_view = revit.query.get_all_elements_in_view(active_view)
    viewspecific_elements = []
    for x in elements_in_view:
        if x.ViewSpecific:
            viewspecific_elements.append(x)
    return viewspecific_elements


if __name__ == '__main__':
    config = script.get_config()
    OVERRIDEN = getattr(config, 'OVERRIDEN')

    if OVERRIDEN == "False":
        with forms.WarningBar(title="Highlight 2D elements in {}".format(active_view.Name)):
            element_count = override_projection_lines(
                collect_view_specific_elements())
            script.toggle_icon(True)
            setattr(config, 'OVERRIDEN', "True")
            sleep(SLEEP_TIME)
    else:
        with forms.WarningBar(title="Clearing 2D elements overrides"):
            clear_overrides(collect_view_specific_elements())
            script.toggle_icon(False)
            setattr(config, 'OVERRIDEN', "False")
            sleep(SLEEP_TIME)
