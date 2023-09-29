from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


# note: no needs to check for curves in polygon.
# currently it takes a straight line between the start and end point.
# (no errors so far)
# todo: ask to delete polygon when done

DEBUG = False
MAKELINES = False
MAX_ITERATIONS = 1

selection = revit.get_selection()


class TransformationMatrix:
    def __init__(self):
        pass


transmatrix = TransformationMatrix()


def createreversedcurve(orig):
    # Create a new curve with the same geometry in the reverse direction.
    if isinstance(orig, DB.Line):
        return DB.Line.CreateBound(orig.GetEndPoint(1), orig.GetEndPoint(0))
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
                print('END2START: {0}'
                      .format(_sixteenth > p.DistanceTo(endpoint)))
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
                print('END2END: {0}'
                      .format(_sixteenth > p.DistanceTo(endpoint)))
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

    x_direction = transmatrix.cordinatesystem[0]
    x_scalar = (transmatrix.destmax - transmatrix.destmin).DotProduct(x_direction) / (transmatrix.sourcemax.X - transmatrix.sourcemin.X)
    x_transformation = ((sheetcoord.X - transmatrix.sourcemin.X) * x_scalar) * x_direction

    y_direction = transmatrix.cordinatesystem[1]
    y_scalar = (transmatrix.destmax - transmatrix.destmin).DotProduct(y_direction) / (transmatrix.sourcemax.Y - transmatrix.sourcemin.Y)
    y_transformation = ((sheetcoord.Y - transmatrix.sourcemin.Y) * y_scalar) * y_direction

    tranformed_point = transmatrix.destmin + (x_transformation + y_transformation)
    return tranformed_point


def update_transformation_matrix(transmatrix, view_port, selected_view_crop_shape, selected_view, boundary_offset):
    # get vp min max points in sheetUCS
    ol = view_port.GetBoxOutline()
    vptempmin = ol.MinimumPoint
    vpmin = DB.XYZ(vptempmin.X + boundary_offset,
                   vptempmin.Y + boundary_offset,
                   0.0)

    vptempmax = ol.MaximumPoint
    vpmax = DB.XYZ(vptempmax.X - boundary_offset,
                   vptempmax.Y - boundary_offset,
                   0.0)
    if DEBUG:
        print('VP MIN MAX: {0}\n'
              '            {1}\n'.format(vpmin, vpmax))

    # get view min max points in modelUCS.
    view_max, view_min = (lambda x: ([-x] * 3, [x-1] * 3))(2**63) # (2) 1x3 vectors with max/min 64 bit numbers
    cl = selected_view_crop_shape
    for l in cl:
        end_point_zero = l.GetEndPoint(0)
        end_point_one = l.GetEndPoint(1)
        for i in range(3):
            view_min[i] = min(view_min[i], end_point_zero[i], end_point_one[i])
            view_max[i] = max(view_max[i], end_point_zero[i], end_point_one[i])
        if DEBUG:
            print('CROP LINE POINTS: {0}\n'
                  '                  {1}\n'.format(l.GetEndPoint(0),
                                                   l.GetEndPoint(1)))

    cropmin = DB.XYZ(*view_min)
    cropmax = DB.XYZ(*view_max)
    if DEBUG:
        print('CROP MIN MAX: {0}\n'
              '              {1}\n'.format(cropmin, cropmax))
    if DEBUG:
        print('VIEW BOUNDING BOX ON THIS SHEET: {0}\n'
              '                                 {1}\n'
              .format(selected_view.BoundingBox[selected_view].Min,
                      selected_view.BoundingBox[selected_view].Max))
    transmatrix.sourcemin = vpmin
    transmatrix.sourcemax = vpmax
    transmatrix.destmin = cropmin
    transmatrix.destmax = cropmax


def set_crop_boundary():
    selview = selvp = None
    vpboundaryoffset = 0.01
    selviewports = []
    selboundary = []

    # pick viewport and line boundary from selection
    for el in selection:
        if isinstance(el, DB.Viewport):
            selviewports.append(el)
        elif isinstance(el, DB.CurveElement):
            selboundary.append(el)
    if len(selviewports) > 0:
        selvp = selviewports[0]
        selview = revit.doc.GetElement(selvp.ViewId)
    else:
        forms.alert('At least one viewport must be selected.')

    if len(selboundary) < 3:
        forms.alert('At least one closed polygon must be '
                    'selected (minimum 3 detail lines).')

    # making sure the cropbox is active.
    if not selview.CropBoxActive:
        with revit.Transaction('Activate Crop Box'):
            selview.CropBoxActive = True

    crsm = selview.GetCropRegionShapeManager()
    transmatrix.cordinatesystem = [selview.RightDirection, selview.UpDirection]

    with revit.Transaction('Set Crop Region'):
        for i in range(max(MAX_ITERATIONS, 1)):
            update_transformation_matrix(transmatrix, selvp, crsm.GetCropShape()[0], selview, vpboundaryoffset)
            curveloop = []
            for bl in selboundary:
                newlinestart = sheet_to_view_transform(bl.GeometryCurve.GetEndPoint(0))
                newlineend = sheet_to_view_transform(bl.GeometryCurve.GetEndPoint(1))
                geomLine = DB.Line.CreateBound(newlinestart, newlineend)
                if MAKELINES:
                    sketchp = selview.SketchPlane
                    mline = revit.doc.Create.NewModelCurve(geomLine, sketchp)
                curveloop.append(geomLine)
                if DEBUG:
                    print('VP POLY LINE POINTS: {0}\n'
                        '                     {1}\n'
                        .format(bl.GeometryCurve.GetEndPoint(0),
                                bl.GeometryCurve.GetEndPoint(1)))

                if DEBUG:
                    print('NEW CROP LINE POINTS: {0}\n'
                        '                      {1}\n'.format(newlinestart,
                                                            newlineend))
            sortedcurves = sortcurvescontiguous(curveloop)
            if sortedcurves:
                crsm.SetCropShape(DB.CurveLoop.Create(List[DB.Curve](sortedcurves)))
            else:
                forms.alert('Curves must be in a closed loop.')
            revit.doc.Regenerate()


if selection:
    set_crop_boundary()
else:
    forms.alert('Select one viewport and a detail line boundary.')
