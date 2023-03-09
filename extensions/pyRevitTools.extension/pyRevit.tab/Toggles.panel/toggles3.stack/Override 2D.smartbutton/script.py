from pyrevit import DB, script, revit
from pyrevit import forms
from time import sleep
from pyrevit.coreutils.ribbon import ICON_MEDIUM
from pyrevit.userconfig import user_config

op = script.get_output()
op.close_others()

doc = revit.doc
active_view = revit.active_view

SLEEP_TIME = 0.8


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    button_icon = script_cmp.get_bundle_file(
        'on.png' if user_config.colorize_docs else 'off.png'
    )
    ui_button_cmp.set_icon(button_icon, icon_size=ICON_MEDIUM)


def set_override(r=255, g=0, b=0):
    src_style = DB.OverrideGraphicSettings()
    # constructing RGB value from list
    color = DB.Color(r, g, b)
    src_style.SetProjectionLineColor(color)
    return src_style


@revit.carryout('Override 2D elements')
def override_projection_lines(elements_set):
    count = 0
    if len(elements_set) > 0:
        try:
            src_style = set_override()
            for element in elements_set:
                active_view.SetElementOverrides(element.Id, src_style)
                count += 1
        except Exception as e:
            forms.alert('Error: {}'.format(e), exitscript=True)
        return str(count)
    else:
        forms.alert('No 2D elements in view', exitscript=True)
        return str(count)


@revit.carryout('Clear overrides')
def clear_overrides(elements_set):
    if len(elements_set) > 0:
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
    elements_set = collect_view_specific_elements()
    overrides = revit.active_view.GetElementOverrides(elements_set[0].Id).ProjectionLineColor
    try:
        if overrides.Red == 255:
            with forms.WarningBar(title="Clearing 2D elements overrides"):
                clear_overrides(collect_view_specific_elements())
                script.toggle_icon(False)
                sleep(SLEEP_TIME)
    except:
        with forms.WarningBar(title="Highlight 2D elements in {}".format(active_view.Name)):
            element_count = override_projection_lines(elements_set)
            script.toggle_icon(True)
            sleep(SLEEP_TIME)
