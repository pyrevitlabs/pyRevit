# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
import os
import os.path as op
import pickle
import math
import inspect
from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script
import copy_paste_state_actions
import viewport_placement_utils as vpu
__doc__ = 'Applies the copied state to the active view. '\
          'This works in conjunction with the Copy State tool.'

logger = script.get_logger()

LAST_ACTION_VAR = "COPYPASTESTATE"

ALIGNMENT_CENTER = 'Center'
ALIGNMENT_CROPBOX = 'Crop Box'
ALIGNMENT_BASEPOINT = 'Project Base Point'


@copy_paste_state_actions.copy_paste_action
class ViewportPlacement(copy_paste_state_actions.CopyPasteStateAction):
    name = 'Viewport Placement on Sheet'

    def paste(self, datafile):
        viewport = vpu.select_viewport()

        view = revit.doc.GetElement(viewport.ViewId)
        saved_alignment = datafile.load()

        saved_center = datafile.load()
        title_block_pt = vpu.get_title_block_placement_by_vp(viewport)

        crop_region_current = None
        cropbox_values_current = None
        hidden_elements = None

        with revit.TransactionGroup('Paste Viewport Location'):
            if saved_alignment == ALIGNMENT_BASEPOINT or view.CropBoxActive:
                with revit.Transaction('Temporary settings'):
                    if saved_alignment == ALIGNMENT_BASEPOINT:
                        crop_region_current = vpu.get_crop_region(view)
                        vpu.set_crop_region(view, vpu.zero_cropbox(view))
                    cropbox_values_current = vpu.activate_cropbox(view)
                    hidden_elements = vpu.hide_all_elements(view)

            with revit.Transaction('Apply Viewport Placement'):
                if saved_alignment == ALIGNMENT_CROPBOX:
                    pass
                else:
                    viewport.SetBoxCenter(saved_center + title_block_pt)

            if crop_region_current:
                with revit.Transaction('Recover crop region form'):
                    vpu.set_crop_region(view, crop_region_current)
            if cropbox_values_current:
                with revit.Transaction('Recover crop region values'):
                    vpu.recover_cropbox(view, cropbox_values_current)
            if hidden_elements:
                with revit.Transaction('Recover hidden elements'):
                    vpu.unhide_all_elements(view, hidden_elements)

        
# main logic

available_actions = {'Viewport Placement on Sheet': ViewportPlacement}

for mem in inspect.getmembers(copy_paste_state_actions):
    moduleobject = mem[1]
    if inspect.isclass(moduleobject) \
            and hasattr(moduleobject, 'is_copy_paste_action'):
        if hasattr(moduleobject, 'validate_context') \
                and not moduleobject.validate_context():
            available_actions[moduleobject.name] = moduleobject
# read last saved action from env var
last_action = script.get_envvar(LAST_ACTION_VAR)
if not last_action \
        or __shiftclick__ \
        or last_action not in available_actions.keys():
    selected_option = \
        forms.CommandSwitchWindow.show(
            available_actions.keys(),
            message='Select property to be copied to memory:')
else:
    selected_option = last_action

if selected_option:
    action = available_actions[selected_option]()
    action.paste_wrapper()
