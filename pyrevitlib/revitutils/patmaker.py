from math import sqrt, pi, sin, cos, tan

from pyrevit import PyRevitException
from pyrevit.coreutils.logger import get_logger
from revitutils import doc

# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction, FillPattern, FillPatternElement, FillGrid, \
                              FillPatternTarget, FillPatternHostOrientation, UV, XYZ


logger = get_logger(__name__)


PI = pi
HALF_PI = PI/2.0
RESOLUTION = 4
COORD_RESOLUTION = 10
ZERO_TOL = 5 / 10.0**RESOLUTION
MAX_TRY = 20000
MAX_DOMAIN = 200
MAX_JIGGLE = 16


class CanNotDetermineSpanException(PyRevitException):
    pass


class CanNotDetermineNextGridException(PyRevitException):
    pass


class PatternPoint:
    def __init__(self, u_point, v_point):
        self.u = round(u_point, COORD_RESOLUTION)
        self.v = round(v_point, COORD_RESOLUTION)

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

    def point_on_line(self, point, tolerance=0.0):
        a = self.start_point
        b = self.end_point
        c = point
        if 0.0 <= abs((a.u - c.u) * (b.v - c.v) - (a.v - c.v) * (b.u - c.u)) <= tolerance:
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
        # setting up domain bounds
        self._pat_domain = pat_domain
        self._dom_diag = PatternLine(PatternPoint(0.0, 0.0), PatternPoint(self._pat_domain.u, self._pat_domain.v))
        self._quarter_angle = self._dom_diag.angle
        self._threequart_angle = PI - self._dom_diag.angle

        # setup initial line to base axis on
        self._init_line = line
        self._pivot_point = self._init_line.center_point

        # set default values
        self.tile_count_prep = self.tile_count_base = 1
        self._shift_direction = self._offset_direction = 1

        # try finding axis
        try_count = 0
        self._setup_axis()
        while not self._determite_tri_params() and try_count < MAX_JIGGLE:
            # if cant jiggle init line and try again
            try_count += 1
            self._jiggle_axis(try_count)
            self._setup_axis()

        if try_count >= MAX_JIGGLE:
            raise PyRevitException('Can not find a decent approximate axis.')
        else:
            self.jiggle_count = try_count

        self.segment_lines = [self._init_line]

    def __repr__(self):
        return '<PatternGridAxis Axis:{} AxisAngle:{} uSide:{} ' \
               'Angle:{} Offset:{} Shift:{} Jiggle:{} ' \
               'Span:{} Tiles:{} Origin:{} Segments:{}>'.format(self.axis, self.axis.angle, self._is_small_angle_u_side(),
                                                                self.angle, self.offset, self.shift, self.jiggle_count,
                                                                self.span, self.tile_count_prep, self.origin, self.segments)

    def _is_small_angle_u_side(self):
        return (self.axis.angle <= self._quarter_angle) or (self.axis.angle >= self._threequart_angle)

    def _is_almost_right_angle(self):
        if self._is_small_angle_u_side():
            return 0.0 <= self.axis.angle < ZERO_TOL or PI - ZERO_TOL < self.axis.angle <= PI
        else:
            return HALF_PI - ZERO_TOL < abs(HALF_PI - self.axis.angle) < HALF_PI + ZERO_TOL

    def _determine_relative_vectors(self):
        if self._is_small_angle_u_side():
            self.dom_base_length = self._pat_domain.u
            self.dom_prep_length = self._pat_domain.v

            if self.axis.angle <= self._quarter_angle:
                self._offset_direction = -1.0
                self._shift_direction = 1.0
                if self._is_almost_right_angle():
                    self.angle = 0.0
                else:
                    self.angle = abs(self.axis.angle)
            elif self.axis.angle >= self._threequart_angle:
                self._offset_direction = 1.0
                self._shift_direction = 1.0
                if self._is_almost_right_angle():
                    self.angle = 0.0
                else:
                    self.angle = abs(PI - self.axis.angle)
        else:
            self.dom_base_length = self._pat_domain.v
            self.dom_prep_length = self._pat_domain.u

            if self._quarter_angle < self.axis.angle < HALF_PI:
                self._offset_direction = 1.0
                self._shift_direction = 1.0
            elif HALF_PI < self.axis.angle < self._threequart_angle:
                self._offset_direction = -1.0
                self._shift_direction = 1.0

            if self._is_almost_right_angle():
                self.angle = 0.0
            else:
                self.angle = abs(HALF_PI - self.axis.angle)

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
        if self.angle == 0.0:
            return self.dom_base_length
        elif round(self.angle, RESOLUTION) == round(self._quarter_angle, RESOLUTION):
            return self._dom_diag.length

        def calc_span_rem(rep_count):
            dom_prep_rep = self.dom_prep_length * rep_count
            return dom_prep_rep * tan(HALF_PI - self.angle)

        tolerance = self.dom_base_length / 100.0
        pos_tolerance = tolerance
        neg_tolerance = self.dom_base_length - tolerance
        def is_not_within_tolerance(dom_base_rep):
            rem = dom_base_rep % self.dom_base_length
            return not (neg_tolerance <= rem <= self.dom_base_length or 0.0 <= rem <= pos_tolerance)

        rep_count = 1
        while is_not_within_tolerance(calc_span_rem(rep_count)) and rep_count < MAX_TRY:
            rep_count += 1

        if rep_count < MAX_TRY:
            self.tile_count_prep = rep_count
            self.tile_count_base = round(calc_span_rem(rep_count) / self.dom_base_length, 0)
            return abs(calc_span_rem(rep_count) / cos(self.angle))
        else:
            raise CanNotDetermineSpanException()

    def _get_offset(self):
        if self.angle == 0.0:
            return self.dom_prep_length

        # offset_value = abs(self.dom_base_length * self.tile_count_base * sin(self.angle) / self.tile_count_prep)
        # return  offset_value * self._offset_direction
        return  abs(self.dom_base_length * sin(self.angle) / self.tile_count_prep) * self._offset_direction

    def _get_shift(self):
        def find_nxt_grid_point(offset_line, domain_u, domain_v, tol=5.0/10**RESOLUTION):
            u_mult = 0
            u_max = MAX_TRY
            while u_mult < u_max:
                for v_mult in range(0, MAX_TRY):
                    grid_point = PatternPoint(domain_u * u_mult, domain_v * v_mult)
                    if offset_line.point_on_line(grid_point, tolerance=tol):
                        return grid_point
                u_mult +=1
            if u_mult >= u_max:
                raise CanNotDetermineNextGridException()

        offset_u = abs(self.offset * sin(self.angle))
        offset_v = -abs(self.offset * cos(self.angle))
        offset_vector_start = PatternPoint(self.axis.start_point.u + offset_u, self.axis.start_point.v + offset_v)
        offset_vector_end = PatternPoint(self.axis.end_point.u + offset_u, self.axis.end_point.v + offset_v)
        offset_vector = PatternLine(offset_vector_start, offset_vector_end)

        if self.tile_count_prep > 1:
            nxt_grid_point = find_nxt_grid_point(offset_vector,
                                                 self.dom_base_length,
                                                 self.dom_prep_length)

            total_shift = offset_vector_start.distance_to(nxt_grid_point)
            return total_shift * self._shift_direction
        else:
            return abs(self.dom_base_length * cos(self.angle)) * self._shift_direction

    def _setup_axis(self):
        start_point, end_point = self._intersect_with_domain(self._init_line)
        self.axis = PatternLine(start_point, end_point)
        self._determine_relative_vectors()

    def _determite_tri_params(self):
        try:
            self.span = self._get_span()
            self.offset = self._get_offset()
            self.shift = self._get_shift()
            if self.span > MAX_DOMAIN or self.shift > MAX_DOMAIN:
                logger.debug('Calculated span is too wide for line id: {} | {}'.format(self._init_line.id, self.span))
                return False
            else:
                return True
        except Exception as calc_err:
            logger.debug('Error calculating tri params | {}'.format(calc_err))
            return False

    def _jiggle_axis(self, try_count):
        def rotate_point(origin, point, angle):
            qx = origin.u + cos(angle) * (point.u - origin.u) - sin(angle) * (point.v - origin.v)
            qy = origin.v + sin(angle) * (point.u - origin.u) + cos(angle) * (point.v - origin.v)
            return PatternPoint(qx, qy)

        if try_count%2 == 0:
            jiggle_mult = -try_count
        else:
            jiggle_mult = try_count

        rotate_increment = 0.01 * jiggle_mult
        new_start = rotate_point(self._init_line.center_point, self._init_line.start_point, rotate_increment)
        new_end = rotate_point(self._init_line.center_point, self._init_line.end_point, rotate_increment)
        self._init_line = PatternLine(new_start, new_end)

    def _overlap_line(self, pat_line):
        # see if pat_line overlaps, if yes:
        return False
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
        # segment_list = [0.05, 0.05, line.length - 0.1, self.span - line.length]
        segment_list = [line.length, self.span - line.length]
        return segment_list

    def add_segment(self, line):
        return self._overlap_line(line)

    def get_fill_grid(self, scale):
        fg = FillGrid()
        fg.Angle = self.axis.angle
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
            except Exception as gridaxis_err:
                logger.error('Error determining axis on line id: {} | {}'.format(line.id, gridaxis_err))

    # get list of FillGrids
    fill_grids = [seg.get_fill_grid(scale) for seg in grid_axes_list]

    # Make new FillPattern
    fp_target = FillPatternTarget.Model if model_pattern else FillPatternTarget.Drafting
    fill_pat = FillPattern(pat_name, fp_target, FillPatternHostOrientation.ToHost)
    # Apply the FillGrids
    fill_pat.SetFillGrids(List[FillGrid](fill_grids))

    # Create the FillPatternElement in current document
    _make_rvt_fillpattern(fill_pat)
