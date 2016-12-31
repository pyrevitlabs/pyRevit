"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

DEBUG = False
MAKELINES = False

__doc__ = 'Draw the desired crop boundary as a closed polygon on your sheet (using detail lines). ' \
          'Then select the bounday and the destination viewport and run the script. ' \
          'This script will apply the drafted boundary to the view of the selected viewport.'

# note: no needs to check for curves in polygon.
# currently it takes a straight line between the start and end point. (no errors so far)
# todo: ask to delete polygon when done

if not DEBUG:
    __window__.Close()

from Autodesk.Revit.DB import Transaction, Viewport, ViewSheet, CurveElement, XYZ, Line, Curve, CurveLoop
from Autodesk.Revit.UI import TaskDialog
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = uidoc.Selection.GetElementIds()


class TransformationMatrix:
    def __init__(self):
        pass


transmatrix = TransformationMatrix()


def createreversedcurve(orig):
    # Create a new curve with the same geometry in the reverse direction.
    if isinstance(orig, Line):
        return Line.CreateBound(orig.GetEndPoint(1), orig.GetEndPoint(0))
    return None


def sortcurvescontiguous(origcurves):
    """
    Sort a list of curves to make them correctly
    ordered and oriented to form a closed loop.
    """
    curves = origcurves
    _inch = 1.0 / 12.0
    _sixteenth = _inch / 16.0
    n = len(curves)
    if DEBUG:
        print('NUMBER OF CURVES: {0}'.format(n))
    # Walk through each curve (after the first)
    # to match up the curves in order
    for i in range(0, n):
        curve = curves[i]
        endpoint = curve.GetEndPoint(1)
        found = (i + 1 >= n)
        for j in range(i + 1, n):
            # If there is a match end->start,
            # this is the next curve
            p = curves[j].GetEndPoint(0)
            if DEBUG:
                print('END2START: {0}'.format(_sixteenth > p.DistanceTo(endpoint)))
            if _sixteenth > p.DistanceTo(endpoint):
                if i + 1 != j:
                    tmp = curves[i + 1]
                    curves[i + 1] = curves[j]
                    curves[j] = tmp
                    if DEBUG:
                        print('SWAPPED.')
                if DEBUG:
                    print('SWAP UNECESSARY.')
                found = True
                break
            # If there is a match end->end,
            # reverse the next curve
            p = curves[j].GetEndPoint(1)
            if DEBUG:
                print('END2END: {0}'.format(_sixteenth > p.DistanceTo(endpoint)))
            if _sixteenth > p.DistanceTo(endpoint):
                if i + 1 == j:
                    curves[i + 1] = createreversedcurve(curves[j])
                else:
                    tmp = curves[i + 1]
                    curves[i + 1] = createreversedcurve(curves[j])
                    curves[j] = tmp
                if DEBUG:
                    print('REVERSED.')
                found = True
                break
        if not found:
            return None
    return curves


def sheet_to_view_transform(sheetcoord):
    global transmatrix
    newx = transmatrix.destmin.X + (
        ((sheetcoord.X - transmatrix.sourcemin.X) * (transmatrix.destmax.X - transmatrix.destmin.X)) / (
            transmatrix.sourcemax.X - transmatrix.sourcemin.X))
    newy = transmatrix.destmin.Y + (
        ((sheetcoord.Y - transmatrix.sourcemin.Y) * (transmatrix.destmax.Y - transmatrix.destmin.Y)) / (
            transmatrix.sourcemax.Y - transmatrix.sourcemin.Y))
    return XYZ(newx, newy, 0.0)


selview = selvp = None
vpboundaryoffset = 0.01
selviewports = []
selboundary = []
activeSheet = uidoc.ActiveGraphicalView

# pick viewport and line boundary from selection
for elId in selection:
    el = doc.GetElement(elId)
    if isinstance(el, Viewport):
        selviewports.append(el)
    elif isinstance(el, CurveElement):
        selboundary.append(el)
if len(selviewports) > 0:
    selvp = selviewports[0]
    selview = doc.GetElement(selvp.ViewId)
else:
    TaskDialog.Show('pyrevit', 'At least one viewport must be selected.')

if len(selboundary) < 3:
    TaskDialog.Show('pyrevit', 'At least one closed polygon must be selected (minimum 3 detail lines).')

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
if DEBUG:
    print('VP MIN MAX: {0}\n'
          '            {1}\n'.format(vpmin, vpmax))

# get view min max points in modelUCS.
modelucsx = []
modelucsy = []
crsm = selview.GetCropRegionShapeManager()
cl = crsm.GetCropShape()[0]
for l in cl:
    modelucsx.append(l.GetEndPoint(0).X)
    modelucsy.append(l.GetEndPoint(0).Y)
    if DEBUG:
        print('CROP LINE POINTS: {0}\n'
              '                  {1}\n'.format(l.GetEndPoint(0), l.GetEndPoint(1)))

cropmin = XYZ(min(modelucsx), min(modelucsy), 0.0)
cropmax = XYZ(max(modelucsx), max(modelucsy), 0.0)
if DEBUG:
    print('CROP MIN MAX: {0}\n'
          '              {1}\n'.format(cropmin, cropmax))
if DEBUG:
    print('VIEW BOUNDING BOX ON THIS SHEET: {0}\n'
          '                                 {1}\n'.format(selview.BoundingBox[selview].Min,
                                                          selview.BoundingBox[selview].Max))
transmatrix.sourcemin = vpmin
transmatrix.sourcemax = vpmax
transmatrix.destmin = cropmin
transmatrix.destmax = cropmax

with Transaction(doc, 'Set Crop Region') as t:
    curveloop = []
    t.Start()
    for bl in selboundary:
        newlinestart = sheet_to_view_transform(bl.GeometryCurve.GetEndPoint(0))
        newlineend = sheet_to_view_transform(bl.GeometryCurve.GetEndPoint(1))
        geomLine = Line.CreateBound(newlinestart, newlineend)
        if MAKELINES:
            sketchp = selview.SketchPlane
            mline = doc.Create.NewModelCurve(geomLine, sketchp)
        curveloop.append(geomLine)
        if DEBUG:
            print('VP POLY LINE POINTS: {0}\n'
                  '                     {1}\n'.format(bl.GeometryCurve.GetEndPoint(0),
                                                      bl.GeometryCurve.GetEndPoint(1)
                                                      ))

        if DEBUG:
            print('NEW CROP LINE POINTS: {0}\n'
                  '                      {1}\n'.format(newlinestart,
                                                       newlineend))
    sortedcurves = sortcurvescontiguous(curveloop)
    if sortedcurves:
        crsm.SetCropShape(CurveLoop.Create(List[Curve](sortedcurves)))
    else:
        TaskDialog.Show('pyrevit', 'Curves must be in a closed loop.')
    t.Commit()
