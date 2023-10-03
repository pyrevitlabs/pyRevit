from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


# note: no needs to check for curves in polygon.
# currently it takes a straight line between the start and end point.
# (no errors so far)
# todo: ask to delete polygon when done

DEBUG = False

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


def get_transformation(view_port, view, view_crop_shape):
    def _min_mix(_shape):
        _max, _min = (lambda x: ([-x] * 3, [x-1] * 3))(2**63) # (2) 1x3 vectors with max/min 64 bit numbers
        _cl = _shape
        for _l in _cl:
            _p_zero = _l.GetEndPoint(0)
            _p_one = _l.GetEndPoint(1)
            for i in range(3):
                _min[i] = min(_min[i], _p_zero[i], _p_one[i])
                _max[i] = max(_max[i], _p_zero[i], _p_one[i])
        return DB.XYZ(*_max), DB.XYZ(*_min)

    view_crop_max, view_crop_min = _min_mix(view_crop_shape)
    sheet_max, sheet_min = view_port.GetBoxOutline().MaximumPoint, view_port.GetBoxOutline().MinimumPoint

    view_crop_center = (view_crop_max + view_crop_min) * 0.5
    sheet_center = (sheet_max + sheet_min) * 0.5

    # transforms all points on the sheet to be relative to center of sheet viewport
    sheet_transform = DB.Transform.CreateTranslation(-sheet_center)

    # transforms all sheet points to be relative to the model views crop center
    basis_transform = DB.Transform.CreateTranslation(view_crop_center)
    basis_transform.BasisX = view.RightDirection * view.Scale
    basis_transform.BasisY = view.UpDirection * view.Scale
    basis_transform.BasisZ = view.ViewDirection * view.Scale

    # return composition of transforms going from right to left (sheet transform first, then basis transform)
    return  basis_transform * sheet_transform


def set_crop_boundary():
    selview = selvp = None
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
    view_crop = crsm.GetCropShape()[0]

    with revit.Transaction('Set Crop Region'):
        selview.AreAnnotationCategoriesHidden = True

        curveloop = []
        for bl in selboundary:
            newlinestart = bl.GeometryCurve.GetEndPoint(0)
            newlineend = bl.GeometryCurve.GetEndPoint(1)
            geomLine = DB.Line.CreateBound(newlinestart, newlineend)
            curveloop.append(geomLine)
        sortedcurves = sortcurvescontiguous(curveloop)

        if sortedcurves:
            crop_shape = DB.CurveLoop.Create(List[DB.Curve](sortedcurves))
        else:
            forms.alert('Curves must be in a closed loop.')

        transform = get_transformation(selvp, selview, view_crop)
        crop_shape = DB.CurveLoop.CreateViaTransform(crop_shape, transform)
        crsm.SetCropShape(crop_shape)
        selview.AreAnnotationCategoriesHidden = False


selection = revit.get_selection()

if selection:
    set_crop_boundary()
else:
    forms.alert('Select one viewport and a detail line boundary.')
