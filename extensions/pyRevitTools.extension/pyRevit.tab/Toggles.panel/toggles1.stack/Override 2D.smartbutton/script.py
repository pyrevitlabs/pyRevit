from time import sleep
from pyrevit import DB, script, revit
from pyrevit import forms
from pyrevit.framework import List

op = script.get_output()
op.close_others()

config = script.get_config('twoDhighlight')

doc = revit.doc
active_view = revit.active_view

SLEEP_TIME = 0.8

def set_config(state, config):
    config.twoDhighlight = state
    script.toggle_icon(state)
    script.save_config()


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    off_icon = script_cmp.get_bundle_file('off.png')
    ui_button_cmp.set_icon(off_icon)


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
            active_view.SetElementOverrides(element.Id, src_style)


def collect_view_specific_elements():
    elements_in_view = revit.query.get_all_elements_in_view(active_view)
    viewspecific_elements = []
    for x in elements_in_view:
        if x.ViewSpecific:
            viewspecific_elements.append(x)
    elements_id_set = List[DB.ElementId](i.Id for i in viewspecific_elements)
    return viewspecific_elements, elements_id_set


@revit.carryout('Disable temporary isolation')
def disable_temp_isolation(view=active_view):
    if active_view.ViewType == DB.ViewType.DrawingSheet and view.IsTemporaryHideIsolateActive == True:
        view.DisableTemporaryViewMode(DB.TemporaryViewMode.TemporaryHideIsolate)
    else:
        view.DisableTemporaryViewMode(DB.TemporaryViewMode.TemporaryViewProperties)


@revit.carryout('Enable temporary isolation')
def enable_temp_isolation(view=active_view):
    if view.ViewType == DB.ViewType.DrawingSheet and view.IsTemporaryHideIsolateActive() == False:
        view.DisableTemporaryViewMode(DB.TemporaryViewMode.TemporaryHideIsolate)
    else:
        view.EnableTemporaryViewPropertiesMode(view.Id)


if __name__ == '__main__':
    elements_set, elements_id_set = collect_view_specific_elements()
    overrides = active_view.GetElementOverrides(elements_set[0].Id).ProjectionLineColor
    with revit.TransactionGroup('Override 2D elements'):
        if overrides.IsValid:
            if overrides.Red == 255 and overrides.Green == 0 and overrides.Blue == 0:
                with forms.WarningBar(title="Clearing 2D elements overrides"):
                    disable_temp_isolation()
                    clear_overrides(elements_set)
                    set_config(False, config)
                    sleep(SLEEP_TIME)
        else:
            with forms.WarningBar(title="Highlight 2D elements in {}".format(active_view.Name)):
                enable_temp_isolation()
                element_count = override_projection_lines(elements_set)
                set_config(True, config)
                sleep(SLEEP_TIME)
