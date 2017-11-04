import re

from pyrevit import coreutils
from pyrevit import forms
from pyrevit import revit, DB, UI
from pyrevit import script

from pyrevittoolslib import patmaker


__title__ = 'Make\nPattern'

__helpurl__ = 'https://www.youtube.com/watch?v=H7b8hjHbauE'

__doc__ = 'Draw your pattern tile in a detail view using detail lines, '\
          'curves, circles or ellipses; select the pattern lines and curves '\
          'and run this tool. Give the pattern a name and '\
          'hit "Create Pattern". The tool asks you to pick the boundary '\
          'corners of the pattern. The tool will process the input lines, '\
          'approximates the curves and splines with smaller lines and '\
          'finds the best angles for these lines and will '\
          'generate a pattern. You can also check the option to create a '\
          'filled region type for this new pattern.'


logger = script.get_logger()

selection = revit.get_selection()

accpeted_lines = [DB.DetailLine,
                  DB.DetailArc,
                  DB.DetailEllipse,
                  DB.DetailNurbSpline]

accpeted_curves = [DB.Arc,
                   DB.Ellipse,
                   DB.NurbSpline]

detail_line_types = [DB.DetailLine,
                     DB.DetailEllipse,
                     DB.DetailArc,
                     DB.DetailNurbSpline]


PICK_COORD_RESOLUTION = 10


class MakePatternWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name, rvt_elements):
        # cleanup selection (pick only acceptable curves)
        self.selected_lines = self._cleanup_selection(rvt_elements)
        self.active_view = \
            revit.doc.GetElement(self.selected_lines[0].OwnerViewId)

        # create pattern maker window and process options
        forms.WPFWindow.__init__(self, xaml_file_name)
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
        with forms.WarningBar(title='Pick origin point (bottom-left '
                                    'corner of the pattern area):'):
            pat_bottomleft = revit.pick_point()
        if pat_bottomleft:
            with forms.WarningBar(title='Pick top-right corner '
                                        'of the pattern area:'):
                pat_topright = revit.pick_point()
            if pat_topright:
                return (round_domain_coord(pat_bottomleft.X),
                        round_domain_coord(pat_bottomleft.Y)), \
                       (round_domain_coord(pat_topright.X),
                        round_domain_coord(pat_topright.Y))

        return False

    def _make_pattern_line(self, start_xyz, end_xyz):
        return (start_xyz.X, start_xyz.Y), (end_xyz.X, end_xyz.Y)

    def _create_pattern(self, domain, export_only=False, export_path=None):
        pat_lines = []
        for det_line in self.selected_lines:
            geom_curve = det_line.GeometryCurve
            if type(geom_curve) in accpeted_curves:
                tes_points = [tp for tp in geom_curve.Tessellate()]
                for xyz1, xyz2 in coreutils.pairwise(tes_points):
                    pat_lines.append(self._make_pattern_line(xyz1, xyz2))

            elif isinstance(geom_curve, DB.Line):
                pat_lines.append(
                    self._make_pattern_line(geom_curve.GetEndPoint(0),
                                            geom_curve.GetEndPoint(1))
                    )

        call_params = 'Name:{} Model:{} FilledRegion:{} Domain:{} Lines:{}'\
                      .format(self.pat_name,
                              self.is_model_pat,
                              self.create_filledregion,
                              domain,
                              pat_lines)

        logger.debug(call_params)

        if not self.is_model_pat:
            pat_scale = 1.0 / self.active_view.Scale
        else:
            pat_scale = 1.0

        if export_only:
            patmaker.export_pattern(self.pat_name,
                                    pat_lines, domain, export_path,
                                    model_pattern=self.is_model_pat,
                                    scale=pat_scale * 12.0)
            UI.TaskDialog.Show('pyRevit',
                               'Pattern {} exported.'
                               .format(self.pat_name))
        else:
            patmaker.make_pattern(self.pat_name,
                                  pat_lines, domain,
                                  model_pattern=self.is_model_pat,
                                  create_filledregion=self.create_filledregion,
                                  scale=pat_scale)
            UI.TaskDialog.Show('pyRevit',
                               'Pattern {} created/updated.'
                               .format(self.pat_name))

    def _verify_name(self):
        if not self.pat_name:
            UI.TaskDialog.Show('pyRevit', 'Type a name for the pattern first')
            return False
        elif not re.search('[a-zA-Z0-9]', self.pat_name):
            UI.TaskDialog.Show('pyRevit',
                               'Pattern name must have at least '
                               'one character or digit')
            return False
        return True

    def open_help(self, sender, args):
        pass

    def export_pat(self, sender, args):
        if self._verify_name():
            self.Hide()
            domain = self._pick_domain()
            export_dir = script.pick_folder()
            if domain and export_dir:
                self._create_pattern(domain,
                                     export_only=True,
                                     export_path=export_dir)
            self.Close()

    def make_pattern(self, sender, args):
        if self._verify_name():
            self.Hide()
            domain = self._pick_domain()
            if domain:
                self._create_pattern(domain)
            self.Close()

    def fix_angles(self, sender, args):
        # self.Close()
        UI.TaskDialog.Show('pyRevit', 'Work in progress...')


# filter line types - only detail lines allowed
def filter_detail_lines(element):
    if type(element) in detail_line_types and element.OwnerViewId is not None:
        return True
    else:
        return False


# filter line types before making pattern
selected_elements = filter(filter_detail_lines, selection.elements)
if len(selected_elements) > 0:
    MakePatternWindow('MakePatternWindow.xaml', selected_elements).ShowDialog()
else:
    UI.TaskDialog.Show('pyRevit', 'At least one Detail Line must be selected.')
