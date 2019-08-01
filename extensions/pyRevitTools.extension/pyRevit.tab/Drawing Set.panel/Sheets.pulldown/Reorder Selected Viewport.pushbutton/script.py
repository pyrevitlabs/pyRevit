"""Reorders the selected viewport on current sheet."""

from collections import namedtuple

from pyrevit import revit, DB
from pyrevit import forms


ViewportConfig = namedtuple('ViewportConfig', ['box_center',
                                               'type_id',
                                               'view_id'])


def get_selected_viewports():
    selection = revit.get_selection()
    return [x for x in selection if isinstance(x, DB.Viewport)]


def get_nonselected_viewports(sheet):
    svps = get_selected_viewports()
    svp_ids = [x.Id for x in svps]
    if isinstance(sheet, DB.ViewSheet):
        vps = sheet.GetAllViewports()
        if svp_ids:
            return [revit.doc.GetElement(x) for x in vps if x not in svp_ids]

    return []


def capture_vp_config(viewport):
    return ViewportConfig(viewport.GetBoxCenter(),
                          viewport.GetTypeId(),
                          viewport.ViewId)


def bring_to_front(sheet, vp_list):
    with revit.Transaction('Reorder Viewports'):
        for vp in vp_list:
            config = capture_vp_config(vp)
            sheet.DeleteViewport(vp)
            new_vp = DB.Viewport.Create(revit.doc,
                                        sheet.Id,
                                        config.view_id,
                                        config.box_center)
            new_vp.ChangeTypeId(config.type_id)


selected_vps = get_selected_viewports()

if selected_vps:
    selected_option = \
        forms.CommandSwitchWindow.show(
            ['Bring to Front', 'Send to Back'],
            message='Select reordering method:'
        )


    if selected_option:
        if selected_option == 'Bring to Front':
            viewports = get_selected_viewports()
        elif selected_option == 'Send to Back':
            viewports = get_nonselected_viewports(revit.active_view)

        bring_to_front(revit.active_view, viewports)
else:
    forms.alert('Select a Viewport first.')
