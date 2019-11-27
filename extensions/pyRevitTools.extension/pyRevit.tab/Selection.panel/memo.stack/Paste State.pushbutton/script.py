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

__doc__ = 'Applies the copied state to the active view. '\
          'This works in conjunction with the Copy State tool.'

logger = script.get_logger()

LAST_ACTION_VAR = "COPYPASTESTATE"

available_actions = {}
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
    with revit.Transaction('test'):
        action.paste_wrapper()


# elif selected_switch == 'Viewport Placement on Sheet':
#     """
#     Copyright (c) 2016 Gui Talarico

#     CopyPasteViewportPlacemenet
#     Copy and paste the placement of viewports across sheets
#     github.com/gtalarico

#     --------------------------------------------------------
#     pyrevit Notice:
#     pyrevit: repository at https://github.com/eirannejad/pyrevit
#     """
#     PINAFTERSET = False
#     originalviewtype = ''

#     selview = selvp = None
#     vpboundaryoffset = 0.01
#     activeSheet = revit.uidoc.ActiveGraphicalView
#     transmatrix = TransformationMatrix()
#     revtransmatrix = TransformationMatrix()

#     def sheet_to_view_transform(sheetcoord):
#         global transmatrix
#         newx = \
#             transmatrix.destmin.X \
#             + (((sheetcoord.X - transmatrix.sourcemin.X)
#                 * (transmatrix.destmax.X - transmatrix.destmin.X))
#                / (transmatrix.sourcemax.X - transmatrix.sourcemin.X))

#         newy = \
#             transmatrix.destmin.Y \
#             + (((sheetcoord.Y - transmatrix.sourcemin.Y)
#                 * (transmatrix.destmax.Y - transmatrix.destmin.Y))
#                / (transmatrix.sourcemax.Y - transmatrix.sourcemin.Y))

#         return DB.XYZ(newx, newy, 0.0)

#     def view_to_sheet_transform(modelcoord):
#         global revtransmatrix
#         newx = \
#             revtransmatrix.destmin.X \
#             + (((modelcoord.X - revtransmatrix.sourcemin.X)
#                 * (revtransmatrix.destmax.X - revtransmatrix.destmin.X))
#                / (revtransmatrix.sourcemax.X - revtransmatrix.sourcemin.X))

#         newy = \
#             revtransmatrix.destmin.Y \
#             + (((modelcoord.Y - revtransmatrix.sourcemin.Y)
#                 * (revtransmatrix.destmax.Y - revtransmatrix.destmin.Y))
#                / (revtransmatrix.sourcemax.Y - revtransmatrix.sourcemin.Y))

#         return DB.XYZ(newx, newy, 0.0)

#     def set_tansform_matrix(selvp, selview):
#         # making sure the cropbox is active.
#         cboxactive = selview.CropBoxActive
#         cboxvisible = selview.CropBoxVisible
#         cboxannoparam = selview.get_Parameter(
#             DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE
#         )
#         cboxannostate = cboxannoparam.AsInteger()
#         curviewelements = \
#             DB.FilteredElementCollector(revit.doc)\
#               .OwnedByView(selview.Id)\
#               .WhereElementIsNotElementType()\
#               .ToElements()

#         viewspecificelements = []
#         for el in curviewelements:
#             if el.ViewSpecific \
#                     and not el.IsHidden(selview) \
#                     and el.CanBeHidden(selview) \
#                     and el.Category is not None:
#                 viewspecificelements.append(el.Id)

#         basepoints = DB.FilteredElementCollector(revit.doc)\
#                        .OfClass(DB.BasePoint)\
#                        .WhereElementIsNotElementType()\
#                        .ToElements()

#         excludecategories = ['Survey Point',
#                              'Project Base Point']
#         for el in basepoints:
#             if el.Category and el.Category.Name in excludecategories:
#                 viewspecificelements.append(el.Id)

#         with revit.TransactionGroup('Activate & Read Cropbox Boundary'):
#             with revit.Transaction('Hiding all 2d elements'):
#                 if viewspecificelements:
#                     try:
#                         selview.HideElements(
#                             List[DB.ElementId](viewspecificelements))
#                     except Exception as e:
#                         logger.debug(e)

#             with revit.Transaction('Activate & Read Cropbox Boundary'):
#                 selview.CropBoxActive = True
#                 selview.CropBoxVisible = False
#                 cboxannoparam.Set(0)

#                 # get view min max points in modelUCS.
#                 modelucsx = []
#                 modelucsy = []
#                 crsm = selview.GetCropRegionShapeManager()

