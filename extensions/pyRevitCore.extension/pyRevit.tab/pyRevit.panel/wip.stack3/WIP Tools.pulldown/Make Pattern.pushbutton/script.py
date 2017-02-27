from itertools import tee, izip

from scriptutils import this_script, logger
from scriptutils.userinput import WPFWindow
from revitutils import doc, selection, patmaker

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import DetailLine, DetailArc, DetailEllipse, DetailNurbSpline
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Line, Arc, Ellipse, NurbSpline
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog



accpeted_lines = [DetailLine, DetailArc, DetailEllipse, DetailNurbSpline]
accpeted_curves = [Arc, Ellipse, NurbSpline]



class MakePatternWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)
        self.pat_name_tb.Focus()

    @property
    def is_detail_pat(self):
        return self.is_detail_cb.IsChecked

    @property
    def is_model_pat(self):
        return self.is_model_cb.IsChecked

    @property
    def pat_name(self):
        return self.pat_name_tb.Text

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def make_pattern(self, sender, args):
        self.Close()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def fix_angles(self, sender, args):
        self.Close()


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)


def make_pattern_line(rvt_start_p, rvt_end_p, rvt_origin, id):
    relative_start_p = rvt_start_p - rvt_origin
    relative_end_p = rvt_end_p - rvt_origin
    start_p = patmaker.PatternPoint(relative_start_p.X, relative_start_p.Y)
    end_p = patmaker.PatternPoint(relative_end_p.X, relative_end_p.Y)
    return patmaker.PatternLine(start_p, end_p, line_id=id)


def cleanup_selection():
    lines = []
    for element in selection.elements:
        if type(element) in accpeted_lines:
            lines.append(element)
    return lines


def create_pattern(det_lines, pat_name, is_model_pat):
    # ask user for origin and max domain points
    pat_bottomleft = selection.utils.pick_point('Pick origin point (bottom-right corner of the pattern area):')
    if pat_bottomleft:
        pat_topright = selection.utils.pick_point('Pick top-right corner of the pattern area:')
        if pat_topright:
            domain = pat_topright - pat_bottomleft
            print('Calculating safe angles for this tile size...')
            pat_domain = patmaker.PatternPoint(domain.X, domain.Y)

            pat_lines = []
            for det_line in det_lines:
                geom_curve = det_line.GeometryCurve
                if type(geom_curve) in accpeted_curves:
                    tes_points = [tp for tp in geom_curve.Tessellate()]
                    for p1, p2 in pairwise(tes_points):
                        pat_lines.append(make_pattern_line(p1, p2, pat_bottomleft, det_line.Id.IntegerValue))

                elif isinstance(geom_curve, Line):
                    pat_lines.append(make_pattern_line(geom_curve.GetEndPoint(0),
                                                       geom_curve.GetEndPoint(1),
                                                       pat_bottomleft,
                                                       det_line.Id.IntegerValue))

            logger.debug('Pattern domain is: {}'.format(pat_domain))
            logger.debug('Pattern lines are: {}'.format(pat_lines))

            patmaker.make_pattern(pat_name, pat_lines, pat_domain, model_pattern=is_model_pat)


if __name__ == '__main__':
    det_lines = cleanup_selection()
    if len(det_lines) > 0:
        pat_info = MakePatternWindow('MakePatternWindow.xaml')
        pat_info.ShowDialog()
        create_pattern(det_lines, pat_info.pat_name, pat_info.is_model_pat)
    else:
        TaskDialog.Show('pyRevit', 'At least one Detail Line must be selected.')
