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

__doc__ = 'Copies the location of the selected viewport to memory. This can be later applied to other viewports ' \
          'on other sheets.'
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


def sheet_to_view_transform(sheetcoord):
    global transmatrix
    newx = transmatrix.destmin.X + (
        ((sheetcoord.X - transmatrix.sourcemin.X) * (transmatrix.destmax.X - transmatrix.destmin.X)) / (
            transmatrix.sourcemax.X - transmatrix.sourcemin.X))
    newy = transmatrix.destmin.Y + (
        ((sheetcoord.Y - transmatrix.sourcemin.Y) * (transmatrix.destmax.Y - transmatrix.destmin.Y)) / (
            transmatrix.sourcemax.Y - transmatrix.sourcemin.Y))
    return XYZ(newx, newy, 0.0)


def set_tansform_matrix(selvp, selview):
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

usertemp = os.getenv('Temp')
prjname = op.splitext(op.basename(doc.PathName))[0]
datafile = usertemp + '\\' + prjname + '_pySaveViewportLocation.pym'

selected_ids = uidoc.Selection.GetElementIds()

if selected_ids.Count == 1:
    for vport_id in selected_ids:
        vport = doc.GetElement(vport_id)
        view = doc.GetElement(vport.ViewId)
        if isinstance(vport, Viewport):
            set_tansform_matrix(vport, view)
            center = vport.GetBoxCenter()
            modelpoint = sheet_to_view_transform(center)
            center_pt = Point(center.X, center.Y, center.Z)
            model_pt = Point(modelpoint.X, modelpoint.Y, modelpoint.Z)
            with open(datafile, 'wb') as fp:
                pickle.dump(center_pt, fp)
                pickle.dump(model_pt, fp)
            break
else:
    TaskDialog.Show('pyRevit', 'Select at least one viewport. No more, no less!')
