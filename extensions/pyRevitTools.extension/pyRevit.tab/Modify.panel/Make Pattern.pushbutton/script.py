import re

from pyrevit import coreutils
from pyrevit.coreutils import pyutils
from pyrevit import forms
from pyrevit import revit, DB, UI
from pyrevit import script

import patmaker


__title__ = 'Make\nPattern'

__helpurl__ = 'https://www.youtube.com/watch?v=H7b8hjHbauE'

__doc__ = 'Draw your pattern tile in a detail view using detail lines, '\
          'curves, circles or ellipses, or even filled regions.\n'\
          'Select the pattern lines and curves '\
          'and run this tool. Give the pattern a name and '\
          'hit "Create Pattern". The tool asks you to pick the boundary '\
          'corners of the pattern. The tool will process the input lines, '\
          'approximates the curves and splines with smaller lines and '\
          'finds the best angles for these lines and will '\
          'generate a pattern. It also reads the patterns from selected '\
          'filled regions and will combine with selected detail lines.'\
          '\n\n'\
          'TIP: You can export existing patterns if no lines are selected.'\
          '\n\n'\
          'TRICK: You can convert existing pattern types by selecting a '\
          'filled region only and create the opposite pattern type '\
          '(selected drafting filled region and create model pattern).'\


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


metric_units = [DB.DisplayUnitType.DUT_METERS,
                DB.DisplayUnitType.DUT_CENTIMETERS,
                DB.DisplayUnitType.DUT_MILLIMETERS]


# type in lower case
readonly_patterns = ['solid fill']


PICK_COORD_RESOLUTION = 10


class MakePatternWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name, rvt_elements=None):
        self._selection = rvt_elements
        self._export_only = False

        # create pattern maker window and process options
        forms.WPFWindow.__init__(self, xaml_file_name)

        if not self._selection:
            self.resolver_ops.IsEnabled = False
            self.create_b.IsEnabled = False
            self._export_only = True

        self.setup_patnames()
        self.setup_export_units()

    @property
    def is_detail_pat(self):
        return self.is_detail_cb.IsChecked

    @property
    def is_model_pat(self):
        return self.is_model_cb.IsChecked

    @property
    def pat_name(self):
        return self.pat_name_cb.Text

    @property
    def allow_jiggle(self):
        return self.allow_jiggle_cb.IsChecked

    @property
    def create_filledregion(self):
        return self.createfilledregion_cb.IsChecked

    @property
    def export_scale(self):
        # 12 for feet to inch, 304.8 for feet to mm
        return 12.0 if self.export_units_cb.SelectedItem == 'INCH' else 304.8

    def update_fillgrid(self, rvt_fillgrid, scale):
        ext_origin = rvt_fillgrid.Origin
        rvt_fillgrid.Origin = DB.UV(ext_origin.U * scale,
                                    ext_origin.V * scale)
        rvt_fillgrid.Offset *= scale
        rvt_fillgrid.Shift *= scale

        scaled_segments = [x * scale for x in rvt_fillgrid.GetSegments()]
        rvt_fillgrid.SetSegments(scaled_segments)

        return rvt_fillgrid

    def cleanup_selection(self, rvt_elements, for_model=True):
        lines = []
        adjusted_fillgrids = []
        for element in rvt_elements:
            if type(element) in accpeted_lines:
                lines.append(element)
            elif isinstance(element, DB.FilledRegion):
                frtype = revit.doc.GetElement(element.GetTypeId())
                fillpat_element = revit.doc.GetElement(frtype.FillPatternId)
                fillpat = fillpat_element.GetFillPattern()
                fillgrids = fillpat.GetFillGrids()
                # adjust derafting patterns to current scale
                if fillpat.Target == DB.FillPatternTarget.Drafting:
                    adjusted_fillgrids = \
                        [self.update_fillgrid(x, revit.activeview.Scale)
                         for x in fillgrids]
                else:
                    adjusted_fillgrids.extend(fillgrids)

        return lines, adjusted_fillgrids

    def setup_patnames(self):
        existing_pats = DB.FilteredElementCollector(revit.doc)\
                          .OfClass(DB.FillPatternElement)\
                          .ToElements()

        fillpats = [x.GetFillPattern() for x in existing_pats]
        self._existing_modelpats = \
            sorted([x.Name for x in fillpats
                    if x.Target == DB.FillPatternTarget.Model
                    and x.Name.lower() not in readonly_patterns])
        self._existing_draftingpats = \
            sorted([x.Name for x in fillpats
                    if x.Target == DB.FillPatternTarget.Drafting
                    and x.Name.lower() not in readonly_patterns])

        self.setup_patnames_combobox()

    def setup_patnames_combobox(self, model=True):
        if model:
            self.pat_name_cb.ItemsSource = self._existing_modelpats
        else:
            self.pat_name_cb.ItemsSource = self._existing_draftingpats
        self.pat_name_cb.Focus()

    def setup_export_units(self):
        self.export_units_cb.ItemsSource = ['INCH', 'MM']
        units = revit.doc.GetUnits()
        length_fo = units.GetFormatOptions(DB.UnitType.UT_Length)
        if length_fo.DisplayUnits in metric_units:
            self.export_units_cb.SelectedIndex = 1
        else:
            self.export_units_cb.SelectedIndex = 0

    def pick_domain(self):
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

    def make_pattern_line(self, start_xyz, end_xyz):
        return (start_xyz.X, start_xyz.Y), (end_xyz.X, end_xyz.Y)

    def export_pattern(self, export_dir):
        patname = self.pat_name_cb.SelectedItem
        existing_pats = DB.FilteredElementCollector(revit.doc)\
                          .OfClass(DB.FillPatternElement)\
                          .ToElements()

        fillpats = [x.GetFillPattern() for x in existing_pats]
        target_type = \
            DB.FillPatternTarget.Model \
                if self.is_model_pat else DB.FillPatternTarget.Drafting
        searchpats = [x for x in fillpats if x.Target == target_type]
        for fillpat in searchpats:
            if fillpat.Name == patname:
                patmaker.export_pattern(
                    export_dir,
                    patname,
                    [], ((0, 0), (1, 1)),
                    fillgrids=fillpat.GetFillGrids(),
                    scale=self.export_scale,
                    model_pattern=self.is_model_pat)
                forms.alert('Pattern {} exported.'.format(patname))

    def create_pattern(self, domain, export_only=False, export_path=None):
        # cleanup selection (pick only acceptable curves)
        self.selected_lines, self.selected_fillgrids = \
            self.cleanup_selection(self._selection,
                                   for_model=self.is_model_pat)

        line_tuples = []
        for det_line in self.selected_lines:
            geom_curve = det_line.GeometryCurve
            if type(geom_curve) in accpeted_curves:
                tes_points = [tp for tp in geom_curve.Tessellate()]
                for xyz1, xyz2 in coreutils.pairwise(tes_points):
                    line_tuples.append(self.make_pattern_line(xyz1, xyz2))

            elif isinstance(geom_curve, DB.Line):
                line_tuples.append(
                    self.make_pattern_line(geom_curve.GetEndPoint(0),
                                            geom_curve.GetEndPoint(1))
                    )

        call_params = 'Name:{} Model:{} FilledRegion:{} Domain:{}\n' \
                      'Lines:{}\n'\
                      'FillGrids:{}'\
                      .format(self.pat_name,
                              self.is_model_pat,
                              self.create_filledregion,
                              domain,
                              line_tuples,
                              self.selected_fillgrids)

        logger.debug(call_params)

        if not self.is_model_pat:
            pat_scale = 1.0 / revit.activeview.Scale
        else:
            pat_scale = 1.0

        if export_only:
            patmaker.export_pattern(
                export_path,
                self.pat_name,
                line_tuples, domain,
                fillgrids=self.selected_fillgrids,
                scale=pat_scale * self.export_scale,
                model_pattern=self.is_model_pat,
                allow_expansion=self.highestres_cb.IsChecked
                )
            forms.alert('Pattern {} exported.'.format(self.pat_name))
        else:
            patmaker.make_pattern(self.pat_name,
                                  line_tuples, domain,
                                  fillgrids=self.selected_fillgrids,
                                  scale=pat_scale,
                                  model_pattern=self.is_model_pat,
                                  allow_expansion=self.highestres_cb.IsChecked,
                                  create_filledregion=self.create_filledregion)
            forms.alert('Pattern {} created/updated.'.format(self.pat_name))

    def verify_name(self):
        if not self.pat_name:
            forms.alert('Type a name for the pattern first')
            return False
        elif not re.search('[a-zA-Z0-9]', self.pat_name):
            forms.alert('Pattern name must have at least '
                        'one character or digit')
            return False
        elif self.pat_name.lower() in readonly_patterns:
            forms.alert('Read-Only pattern with name "{}" already exists '
                        .format(self.pat_name))
            return False
        return True

    def target_changed(self, sender, args):
        self.setup_patnames_combobox(model=self.is_model_cb.IsChecked)

    def export_pat(self, sender, args):
        if self._export_only:
            self.Close()
            export_dir = forms.pick_folder()
            if export_dir:
                self.export_pattern(export_dir)
        elif self.verify_name():
            self.Hide()
            domain = self.pick_domain()
            export_dir = forms.pick_folder()
            if domain and export_dir:
                self.create_pattern(domain,
                                    export_only=True,
                                    export_path=export_dir)
            self.Close()

    def make_pattern(self, sender, args):
        if self.verify_name():
            self.Hide()
            domain = self.pick_domain()
            if domain:
                self.create_pattern(domain)
            self.Close()


MakePatternWindow('MakePatternWindow.xaml',
                  selection.elements).show(modal=True)
