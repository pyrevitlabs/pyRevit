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

__doc__ = 'Copies the state of desired parameter of the active'\
          ' view to memory. e.g. Visibility Graphics settings or'\
          ' Zoom state. Run it and see how it works.'

__authors__ = ['Gui Talarico', '{{author}}']

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

selected_option = \
    forms.CommandSwitchWindow.show(available_actions.keys(),
        message='Select property to be copied to memory:')
if selected_option:
    action = available_actions[selected_option]()
    action.copy_wrapper()
    script.set_envvar(LAST_ACTION_VAR, selected_option)

# elif selected_option == 'Viewport Placement on Sheet':
#     """
#     Copyright (c) 2016 Gui Talarico

#     CopyPasteViewportPlacemenet
#     Copy and paste the placement of viewports across sheets
#     github.com/gtalarico

#     --------------------------------------------------------
#     pyrevit Notice:
#     pyrevit: repository at https://github.com/eirannejad/pyrevit
#     """
#     originalviewtype = ''

#     selview = selvp = None
#     vpboundaryoffset = 0.01
#     activeSheet = revit.active_view
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

#     def set_tansform_matrix(selvp, selview):
#         # making sure the cropbox is active.
#         cboxactive = selview.CropBoxActive
#         cboxvisible = selview.CropBoxVisible
#         cboxannoparam = selview.get_Parameter(
#             DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE
#             )

#         cboxannostate = cboxannoparam.AsInteger()
#         curviewelements = DB.FilteredElementCollector(revit.doc)\
#                             .OwnedByView(selview.Id)\
#                             .WhereElementIsNotElementType()\
#                             .ToElements()

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
#                         selview.HideElements(List[DB.ElementId](viewspecificelements))
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
#                             )

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
#             forms.alert('Select exactly one viewport.')

#         if isinstance(vport, DB.Viewport):
#             view = revit.doc.GetElement(vport.ViewId)
#             if view is not None and isinstance(view, DB.ViewPlan):
#                 with revit.TransactionGroup('Copy Viewport Location'):
#                     set_tansform_matrix(vport, view)
#                     center = vport.GetBoxCenter()
#                     modelpoint = sheet_to_view_transform(center)
#                     center_pt = Point(center.X, center.Y, center.Z)
#                     model_pt = Point(modelpoint.X, modelpoint.Y, modelpoint.Z)
#                     with open(datafile, 'wb') as fp:
#                         originalviewtype = 'ViewPlan'
#                         pickle.dump(originalviewtype, fp)
#                         pickle.dump(center_pt, fp)
#                         pickle.dump(model_pt, fp)

#             elif view is not None and isinstance(view, DB.ViewDrafting):
#                 center = vport.GetBoxCenter()
#                 center_pt = Point(center.X, center.Y, center.Z)
#                 with open(datafile, 'wb') as fp:
#                     originalviewtype = 'ViewDrafting'
#                     pickle.dump(originalviewtype, fp)
#                     pickle.dump(center_pt, fp)
#             else:
#                 forms.alert('This tool only works with Plan, '
#                             'RCP, and Detail views and viewports.')
#     else:
#         forms.alert('Select exactly one viewport.')
