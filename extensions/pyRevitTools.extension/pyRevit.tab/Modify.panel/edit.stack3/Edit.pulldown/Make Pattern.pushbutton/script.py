import re

from pyrevit.coreutils import pairwise

from scriptutils import this_script, logger
from scriptutils.userinput import WPFWindow
from revitutils import doc, selection, patmaker

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import DetailLine, DetailArc, DetailEllipse, DetailNurbSpline
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Line, Arc, Ellipse, NurbSpline
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog


__doc__ = 'Draw your pattern tile in a detail view using detail lines, curves, circles or ellipses; '\
          'select the pattern lines and curves and run this tool. Give the pattern a name and hit '\
          '"Create Pattern". The tool asks you to pick the boundary corners of the pattern. The tool will '\
          'process the input lines, approximates the curves and splines with smaller lines and finds the best '\
          'angles for these lines and will generate a pattern. You can also check the option to create a '\
          'filled region type for this new pattern.'


accpeted_lines = [DetailLine, DetailArc, DetailEllipse, DetailNurbSpline]
accpeted_curves = [Arc, Ellipse, NurbSpline]


PICK_COORD_RESOLUTION = 10


class MakePatternWindow(WPFWindow):
    def __init__(self, xaml_file_name, rvt_elements):
        # cleanup selection (pick only acceptable curves)
        self.selected_lines = self._cleanup_selection(rvt_elements)

        # create pattern maker window and process options
        WPFWindow.__init__(self, xaml_file_name)
        self.dottypes_cb.ItemsSource = patmaker.DOT_TYPES
        self.dottypes_cb.SelectedIndex = 0
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

    @property
    def allow_jiggle(self):
        return self.allow_jiggle_cb.IsChecked

    @property
    def create_filledregion(self):
        return self.createfilledregion_cb.IsChecked

    @staticmethod
    def _cleanup_selection(rvt_elements):
        lines = []
        for element in rvt_elements:
            if type(element) in accpeted_lines:
                lines.append(element)
        return lines

    def _pick_domain(self):
        def round_domain_coord(coord):
            return round(coord, PICK_COORD_RESOLUTION)

        # ask user for origin and max domain points
        pat_bottomleft = selection.utils.pick_point('Pick origin point (bottom-right corner of the pattern area):')
        if pat_bottomleft:
            pat_topright = selection.utils.pick_point('Pick top-right corner of the pattern area:')
            if pat_topright:
                return (round_domain_coord(pat_bottomleft.X), round_domain_coord(pat_bottomleft.Y)), \
                       (round_domain_coord(pat_topright.X), round_domain_coord(pat_topright.Y))

        return False

    def _make_pattern_line(self, start_xyz, end_xyz):
        return (start_xyz.X, start_xyz.Y), (end_xyz.X, end_xyz.Y)

    def _create_pattern(self, domain):
        pat_lines = []
        for det_line in self.selected_lines:
            geom_curve = det_line.GeometryCurve
            if type(geom_curve) in accpeted_curves:
                tes_points = [tp for tp in geom_curve.Tessellate()]
                for xyz1, xyz2 in pairwise(tes_points):
                    pat_lines.append(self._make_pattern_line(xyz1, xyz2))

            elif isinstance(geom_curve, Line):
                pat_lines.append(self._make_pattern_line(geom_curve.GetEndPoint(0), geom_curve.GetEndPoint(1)))

        call_params = 'Name:{} Model:{} FilledRegion:{} Domain:{} Lines:{}'.format(self.pat_name, self.is_model_pat,
                                                                                   self.create_filledregion,
                                                                                   domain, pat_lines)
        logger.debug(call_params)
        patmaker.make_pattern(self.pat_name, pat_lines, domain,
                              model_pattern=self.is_model_pat, create_filledregion=self.create_filledregion)
        TaskDialog.Show('pyRevit', 'Pattern {} created.'.format(self.pat_name))

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def open_help(self, sender, args):
        pass

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def make_pattern(self, sender, args):
        if not self.pat_name:
            TaskDialog.Show('pyRevit', 'Type a name for the pattern first')
        elif not re.search('[a-zA-Z0-9]', self.pat_name):
            TaskDialog.Show('pyRevit', 'Pattern name must have at least one character or digit')
        else:
            self.Hide()
            domain = self._pick_domain()
            if domain:
                self._create_pattern(domain)
            self.Close()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def fix_angles(self, sender, args):
        # self.Close()
        TaskDialog.Show('pyRevit', 'Work in progress...')


if __name__ == '__main__':
    if len(selection.elements) > 0:
        MakePatternWindow('MakePatternWindow.xaml', selection.elements).ShowDialog()
    else:
        TaskDialog.Show('pyRevit', 'At least one Detail Line must be selected.')
