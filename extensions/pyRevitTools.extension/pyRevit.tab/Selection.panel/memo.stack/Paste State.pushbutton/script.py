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

@copy_paste_state_actions.copy_paste_action
class ViewportPlacement(copy_paste_state_actions.CopyPasteStateAction):
    name = 'Viewport Placement on Sheet'

    def paste(self, datafile):
        """
        Copyright (c) 2016 Gui Talarico
        CopyPasteViewportPlacement
        Copy and paste the placement of viewports across sheets
        github.com/gtalarico
        --------------------------------------------------------
        pyrevit Notice:
        pyrevit: repository at https://github.com/eirannejad/pyrevit
        """
        vport = vpu.select_viewport()

        originalviewtype = ''
                                        
        view = revit.doc.GetElement(vport.ViewId)
        if isinstance(view, DB.ViewPlan):
            try:
                originalviewtype = datafile.load()
                if originalviewtype == 'ViewPlan':
                    savedcen_pt = datafile.load()
                    savedmdl_pt = datafile.load()
                    crop_region_saved = datafile.load()
                else:
                    raise OriginalIsViewDrafting
            except IOError:
                forms.alert('Could not find saved viewport '
                            'placement.\n'
                            'Copy a Viewport Placement first.')
            except OriginalIsViewDrafting:
                forms.alert('Viewport placement info is from a '
                            'drafting view and can not '
                            'be applied here.')
            else:
                with revit.TransactionGroup('Paste Viewport Location'):
                    crop_active_saved = view.CropBoxActive
                    if crop_region_saved:
                        cboxannoparam = view.get_Parameter(
                                DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
                        cropbox_active_current = view.CropBoxActive
                        cropbox_visible_current = view.CropBoxVisible
                        cropbox_annotations_current = cboxannoparam.AsInteger()
                        with revit.Transaction('Temporary set saved crop region'):
                            view.CropBoxActive = True
                            crop_region_relevant = vpu.get_crop_region(view)
                            vpu.set_crop_region(view, crop_region_saved)
                            # making sure the cropbox is active.
                            view.CropBoxActive = True
                            view.CropBoxVisible = False
                            
                            if not cboxannoparam.IsReadOnly:
                                cboxannoparam.Set(0)
                    else:
                        crop_region_relevant = None
                        

                    with revit.DryTransaction('Activate & Read Cropbox Boundary'):
                        revtransmatrix = vpu.set_tansform_matrix(vport, view, reverse=True)
                    title_block_pt = vpu.get_title_block_placement_by_vp(vport)
                    savedcenter_pt = savedcen_pt + title_block_pt

                    with revit.Transaction('Apply Viewport Placement'):
                        # target vp center (sheet UCS)
                        center = vport.GetBoxCenter()
                        # source vp center (sheet UCS) - target center
                        centerdiff = vpu.transform_by_matrix(savedmdl_pt, revtransmatrix) - center
                        vport.SetBoxCenter(savedcenter_pt)

                    if crop_region_relevant:
                        with revit.Transaction('Recover crop region'):
                            view.CropBoxActive = crop_active_saved
                            vpu.set_crop_region(view, crop_region_relevant)
                            view.CropBoxActive = cropbox_active_current
                            view.CropBoxVisible = cropbox_visible_current
                            if not cboxannoparam.IsReadOnly:
                                cboxannoparam.Set(cropbox_annotations_current)

        elif isinstance(view, DB.ViewDrafting):
            try:
                originalviewtype = datafile.load()
                if originalviewtype == 'ViewDrafting':
                    savedcen_pt = datafile.load()
                else:
                    raise OriginalIsViewPlan
            except IOError:
                forms.alert('Could not find saved viewport '
                            'placement.\n'
                            'Copy a Viewport Placement first.')
            except OriginalIsViewPlan:
                forms.alert('Viewport placement info is from '
                            'a model view and can not be '
                            'applied here.')
            else:
                with revit.Transaction('Apply Viewport Placement'):
                    vport.SetBoxCenter(savedcen_pt)

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
