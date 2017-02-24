from itertools import tee, izip

from scriptutils import this_script, logger
from revitutils import doc, selection, patmaker

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import DetailLine, DetailArc, DetailEllipse, DetailNurbSpline
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Line, Arc, Ellipse, NurbSpline
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog



accpeted_lines = [DetailLine, DetailArc, DetailEllipse, DetailNurbSpline]
accpeted_curves = [Arc, Ellipse, NurbSpline]


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)


def make_pattern_line(rvt_start_p, rvt_end_p, rvt_origin):
    relative_start_p = rvt_start_p - rvt_origin
    relative_end_p = rvt_end_p - rvt_origin
    start_p = patmaker.PatternPoint(relative_start_p.X, relative_start_p.Y)
    end_p = patmaker.PatternPoint(relative_end_p.X, relative_end_p.Y)
    return patmaker.PatternLine(start_p, end_p, line_id=det_line.Id.IntegerValue)


def cleanup_selection():
    lines = []
    for element in selection.elements:
        if type(element) in accpeted_lines:
            lines.append(element)
    return lines


det_lines = cleanup_selection()


if len(det_lines) > 0:
    # ask user for origin and max domain points
    pat_bottomleft = selection.utils.pick_point('Pick origin point (bottom-right corner of the pattern area):')
    if pat_bottomleft:
        pat_topright = selection.utils.pick_point('Pick top-right corner of the pattern area:')
        if pat_topright:
            domain = pat_topright - pat_bottomleft
            pat_domain = patmaker.PatternPoint(domain.X, domain.Y)

            pat_lines = []
            for det_line in det_lines:
                geom_curve = det_line.GeometryCurve
                if type(geom_curve) in accpeted_curves:
                    tes_points = [tp for tp in geom_curve.Tessellate()]
                    for p1, p2 in pairwise(tes_points):
                        pat_lines.append(make_pattern_line(p1, p2, pat_bottomleft))

                elif isinstance(geom_curve, Line):
                    pat_lines.append(make_pattern_line(geom_curve.GetEndPoint(0),
                                                       geom_curve.GetEndPoint(1),
                                                       pat_bottomleft))

            logger.debug('Pattern domain is: {}'.format(pat_domain))
            logger.debug('Pattern lines are: {}'.format(pat_lines))

            patmaker.make_pattern('Test Pattern 17', pat_lines, pat_domain, model_pattern=True)

else:
    TaskDialog.Show('pyRevit', 'At least one Detail Line must be selected.')
