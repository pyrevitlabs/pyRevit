from math import sqrt, cos, pi, tan

from pyrevit import PyRevitException
from pyrevit.coreutils.logger import get_logger
from revitutils import doc

# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction, FillPattern, FillPatternElement, FillGrid, \
                              FillPatternTarget, FillPatternHostOrientation, UV, XYZ


logger = get_logger(__name__)


RESOLUTION = 4
PI = pi
HALF_PI = pi/2
MAX_SPAN_TRY = 20000
ZERO_TOL = 5 / 10.0**RESOLUTION


class CanNotDetermineSpanException(PyRevitException):
    pass


class PatternPoint:
    def __init__(self, u_point, v_point):
        self.u = u_point
        self.v = v_point

    def __repr__(self):
        return '<PatternPoint U:{} V:{}>'.format(self.u, self.v)

    def __eq__(self, other):
        return self.u == other.u and self.v == other.v

    def __hash__(self):
        return hash(self.u + self.v)

    def distance_to(self, point):
        return sqrt((point.u - self.u)**2 + (point.v - self.v)**2)


class PatternLine:
    def __init__(self, start_p, end_p, line_id=None):
        self.start_point = start_p if start_p.v <= end_p.v else end_p
        self.end_point = end_p if start_p.v <= end_p.v else start_p
        self.id = line_id

    def __repr__(self):
        return '<PatternLine Start:{} End:{} Length:{}>'.format(self.start_point, self.end_point, self.length)

    @property
    def direction(self):
        return PatternPoint(self.end_point.u - self.start_point.u, self.end_point.v - self.start_point.v)

    @property
    def angle(self):
        dir_vect = XYZ(self.direction.u, self.direction.v,0)
        return dir_vect.AngleTo(XYZ(1,0,0))

    @property
    def center_point(self):
        return PatternPoint((self.end_point.u + self.start_point.u)/2.0, (self.end_point.v + self.start_point.v)/2.0)

    @property
    def length(self):
        return abs(sqrt(self.direction.u**2 + self.direction.v**2))

    def point_on_line(self, point):
        a = self.start_point
        b = self.end_point
        c = point
        if (a.u - c.u) * (b.v - c.v) - (a.v - c.v) * (b.u - c.u) == 0:
            return True
        else:
            return False

    def intersect(self, pat_line):
        xdiff = PatternPoint(self.start_point.u - self.end_point.u, pat_line.start_point.u - pat_line.end_point.u)
        ydiff = PatternPoint(self.start_point.v - self.end_point.v, pat_line.start_point.v - pat_line.end_point.v)

        def det(a, b):
            return a.u * b.v - a.v * b.u

        div = det(xdiff, ydiff)
        if div == 0:
           raise Exception('lines do not intersect')

        d = PatternPoint(det(self.start_point, self.end_point), det(pat_line.start_point, pat_line.end_point))
        int_point_x = det(d, xdiff) / div
        int_point_y = det(d, ydiff) / div

        return PatternPoint(int_point_x, int_point_y)


