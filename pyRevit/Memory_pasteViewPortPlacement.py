"""
Copyright (c) 2016 Gui Talarico

CopyPasteViewportPlacemenet
Copy and paste the placement of viewports across sheets
github.com/gtalarico | gtalarico@gmail.com

--------------------------------------------------------
pyRevit Notice:
pyRevit: repository at https://github.com/eirannejad/pyRevit
"""

__window__.Close()

__doc__ = 'Paste the location of a viewport from memory onto the selected viewport. This relocates the selected ' \
          'to the exact location of the original viewport.'

__author__ = 'Gui Talarico | gtalarico@gmail.com\nEhsan Iran-Nejad | eirannejad@gmail.com'
__version__ = '0.1.0'

import os
import os.path as op
import pickle
from collections import namedtuple

from Autodesk.Revit.DB import TransactionGroup, Transaction, Viewport, ViewPlan, ViewSheet, ViewDrafting, XYZ
from Autodesk.Revit.UI import TaskDialog

PINAFTERSET = False


doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument


class OriginalIsViewDrafting(Exception):
    pass


class OriginalIsViewPlan(Exception):
    pass


class TransformationMatrix:
    def __init__(self):
        self.sourcemin = None
        self.sourcemax = None
        self.destmin = None
        self.destmax = None


Point = namedtuple('Point', ['X', 'Y','Z'])
originalviewtype = ''

selview = selvp = None
vpboundaryoffset = 0.01
activeSheet = uidoc.ActiveGraphicalView
transmatrix = TransformationMatrix()
revtransmatrix = TransformationMatrix()

def sheet_to_view_transform(sheetcoord):
    global transmatrix
    newx = transmatrix.destmin.X + (
        ((sheetcoord.X - transmatrix.sourcemin.X) * (transmatrix.destmax.X - transmatrix.destmin.X)) / (
            transmatrix.sourcemax.X - transmatrix.sourcemin.X))
    newy = transmatrix.destmin.Y + (
        ((sheetcoord.Y - transmatrix.sourcemin.Y) * (transmatrix.destmax.Y - transmatrix.destmin.Y)) / (
            transmatrix.sourcemax.Y - transmatrix.sourcemin.Y))
    return XYZ(newx, newy, 0.0)


def view_to_sheet_transform(modelcoord):
    global revtransmatrix
    newx = revtransmatrix.destmin.X + (
        ((modelcoord.X - revtransmatrix.sourcemin.X) * (revtransmatrix.destmax.X - revtransmatrix.destmin.X)) / (
            revtransmatrix.sourcemax.X - revtransmatrix.sourcemin.X))
    newy = revtransmatrix.destmin.Y + (
        ((modelcoord.Y - revtransmatrix.sourcemin.Y) * (revtransmatrix.destmax.Y - revtransmatrix.destmin.Y)) / (
            revtransmatrix.sourcemax.Y - revtransmatrix.sourcemin.Y))
    return XYZ(newx, newy, 0.0)


def set_tansform_matrix(selvp, selview):
    # making sure the cropbox is active.
    cboxactive = selview.CropBoxActive
    cboxvisible = selview.CropBoxVisible
    with Transaction(doc, 'Activate and Read Cropbox Boundary') as t:
        t.Start()
        selview.CropBoxActive = True
        selview.CropBoxVisible = False

        # get view min max points in modelUCS.
        modelucsx = []
        modelucsy = []
        crsm = selview.GetCropRegionShapeManager()
        cl = crsm.GetCropShape()[0]
        for l in cl:
            modelucsx.append(l.GetEndPoint(0).X)
            modelucsy.append(l.GetEndPoint(0).Y)
        cropmin = XYZ(min(modelucsx), min(modelucsy), 0.0)
        cropmax = XYZ(max(modelucsx), max(modelucsy), 0.0)
        
        # get vp min max points in sheetUCS
        ol = selvp.GetBoxOutline()
        vptempmin = ol.MinimumPoint
        vpmin = XYZ(vptempmin.X + vpboundaryoffset, vptempmin.Y + vpboundaryoffset, 0.0)
        vptempmax = ol.MaximumPoint
        vpmax = XYZ(vptempmax.X - vpboundaryoffset, vptempmax.Y - vpboundaryoffset, 0.0)

        transmatrix.sourcemin = vpmin
        transmatrix.sourcemax = vpmax
        transmatrix.destmin = cropmin
        transmatrix.destmax = cropmax

        revtransmatrix.sourcemin = cropmin
        revtransmatrix.sourcemax = cropmax
        revtransmatrix.destmin = vpmin
        revtransmatrix.destmax = vpmax
    
        selview.CropBoxActive = cboxactive
        selview.CropBoxVisible = cboxvisible
        t.Commit()

