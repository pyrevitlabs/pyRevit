# pylint: disable=C0111,E0401,C0103,W0201,W0613
import math

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script
from pyrevit.framework import Media

from System.Windows.Shapes import Line, Rectangle


logger = script.get_logger()
output = script.get_output()

MODEL_SCALE = 400.0
DRAFTING_SCALE = 4000.0
MAX_LINES_PER_GRID = 250
LINE_THICKNESS = 1.0
MIN_DASH = 1e-6


def _round_cap_dashes(segments, thickness):
    if len(segments) % 2:
        return [max(segment, MIN_DASH) for segment in segments]
    dashes = []
    for index in range(0, len(segments), 2):
        dash = max(segments[index] - thickness, MIN_DASH)
        dashes.append(dash)
        dashes.append(segments[index + 1] + segments[index] - dash)
    return dashes


def _dash_array(segments, thickness):
    dashes = Media.DoubleCollection()
    for dash in _round_cap_dashes(segments, thickness):
        dashes.Add(dash / thickness)
    return dashes


def _grid_lines(fill_grid, scale, radius):
    direction = (math.cos(fill_grid.Angle), math.sin(fill_grid.Angle))
    normal = (-direction[1], direction[0])
    origin = (fill_grid.Origin.U, fill_grid.Origin.V)
    step = (
        fill_grid.Offset * normal[0] + fill_grid.Shift * direction[0],
        fill_grid.Offset * normal[1] + fill_grid.Shift * direction[1],
    )
    reach = radius / scale
    base_distance = origin[0] * normal[0] + origin[1] * normal[1]
    bounds = sorted(
        [
            (-reach - base_distance) / fill_grid.Offset,
            (reach - base_distance) / fill_grid.Offset,
        ]
    )
    first = int(math.ceil(bounds[0]))
    last = int(math.floor(bounds[1]))
    stride = max(1, int(math.ceil((last - first + 1) / float(MAX_LINES_PER_GRID))))
    for index in range(first, last + 1, stride):
        base = (origin[0] + index * step[0], origin[1] + index * step[1])
        start = -(base[0] * direction[0] + base[1] * direction[1]) - reach
        end = start + 2 * reach
        yield (
            (base[0] + start * direction[0], base[1] + start * direction[1]),
            (base[0] + end * direction[0], base[1] + end * direction[1]),
            start,
        )


class TestFillPatternViewer(forms.WPFWindow):
    resolve_theme = True

    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self.pat_name_cb.ItemsSource = sorted(
            [
                x.GetFillPattern().Name
                for x in revit.query.get_all_fillpattern_elements(
                    DB.FillPatternTarget.Drafting
                )
            ]
        )
        self.pat_name_cb.SelectedIndex = 0

    def fill_pattern_changed(self, sender, args):
        selected_fillpattern = revit.query.get_fillpattern_element(
            self.pat_name_cb.SelectedItem, DB.FillPatternTarget.Drafting
        ).GetFillPattern()
        if selected_fillpattern:
            self._draw_fill_pattern(selected_fillpattern)

    def _pattern_brush(self):
        brush = self.TryFindResource("pyRevitWindowForegroundBrush")
        return brush if brush is not None else Media.Brushes.Black

    def _draw_fill_pattern(self, fill_pattern):
        canvas = self.fillpattern_canvas
        canvas.Children.Clear()
        brush = self._pattern_brush()
        width = canvas.Width
        height = canvas.Height

        if fill_pattern.IsSolidFill:
            solid = Rectangle()
            solid.Width = width
            solid.Height = height
            solid.Fill = brush
            canvas.Children.Add(solid)
            return

        if fill_pattern.Target == DB.FillPatternTarget.Model:
            scale = MODEL_SCALE
        else:
            scale = DRAFTING_SCALE
        radius = math.hypot(width, height) / 2.0

        for fill_grid in fill_pattern.GetFillGrids():
            if fill_grid.Offset == 0:
                continue
            segments = list(fill_grid.GetSegments())
            period = sum(segments)
            for start_point, end_point, start in _grid_lines(fill_grid, scale, radius):
                line = Line()
                line.X1 = width / 2.0 + start_point[0] * scale
                line.Y1 = height / 2.0 - start_point[1] * scale
                line.X2 = width / 2.0 + end_point[0] * scale
                line.Y2 = height / 2.0 - end_point[1] * scale
                line.Stroke = brush
                line.StrokeThickness = LINE_THICKNESS
                if period > 0:
                    line.StrokeDashCap = Media.PenLineCap.Round
                    line.StrokeDashArray = _dash_array(
                        [x * scale for x in segments], LINE_THICKNESS
                    )
                    line.StrokeDashOffset = (
                        (start % period) * scale - LINE_THICKNESS / 2.0
                    ) / LINE_THICKNESS
                canvas.Children.Add(line)


TestFillPatternViewer("TestFillPatternViewer.xaml").show(modal=True)
