#pylint: disable=import-error,invalid-name,attribute-defined-outside-init
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

@copy_paste_state_actions.copy_paste_action
class ViewportPlacement(copy_paste_state_actions.CopyPasteStateAction):
    name = 'Viewport Placement on Sheet'

    def copy(self, datafile):
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
            # TODO ask use to choose a mode
            #  if SectionBoxes either None
            #  and CropRegions (and SectionBoxes) are not identical
            #  and ViewNormal are identical
            #  (optional) if difference between CropRegions is too big
            # TODO use LeftTop alignment by default,
            #  choose CropBox alignment (LeftTop, RightTop etc.)
            use_base_point = forms.CommandSwitchWindow.show(
                ['Crop Box','Project Base Point'],
                message='Select alignment'
            ) == 'Project Base Point'
            with revit.DryTransaction('Activate & Read Cropbox Boundary'):
                transmatrix = vpu.set_tansform_matrix(vport, view)
                if use_base_point:
                    crop_region_curves = vpu.get_crop_region(view)
                else:
                    crop_region_curves = None
            with revit.TransactionGroup('Copy Viewport Location'):
                title_block_pt = vpu.get_title_block_placement_by_vp(vport)
                # Vport center on a sheet (sheet UCS)
                center = vport.GetBoxCenter() - title_block_pt
                # Vport center on a sheet (model UCS)
                modelpoint = vpu.transform_by_matrix(center, transmatrix)

                originalviewtype = 'ViewPlan'
                datafile.dump(originalviewtype)
                datafile.dump(center)
                datafile.dump(modelpoint)
                if crop_region_curves:
                    datafile.dump(crop_region_curves)
                else:
                    datafile.dump(None)

        elif isinstance(view, DB.ViewDrafting):
            center = vport.GetBoxCenter()
            originalviewtype = 'ViewDrafting'
            datafile.dump(originalviewtype)
            datafile.dump(center)

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