usertemp = os.getenv('Temp')
prjname = op.splitext(op.basename(doc.PathName))[0]
datafile = usertemp + '\\' + prjname + '_pySaveViewportLocation.pym'

selected_ids = uidoc.Selection.GetElementIds()

if selected_ids.Count == 1:
    vport_id = selected_ids[0]
    try:
        vport = doc.GetElement(vport_id)
    except:
        TaskDialog.Show('pyRevit', 'Select at least one viewport. No more, no less!')
    if isinstance(vport, Viewport):
        view = doc.GetElement(vport.ViewId)
        if view is not None and isinstance(view, ViewPlan):
            with TransactionGroup(doc, 'Paste Viewport Location') as tg:
                tg.Start()
                set_tansform_matrix(vport, view)
                try:
                    with open(datafile, 'rb') as fp:
                        originalviewtype = pickle.load(fp)
                        if originalviewtype == 'ViewPlan':
                            savedcen_pt = pickle.load(fp)
                            savedmdl_pt = pickle.load(fp)
                        else:
                            raise OriginalIsViewDrafting
                except IOError:
                    TaskDialog.Show('pyRevit',
                                    'Could not find saved viewport placement.\nCopy a Viewport Placement first.')
                except OriginalIsViewDrafting:
                    TaskDialog.Show('pyRevit',
                                    'Viewport placement info is from a drafting view and can not be applied here.')
                else:
                    savedcenter_pt = XYZ(savedcen_pt.X, savedcen_pt.Y, savedcen_pt.Z)
                    savedmodel_pt = XYZ(savedmdl_pt.X, savedmdl_pt.Y, savedmdl_pt.Z)
                    with Transaction(doc, 'Apply Viewport Placement') as t:
                        t.Start()
                        center = vport.GetBoxCenter()
                        centerdiff = view_to_sheet_transform(savedmodel_pt) - center
                        vport.SetBoxCenter(savedcenter_pt - centerdiff)
                        if PINAFTERSET:
                            vport.Pinned = True
                        t.Commit()
                tg.Assimilate()
        elif view is not None and isinstance(view, ViewDrafting):
            try:
                with open(datafile, 'rb') as fp:
                    originalviewtype = pickle.load(fp)
                    if originalviewtype == 'ViewDrafting':
                        savedcen_pt = pickle.load(fp)
                    else:
                        raise OriginalIsViewPlan
            except IOError:
                TaskDialog.Show('pyRevit',
                                'Could not find saved viewport placement.\nCopy a Viewport Placement first.')
            except OriginalIsViewPlan:
                TaskDialog.Show('pyRevit',
                                'Viewport placement info is from a model view and can not be applied here.')
            else:
                savedcenter_pt = XYZ(savedcen_pt.X, savedcen_pt.Y, savedcen_pt.Z)
                with Transaction(doc, 'Apply Viewport Placement') as t:
                    t.Start()
                    vport.SetBoxCenter(savedcenter_pt)
                    if PINAFTERSET:
                        vport.Pinned = True
                    t.Commit()
        else:
            TaskDialog.Show('pyRevit', 'This tool only works with Plan, RCP, and Detail views and viewports.')
else:
    TaskDialog.Show('pyRevit', 'Select at least one viewport. No more, no less!')
