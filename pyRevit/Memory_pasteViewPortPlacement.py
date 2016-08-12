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

__doc__ = 'Paste a Viewport Placement from memory'
__author__ = 'Gui Talarico | gtalarico@gmail.com\nEhsan Iran-Nejad | eirannejad@gmail.com'
__version__ = '0.1.0'

import os
import os.path as op
import pickle
from collections import namedtuple

from Autodesk.Revit.DB import Transaction, Viewport, ViewSheet, XYZ
from Autodesk.Revit.UI import TaskDialog

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument


class TransformationMatrix:
    def __init__(self):
        self.sourcemin = None
        self.sourcemax = None
        self.destmin = None
        self.destmax = None


Point = namedtuple('Point', ['X', 'Y','Z'])

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
    global transmatrix
    global revtransmatrix
    # making sure the cropbox is active.
    if not selview.CropBoxActive:
        with Transaction(doc, 'Activate Crop Box') as t:
            t.Start()
            selview.CropBoxActive = True
            t.Commit()

    # get vp min max points in sheetUCS
    ol = selvp.GetBoxOutline()
    vptempmin = ol.MinimumPoint
    vpmin = XYZ(vptempmin.X + vpboundaryoffset, vptempmin.Y + vpboundaryoffset, 0.0)
    vptempmax = ol.MaximumPoint
    vpmax = XYZ(vptempmax.X - vpboundaryoffset, vptempmax.Y - vpboundaryoffset, 0.0)

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

    transmatrix.sourcemin = vpmin
    transmatrix.sourcemax = vpmax
    transmatrix.destmin = cropmin
    transmatrix.destmax = cropmax

    revtransmatrix.sourcemin = cropmin
    revtransmatrix.sourcemax = cropmax
    revtransmatrix.destmin = vpmin
    revtransmatrix.destmax = vpmax

usertemp = os.getenv('Temp')
prjname = op.splitext(op.basename(doc.PathName))[0]
datafile = usertemp + '\\' + prjname + '_pySaveViewportLocation.pym'

selected_ids = uidoc.Selection.GetElementIds()

if selected_ids.Count == 1:
    for element_id in selected_ids:
        vport = doc.GetElement(element_id)
        view = doc.GetElement(vport.ViewId)
        if isinstance(vport, Viewport):
            set_tansform_matrix(vport, view)
            try:
                with open(datafile, 'rb') as fp:
                    savedcen_pt = pickle.load(fp)
                    savedmdl_pt = pickle.load(fp)
            except IOError:
                TaskDialog.Show('pyRevit', 'Could not find saved viewport placement.\nCopy a Viewport Placement first.')
            else:
                savedcenter_pt = XYZ(savedcen_pt.X, savedcen_pt.Y, savedcen_pt.Z)
                savedmodel_pt = XYZ(savedmdl_pt.X, savedmdl_pt.Y, savedmdl_pt.Z)
                t = Transaction(doc, 'Paste Viewport Placement')
                t.Start()
                center = vport.GetBoxCenter()
                centerdiff = view_to_sheet_transform(savedmodel_pt) - center
                vport.SetBoxCenter(savedcenter_pt - centerdiff)
                # vport.Pinned = True
                t.Commit()

else:
    TaskDialog.Show('pyRevit', 'Select at least one viewport. No more, no less!')
