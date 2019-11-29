# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
import os
import os.path as op
import pickle
import inspect
from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script
import copy_paste_state_actions
import viewport_placement_utils as vpu

__doc__ = 'Copies the state of desired parameter of the active'\
          ' view to memory. e.g. Visibility Graphics settings or'\
          ' Zoom state. Run it and see how it works.'

__authors__ = ['Gui Talarico', '{{author}}']

logger = script.get_logger()

LAST_ACTION_VAR = "COPYPASTESTATE"

ALIGNMENT_CENTER = 'Center'
ALIGNMENT_CROPBOX = 'Crop Box'
ALIGNMENT_BASEPOINT = 'Project Base Point'


@copy_paste_state_actions.copy_paste_action
class ViewportPlacement(copy_paste_state_actions.CopyPasteStateAction):
    name = 'Viewport Placement on Sheet'

    def copy(self, datafile):
        viewport = vpu.select_viewport()
        view = revit.doc.GetElement(viewport.ViewId)

        title_block_pt = vpu.get_title_block_placement_by_vp(viewport)

        if view.ViewType in [DB.ViewType.DraftingView, DB.ViewType.Legend]:
            alignment = ALIGNMENT_CENTER
        else:
            alignment = forms.CommandSwitchWindow.show(
                [ALIGNMENT_CENTER, ALIGNMENT_CROPBOX, ALIGNMENT_BASEPOINT],
                message='Select alignment')

        if not alignment:
            return

        datafile.dump(alignment)

        with revit.DryTransaction('Activate & Read Cropbox, Copy Center'):
            if alignment == ALIGNMENT_BASEPOINT:
                vpu.set_crop_region(view, vpu.zero_cropbox(view))
            # use cropbox as alignment if it active
            if alignment == ALIGNMENT_BASEPOINT or view.CropBoxActive:
                vpu.activate_cropbox(view)
                vpu.hide_all_elements(view)
                revit.doc.Regenerate()
            center = viewport.GetBoxCenter() - title_block_pt

        datafile.dump(center)
        if alignment == ALIGNMENT_CROPBOX:
            # TODO save left top corner offset
            pass

# main logic


available_actions = {'Viewport Placement on Sheet': ViewportPlacement}
for mem in inspect.getmembers(copy_paste_state_actions):
    moduleobject = mem[1]
    if inspect.isclass(moduleobject) \
            and hasattr(moduleobject, 'is_copy_paste_action'):
        if hasattr(moduleobject, 'validate_context') \
                and not moduleobject.validate_context():
            available_actions[moduleobject.name] = moduleobject

selected_option = \
    forms.CommandSwitchWindow.show(available_actions.keys(),
                                   message='Select property to be copied to memory:')
if selected_option:
    action = available_actions[selected_option]()
    action.copy_wrapper()
    script.set_envvar(LAST_ACTION_VAR, selected_option)