class PatternGridAxis:
    def __init__(self, line, pat_domain):
        self._init_line = line
        self._pat_domain = pat_domain

        start_point, end_point = self._intersect_with_domain(self._init_line)
        self.axis = PatternLine(start_point, end_point)
        self.angle = self.axis.angle
        self.small_angle_u_side = (self.axis.angle <= HALF_PI/2)

        self.span = self._get_span()
        self.shift = self._get_shift()
        self.offset = self._get_offset()

        self.segment_lines = [self._init_line]

    def __repr__(self):
        return '<PatternGridAxis Axis:{} Angle:{} Offset:{} Shift:{} ' \
               'Span:{} Origin:{} Segments:{}>'.format(self.axis, self.angle, self.offset, self.shift,
                                                       self.span, self.origin, self.segments)

    def _intersect_with_domain(self, line):
        boundary_lines = [PatternLine(PatternPoint(0, 0), PatternPoint(self._pat_domain.u, 0)),
                          PatternLine(PatternPoint(0, 0), PatternPoint(0, self._pat_domain.v)),
                          PatternLine(PatternPoint(self._pat_domain.u, 0),
                                      PatternPoint(self._pat_domain.u, self._pat_domain.v)),
                          PatternLine(PatternPoint(0, self._pat_domain.v),
                                      PatternPoint(self._pat_domain.u, self._pat_domain.v))]
        intersect_points = []
        for boundary_line in boundary_lines:
            try:
                intersect_points.append(line.intersect(boundary_line))
            except Exception as intersect_err:
                logger.debug(intersect_err)

        extent_points = set()
        for point in intersect_points:
            # only two point should pass this test
            if 0 <= point.u <= self._pat_domain.u \
            and 0 <= point.v <= self._pat_domain.v:
                extent_points.add(point)

        logger.debug('For axis: {} Intersect points are: {}'.format(line, extent_points))
        return sorted(extent_points)

    def _get_span(self):
        if self.small_angle_u_side:
            if 0.0 <= self.angle < ZERO_TOL:
                return self._pat_domain.u
            else:
                small_angle_dom_length = self._pat_domain.u
                large_angle_dom_length = self._pat_domain.v
                inside_ang = HALF_PI - self.angle
        else:
            if 0.0 <= HALF_PI - self.angle < ZERO_TOL:
                return self._pat_domain.v
            else:
                large_angle_dom_length = self._pat_domain.u
                small_angle_dom_length = self._pat_domain.v
                inside_ang = self.angle

        rep_count = 1
        tolerance = small_angle_dom_length / 50.0
        large_angle_side_rep = large_angle_dom_length * rep_count
        small_angle_side_rep = large_angle_side_rep * tan(inside_ang)
        while round(small_angle_side_rep, RESOLUTION) % small_angle_dom_length > tolerance and rep_count < MAX_SPAN_TRY:
            rep_count += 1
            large_angle_side_rep = large_angle_dom_length * rep_count
            small_angle_side_rep = large_angle_side_rep * tan(inside_ang)

        if rep_count < MAX_SPAN_TRY:
            self.tile_count = rep_count
            return abs(round(large_angle_side_rep / cos(inside_ang), RESOLUTION))
        else:
            raise CanNotDetermineSpanException()

    def _get_offset(self):
        if self.small_angle_u_side:
            if 0.0 <= self.angle < ZERO_TOL:
                return self._pat_domain.u
            else:
                return abs(round(self._pat_domain.u * cos(HALF_PI - self.angle), RESOLUTION))
        else:
            if 0.0 <= HALF_PI - self.angle < ZERO_TOL:
                return self._pat_domain.v
            else:
                return abs(round(self._pat_domain.v * cos(PI - self.angle), RESOLUTION))

    def _get_shift(self):
        if self.small_angle_u_side:
            return -round(self._pat_domain.u * cos(self.angle), RESOLUTION)
        else:
            return -round(self._pat_domain.v * cos(HALF_PI - self.angle), RESOLUTION)

    def _overlap_line(self, pat_line):
        # see if pat_line overlaps, if yes:
        start_check = self.axis.point_on_line(pat_line.start_point)
        end_check = self.axis.point_on_line(pat_line.end_point)
        if start_check and end_check:
            logger.debug('Line {} overlaps with axis: {}'.format(pat_line, self.axis))
            self.segment_lines.append(pat_line)
            return True
        else:
            return False

    def _get_merged_lines(self):
        return self.segment_lines

    @property
    def origin(self):
        point_list = []
        for seg_line in self.segment_lines:
            point_list.extend([seg_line.start_point, seg_line.end_point])

        least_dist = self.axis.length
        closest_point = None
        for point in point_list:
            dist = point.distance_to(self.axis.start_point)
            if dist < least_dist:
                least_dist = dist
                closest_point = point

        return closest_point

    @property
    def segments(self):
        line = self._get_merged_lines()[0]
        segment_list = [line.length, self.span - line.length]
        return segment_list

    def add_segment(self, line):
        return self._overlap_line(line)

    def get_fill_grid(self, scale):
        fg = FillGrid()
        fg.Angle = self.angle
        fg.Origin = UV(self.origin.u * scale, self.origin.v * scale)
        fg.Offset = self.offset * scale
        fg.Shift = self.shift * scale
        scaled_segments = [seg * scale for seg in self.segments]
        fg.SetSegments(scaled_segments)
        return fg


def _make_rvt_fillpattern(fill_pat):
    with Transaction(doc, 'Create Fill Pattern') as t:
        t.Start()
        fill_pat_element = FillPatternElement.Create(doc, fill_pat)
        logger.debug('Created FillPatternElement with id:{}'.format(fill_pat_element.Id))
        t.Commit()


def make_pattern(pat_name, line_list, pat_domain, model_pattern=True, dot_threshold=0.1, scale=1.0):
    # make the FillGrids
    grid_axes_list = []
    for line in line_list:
        # check if line is overlapping any current grid axes
        line_accepted = False
        for grid_axis in grid_axes_list:
            if grid_axis.add_segment(line):
                line_accepted = True
                print 'accepted {}'.format(line)
                break
        # if not, then define a new grid axis
        if not line_accepted:
            try:
                new_axis = PatternGridAxis(line, pat_domain)
                print new_axis
                logger.debug('New pattern axis: {}'.format(new_axis))
                grid_axes_list.append(new_axis)
            except CanNotDetermineSpanException:
                logger.error('Error determining span on line id: {}'.format(line.id))

    # get list of FillGrids
    fill_grids = [seg.get_fill_grid(scale) for seg in grid_axes_list]

    # Make new FillPattern
    fp_target = FillPatternTarget.Model if model_pattern else FillPatternTarget.Drafting
    fill_pat = FillPattern(pat_name, fp_target, FillPatternHostOrientation.ToHost)
    # Apply the FillGrids
    fill_pat.SetFillGrids(List[FillGrid](fill_grids))

    # Create the FillPatternElement in current document
    _make_rvt_fillpattern(fill_pat)
