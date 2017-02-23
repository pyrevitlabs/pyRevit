from scriptutils import this_script, logger
from revitutils import doc, selection, patmaker

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import DetailLine, UnitType
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog


det_lines = []


for element in selection.elements:
    if isinstance(element, DetailLine):
        det_lines.append(element)

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
                relative_start_p = geom_curve.GetEndPoint(0) - pat_bottomleft
                relative_end_p = geom_curve.GetEndPoint(1) - pat_bottomleft
                start_p = patmaker.PatternPoint(relative_start_p.X, relative_start_p.Y)
                end_p = patmaker.PatternPoint(relative_end_p.X, relative_end_p.Y)
                pat_lines.append(patmaker.PatternLine(start_p, end_p, line_id=det_line.Id.IntegerValue))

            logger.debug('Pattern domain is: {}'.format(pat_domain))
            logger.debug('Pattern lines are: {}'.format(pat_lines))

            patmaker.make_pattern('Test Pattern 6', pat_lines, pat_domain, model_pattern=True)

else:
    TaskDialog.Show('pyRevit', 'At least one Detail Line must be selected.')