#                 cllist = crsm.GetCropShape()
#                 if len(cllist) == 1:
#                     cl = cllist[0]
#                     for l in cl:
#                         modelucsx.append(l.GetEndPoint(0).X)
#                         modelucsy.append(l.GetEndPoint(0).Y)
#                     cropmin = DB.XYZ(min(modelucsx), min(modelucsy), 0.0)
#                     cropmax = DB.XYZ(max(modelucsx), max(modelucsy), 0.0)

#                     # get vp min max points in sheetUCS
#                     ol = selvp.GetBoxOutline()
#                     vptempmin = ol.MinimumPoint
#                     vpmin = DB.XYZ(vptempmin.X + vpboundaryoffset,
#                                    vptempmin.Y + vpboundaryoffset, 0.0)
#                     vptempmax = ol.MaximumPoint
#                     vpmax = DB.XYZ(vptempmax.X - vpboundaryoffset,
#                                    vptempmax.Y - vpboundaryoffset, 0.0)

#                     transmatrix.sourcemin = vpmin
#                     transmatrix.sourcemax = vpmax
#                     transmatrix.destmin = cropmin
#                     transmatrix.destmax = cropmax

#                     revtransmatrix.sourcemin = cropmin
#                     revtransmatrix.sourcemax = cropmax
#                     revtransmatrix.destmin = vpmin
#                     revtransmatrix.destmax = vpmax

#                     selview.CropBoxActive = cboxactive
#                     selview.CropBoxVisible = cboxvisible
#                     cboxannoparam.Set(cboxannostate)

#                     if viewspecificelements:
#                         selview.UnhideElements(
#                             List[DB.ElementId](viewspecificelements)
#                         )

#     datafile = \
#         script.get_document_data_file(file_id='SaveViewportLocation',
#                                       file_ext='pym',
#                                       add_cmd_name=False)

#     selected_ids = revit.get_selection().element_ids

#     if len(selected_ids) == 1:
#         vport_id = selected_ids[0]
#         try:
#             vport = revit.doc.GetElement(vport_id)
#         except Exception:
#             DB.TaskDialog.Show('pyrevit',
#                                'Select exactly one viewport.')

#         if isinstance(vport, DB.Viewport):
#             view = revit.doc.GetElement(vport.ViewId)
#             if view is not None and isinstance(view, DB.ViewPlan):
#                 with revit.TransactionGroup('Paste Viewport Location'):
#                     set_tansform_matrix(vport, view)
#                     try:
#                         with open(datafile, 'rb') as fp:
#                             originalviewtype = pickle.load(fp)
#                             if originalviewtype == 'ViewPlan':
#                                 savedcen_pt = pickle.load(fp)
#                                 savedmdl_pt = pickle.load(fp)
#                             else:
#                                 raise OriginalIsViewDrafting
#                     except IOError:
#                         forms.alert('Could not find saved viewport '
#                                     'placement.\n'
#                                     'Copy a Viewport Placement first.')
#                     except OriginalIsViewDrafting:
#                         forms.alert('Viewport placement info is from a '
#                                     'drafting view and can not '
#                                     'be applied here.')
#                     else:
#                         savedcenter_pt = DB.XYZ(savedcen_pt.x,
#                                                 savedcen_pt.y,
#                                                 savedcen_pt.z)
#                         savedmodel_pt = DB.XYZ(savedmdl_pt.x,
#                                                savedmdl_pt.y,
#                                                savedmdl_pt.z)
#                         with revit.Transaction('Apply Viewport Placement'):
#                             center = vport.GetBoxCenter()
#                             centerdiff = \
#                                 view_to_sheet_transform(savedmodel_pt) - center
#                             vport.SetBoxCenter(savedcenter_pt - centerdiff)
#                             if PINAFTERSET:
#                                 vport.Pinned = True

#             elif view is not None and isinstance(view, DB.ViewDrafting):
#                 try:
#                     with open(datafile, 'rb') as fp:
#                         originalviewtype = pickle.load(fp)
#                         if originalviewtype == 'ViewDrafting':
#                             savedcen_pt = pickle.load(fp)
#                         else:
#                             raise OriginalIsViewPlan
#                 except IOError:
#                     forms.alert('Could not find saved viewport '
#                                 'placement.\n'
#                                 'Copy a Viewport Placement first.')
#                 except OriginalIsViewPlan:
#                     forms.alert('Viewport placement info is from '
#                                 'a model view and can not be '
#                                 'applied here.')
#                 else:
#                     savedcenter_pt = DB.XYZ(savedcen_pt.x,
#                                             savedcen_pt.y,
#                                             savedcen_pt.z)
#                     with revit.Transaction('Apply Viewport Placement'):
#                         vport.SetBoxCenter(savedcenter_pt)
#                         if PINAFTERSET:
#                             vport.Pinned = True
#             else:
#                 forms.alert('This tool only works with Plan, '
#                             'RCP, and Detail views and viewports.')
#     else:
#         forms.alert('Select exactly one viewport.')
