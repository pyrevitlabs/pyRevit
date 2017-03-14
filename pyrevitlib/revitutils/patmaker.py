import os.path as op
from math import sqrt, pi, sin, cos, degrees

from pyrevit import PyRevitException
from pyrevit.coreutils import cleanup_filename
from pyrevit.coreutils.logger import get_logger
from revitutils import doc
from revitutils import typeutils

# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction, FillPattern, FillPatternElement, FillGrid, \
                              FillPatternTarget, FillPatternHostOrientation, UV


logger = get_logger(__name__)


PI = pi
HALF_PI = PI/2.0
ZERO_TOL = 5e-06

MAX_DOMAIN = 100.0

DOT_TYPES = ['Line Segment', u'\u2795', u'\u274C', u'Diamond \u25C7', u'\u25EF']


PAT_SEPARATOR = ', '
PAT_FILE_TEMPLATE = ";        Written by \"Make Pattern\" tool for pyRevit\n"                             \
                    ";          http://eirannejad.github.io/pyRevit/\n"                                   \
                    ";-Date                                   : {date}\n"                                 \
                    ";-Time                                   : {time}\n"                                 \
                    ";-pyRevit Version                        : {version}\n"                              \
                    ";-----------------------------------------------------------------------------\n"    \
                    ";%UNITS=INCH\n"                                                                      \
                    "*{name},created by pyRevit\n"                                                        \
                    ";%TYPE={type}\n"


class _PatternPoint:
    def __init__(self, u_point, v_point):
        self.u = u_point
        self.v = v_point

    def __repr__(self):
        return '<_PatternPoint U:{0:.20f} V:{1:.20f}>'.format(self.u, self.v)

    def __eq__(self, other):
        return self.u == other.u and self.v == other.v

    def __hash__(self):
        # todo: come up with method for sorting lines
        return hash(self.u + self.v)

    def __add__(self, other):
        return _PatternPoint(self.u + other.u, self.v + other.v)

    def __sub__(self, other):
        return _PatternPoint(self.u - other.u, self.v - other.v)

    def distance_to(self, point):
        return sqrt((point.u - self.u)**2 + (point.v - self.v)**2)

    def rotate(self, origin, angle):
        tu = self.u - origin.u
        tv = self.v - origin.v
        self.u = origin.u + (tu*cos(angle) - tv*sin(angle))
        self.v = origin.v + (tu*sin(angle) + tv*cos(angle))
        return True


class _PatternLine:
    def __init__(self, start_p, end_p):
        """

        Args:
            start_p (_PatternPoint):
            end_p (_PatternPoint):
        """
        self.start_point = start_p if start_p.v <= end_p.v else end_p
        self.end_point = end_p if start_p.v <= end_p.v else start_p
        self.u_vector = UV(1, 0)

    def __repr__(self):
        return '<_PatternLine Start:{} End:{} Length:{} Angle:{}>'.format(self.start_point, self.end_point,
                                                                          self.length, self.angle)

    @property
    def direction(self):
        return _PatternPoint(self.end_point.u - self.start_point.u, self.end_point.v - self.start_point.v)

    @property
    def angle(self):
        # always return angle to u direction
        # todo: fix and use actual math for angles to remove revit dependency
        return self.u_vector.AngleTo(UV(self.direction.u, self.direction.v))

    @property
    def center_point(self):
        return _PatternPoint((self.end_point.u + self.start_point.u)/2.0, (self.end_point.v + self.start_point.v)/2.0)

    @property
    def length(self):
        return abs(sqrt(self.direction.u**2 + self.direction.v**2))

    def point_on_line(self, point, tolerance=ZERO_TOL):
        a = self.start_point
        b = self.end_point
        c = point
        if 0.0 <= abs((a.u - c.u) * (b.v - c.v) - (a.v - c.v) * (b.u - c.u)) <= tolerance:
            return True
        else:
            return False

    def intersect(self, pat_line):
        xdiff = _PatternPoint(self.start_point.u - self.end_point.u, pat_line.start_point.u - pat_line.end_point.u)
        ydiff = _PatternPoint(self.start_point.v - self.end_point.v, pat_line.start_point.v - pat_line.end_point.v)

        def det(a, b):
            return a.u * b.v - a.v * b.u

        div = det(xdiff, ydiff)
        if div == 0:
            raise PyRevitException('Lines do not intersect.')

        d = _PatternPoint(det(self.start_point, self.end_point), det(pat_line.start_point, pat_line.end_point))
        int_point_x = det(d, xdiff) / div
        int_point_y = det(d, ydiff) / div

        return _PatternPoint(int_point_x, int_point_y)

    def rotate(self, origin, angle):
        self.start_point.rotate(origin, angle)
        self.end_point.rotate(origin, angle)


class _PatternSafeGrid:
    def __init__(self, domain, diag_angle, u_tiles, v_tiles, flipped=False):
        self._domain = domain
        self._flipped = flipped
        self._diag_angle = diag_angle
        # find out the axis line to calculate angle and length
        self._axis_line = _PatternLine(_PatternPoint(0, 0),
                                       _PatternPoint(self._domain.u * u_tiles, self._domain.v * v_tiles))
        # now determine the parameters necessary to calculate span, offset, and shift
        self._determine_abstract_params(u_tiles, v_tiles)
        self._verify_repeatability()

    def __eq__(self, other):
        return 0 <= self.grid_angle - other.grid_angle <= ZERO_TOL

    def __hash__(self):
        return hash(self.grid_angle)

    def _determine_abstract_params(self, u_tiles, v_tiles):
        if self._axis_line.angle <= self._diag_angle:
            if not self._flipped:
                self._offset_direction = -1.0
            else:
                self._offset_direction = 1.0

            self._angle = self._axis_line.angle
            self._u_tiles = u_tiles
            self._v_tiles = v_tiles
            self._domain_u = self._domain.u
            self._domain_v = self._domain.v

        else:
            if not self._flipped:
                self._offset_direction = 1.0
            else:
                self._offset_direction = -1.0

            self._angle = HALF_PI - self._axis_line.angle if not self._flipped else self._axis_line.angle - HALF_PI
            self._u_tiles = v_tiles
            self._v_tiles = u_tiles
            self._domain_u = self._domain.v
            self._domain_v = self._domain.u

    def _verify_repeatability(self):
        return self.shift

    def __repr__(self):
        return '<_PatternSafeGrid GridAngle:{} Angle:{} U_Tiles:{} V_Tiles:{} ' \
               'Domain_U:{} Domain_V:{} Offset_Dir:{} ' \
               'Span:{} Offset:{} Shift:{}>'.format(self.grid_angle, self._angle, self._u_tiles, self._v_tiles,
                                                    self._domain_u, self._domain_v, self._offset_direction,
                                                    self.span, self.offset, self.shift)

    @property
    def grid_angle(self):
        return self._axis_line.angle if not self._flipped else PI - self._axis_line.angle

    @property
    def span(self):
        return self._axis_line.length

    @property
    def offset(self):
        if self._angle == 0.0:
            return self._domain_v * self._offset_direction
        else:
            return abs(self._domain_u * sin(self._angle) / self._v_tiles) * self._offset_direction

    @property
    def shift(self):
        if self._angle == 0.0:
            return 0

        def find_nxt_grid_point(offset_line):
            u_mult = 0
            while u_mult < self._u_tiles:
                for v_mult in range(0, self._v_tiles):
                    grid_point = _PatternPoint(self._domain_u * u_mult, self._domain_v * v_mult)
                    if offset_line.point_on_line(grid_point):
                        return grid_point
                u_mult += 1
            if u_mult >= self._u_tiles:
                raise PyRevitException('Can not determine next repeating grid.')

        if self._u_tiles == self._v_tiles == 1:
            return abs(self._domain_u * cos(self._angle))
        else:
            # calculate the abstract offset axis
            offset_u = abs(self.offset * sin(self._angle))
            offset_v = -abs(self.offset * cos(self._angle))
            offset_vector = _PatternPoint(offset_u, offset_v)
            # find the offset line
            abstract_axis_start_point = _PatternPoint(0, 0)
            abstract_axis_end_point = _PatternPoint(self._domain_u * self._u_tiles, self._domain_v * self._v_tiles)
            offset_vector_start = abstract_axis_start_point + offset_vector
            offset_vector_end = abstract_axis_end_point + offset_vector
            offset_axis = _PatternLine(offset_vector_start, offset_vector_end)

            # try to find the next occurance on the abstract offset axis
            nxt_grid_point = find_nxt_grid_point(offset_axis)

            total_shift = offset_axis.start_point.distance_to(nxt_grid_point)
            return total_shift


class _PatternDomain:
    def __init__(self, start_u, start_v, end_u, end_v):
        self._origin = _PatternPoint(min(start_u, end_u), min(start_v, end_v))
        self._corner = _PatternPoint(max(start_u, end_u), max(start_v, end_v))
        self._domain = self._corner - self._origin
        if self._zero_domain():
            raise PyRevitException('Can not process zero domain.')

        self.u_vec = _PatternLine(_PatternPoint(0, 0), _PatternPoint(self._domain.u, 0))
        self.v_vec = _PatternLine(_PatternPoint(0, 0), _PatternPoint(0, self._domain.v))

        self.diagonal = _PatternLine(_PatternPoint(0.0, 0.0), _PatternPoint(self._domain.u, self._domain.v))

        self.safe_angles = []
        self._calculate_safe_angles()

    def __repr__(self):
        return '<_PatternDomain U:{} V:{} SafeAngles:{}>'.format(self._domain.u,
                                                                 self._domain.v,
                                                                 len(self.safe_angles))

    def _zero_domain(self):
        return self._domain.u == 0 or self._domain.v == 0

    def _calculate_safe_angles(self):
        # setup tile counters
        u_mult = v_mult = 1

        # add standard angles to the list
        self.safe_angles.append(_PatternSafeGrid(self._domain, self.diagonal.angle, u_mult, 0))
        self.safe_angles.append(_PatternSafeGrid(self._domain, self.diagonal.angle, u_mult, 0, flipped=True))
        self.safe_angles.append(_PatternSafeGrid(self._domain, self.diagonal.angle, u_mult, v_mult))
        self.safe_angles.append(_PatternSafeGrid(self._domain, self.diagonal.angle, u_mult, v_mult, flipped=True))
        self.safe_angles.append(_PatternSafeGrid(self._domain, self.diagonal.angle, 0, v_mult))

        # traverse the tile space and add safe grids to the list
        processed_ratios = [1.0]
        while self._domain.u * u_mult <= MAX_DOMAIN/2.0:
            while self._domain.v * v_mult <= MAX_DOMAIN/2.0:
                if float(v_mult)/float(u_mult) not in processed_ratios:
                    # for every tile, also add the mirrored tile
                    try:
                        angle1 = _PatternSafeGrid(self._domain, self.diagonal.angle, u_mult, v_mult)
                        angle2 = _PatternSafeGrid(self._domain, self.diagonal.angle, u_mult, v_mult, flipped=True)
                        self.safe_angles.append(angle1)
                        self.safe_angles.append(angle2)
                        processed_ratios.append(float(v_mult)/float(u_mult))
                    except PyRevitException:
                        logger.warning('Skipping safe angle for grid point U:{} V:{}'.format(u_mult, v_mult))
                v_mult += 1
            v_mult = 1
            u_mult += 1

    def get_domain_coords(self, pat_line):
        return _PatternLine(pat_line.start_point - self._origin, pat_line.end_point - self._origin)

    def get_grid_params(self, axis_angle):
        return min(self.safe_angles, key=lambda x: abs(x.grid_angle - axis_angle))


class _PatternGrid:
    def __init__(self, pat_domain, init_line):
        self._domain = pat_domain
        self._grid = self._domain.get_grid_params(init_line.angle)
        logger.debug('Closest safe angle is: {}'.format(self._grid))
        self.angle = self._grid.grid_angle
        self.span, self.offset, self.shift = self._grid.span, self._grid.offset, self._grid.shift

        self.segment_lines = []
        init_line.rotate(init_line.center_point, self.angle - init_line.angle)
        self.segment_lines.append(init_line)

    def __repr__(self):
        return '<_PatternGrid Angle:{} Span:{} Offset:{} Shift:{}>'.format(self.angle, self.span,
                                                                           self.offset, self.shift)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def adopt_line(self, pat_line):
        # todo: optimise grid creation. check overlap and combine overlapping lines into one grid
        return False

    @property
    def origin(self):
        # collect all line segment points
        point_list = []
        for seg_line in self.segment_lines:
            point_list.extend([seg_line.start_point, seg_line.end_point])

        # origin is the point that is closest to zero
        if self.angle <= HALF_PI:
            return min(point_list, key=lambda x: x.distance_to(_PatternPoint(0, 0)))
        else:
            return min(point_list, key=lambda x: x.distance_to(_PatternPoint(self._domain.u_vec.length, 0)))

    @property
    def segments(self):
        pen_down = self.segment_lines[0].length
        return [pen_down, self.span - pen_down]

    @property
    def segments_as_lines(self):
        # todo: see _RevitPattern.adjust_line()
        return self.segment_lines


class _RevitPattern:
    def __init__(self, pat_domain, pat_name, model_pat=True, scale=1.0):
        self._domain = pat_domain
        self._pattern_grids = []

        self._name = pat_name
        self._model_pat = model_pat
        self._scale = scale

    def __repr__(self):
        return '<_RevitPattern Name:{} Model:{} Scale:{}>'.format(self._name, self._model_pat, self._scale)

    def append_line(self, pat_line):
        # get line in current domain
        domain_line = self._domain.get_domain_coords(pat_line)
        logger.debug('New domain line: {}'.format(domain_line))
        # check if line overlaps any of existing grids
        for pat_grid in self._pattern_grids:
            if pat_grid.adopt_line(domain_line):
                return True
        # if line does not overlap any of existing grids, create new grid
        new_grid = _PatternGrid(self._domain, domain_line)
        logger.debug('New pattern grid: {}'.format(new_grid))
        self._pattern_grids.append(new_grid)

    def adjust_line(self, pat_line):
        # todo:
        # create a pat_grid with pat_line
        # ask for segments_as_lines and return first line
        pass

    @property
    def name(self):
        return self._name

    @staticmethod
    def _make_fill_grid(pattern_grid, scale):
        rvt_fill_grid = FillGrid()
        rvt_fill_grid.Angle = pattern_grid.angle
        rvt_fill_grid.Origin = UV(pattern_grid.origin.u * scale, pattern_grid.origin.v * scale)
        rvt_fill_grid.Offset = pattern_grid.offset * scale
        rvt_fill_grid.Shift = pattern_grid.shift * scale
        if pattern_grid.segments:
            scaled_segments = [seg * scale for seg in pattern_grid.segments]
            rvt_fill_grid.SetSegments(scaled_segments)
        return rvt_fill_grid

    @staticmethod
    def _make_fillpattern_element(rvt_fill_pat):
        with Transaction(doc, 'Create Fill Pattern') as t:
            t.Start()
            fill_pat_element = FillPatternElement.Create(doc, rvt_fill_pat)
            logger.debug('Created FillPatternElement with id:{}'.format(fill_pat_element.Id))
            t.Commit()

        logger.debug('Fill Pattern:{}'.format(fill_pat_element.Name))
        fp = fill_pat_element.GetFillPattern()
        logger.debug('Fill Grids Count: {}'.format(len(fp.GetFillGrids())))
        for idx, fg in enumerate(fp.GetFillGrids()):
            logger.debug('FillGrid #{} '
                         'Origin:{} Angle:{} Shift:{} Offset:{} Segments:{}'.format(idx, fg.Origin,
                                                                                    fg.Angle, fg.Shift,
                                                                                    fg.Offset, fg.GetSegments()))
        return fill_pat_element

    def create_pattern(self):
        fill_grids = [self._make_fill_grid(pat_grid, self._scale) for pat_grid in self._pattern_grids]

        # Make new FillPattern
        fp_target = FillPatternTarget.Model if self._model_pat else FillPatternTarget.Drafting
        fill_pat = FillPattern(self._name, fp_target, FillPatternHostOrientation.ToHost)

        # Apply the FillGrids
        fill_pat.SetFillGrids(List[FillGrid](fill_grids))

        # Create the FillPatternElement in current document
        return self._make_fillpattern_element(fill_pat)

    def get_pat_data(self):
        pat_type = 'MODEL' if self._model_pat else 'DRAFTING'
        pattern_desc = PAT_FILE_TEMPLATE.format(time='0', date='0', version='0', name=self._name, type=pat_type)
        for pat_grid in self._pattern_grids:
            grid_desc = PAT_SEPARATOR.join([str(degrees(pat_grid.angle)),
                                            str(pat_grid.origin.u * self._scale), str(pat_grid.origin.v * self._scale),
                                            str(pat_grid.shift * self._scale),
                                            str(pat_grid.offset * self._scale)])
            grid_desc += PAT_SEPARATOR
            if pat_grid.segments:
                scaled_segments = []
                for idx, seg in enumerate(pat_grid.segments):
                    if idx%2 != 0:
                        seg = seg * -1
                    scaled_segments.append(seg * self._scale)

                grid_desc += PAT_SEPARATOR.join([str(seg_l) for seg_l in scaled_segments])

            pattern_desc += grid_desc + '\n'

        return pattern_desc


def _export_pat(revit_pat, export_dir):
    pat_file_contents = revit_pat.get_pat_data()
    with open(op.join(export_dir, '{}.pat'.format(cleanup_filename(revit_pat.name))), 'w') as pat_file:
        pat_file.write(pat_file_contents)


def _create_fill_pattern(revit_pat, create_filledregion=False):
    try:
        fillpat_element = revit_pat.create_pattern()
        if create_filledregion:
            typeutils.make_filledregion(fillpat_element.Name, fillpat_element.Id)
        return fillpat_element
    except Exception as create_pat_err:
        logger.error('Error creating pattern element. | {}'.format(create_pat_err))


def _make_rvt_pattern(pat_name, pat_lines, domain, model_pattern=True, scale=1.0):
    pat_domain = _PatternDomain(domain[0][0], domain[0][1], domain[1][0], domain[1][1])
    logger.debug('New pattern domain: {}'.format(pat_domain))

    revit_pat = _RevitPattern(pat_domain, pat_name, model_pattern, scale)
    logger.debug('New revit pattern: {}'.format(revit_pat))

    for line_coords in pat_lines:
        startp = _PatternPoint(line_coords[0][0], line_coords[0][1])
        endp = _PatternPoint(line_coords[1][0], line_coords[1][1])
        pat_line = _PatternLine(startp, endp)
        try:
            revit_pat.append_line(pat_line)
        except Exception as pat_line_err:
            logger.error('Error adding line: {} | {}'.format(line_coords, pat_line_err))

    return revit_pat


def make_pattern(pat_name, pat_lines, domain, model_pattern=True, create_filledregion=False, scale=1.0):
    revit_pat = _make_rvt_pattern(pat_name, pat_lines, domain, model_pattern, scale)
    return _create_fill_pattern(revit_pat, create_filledregion)


def export_pattern(pat_name, pat_lines, domain, export_dir, model_pattern=True, scale=12.0):
    revit_pat = _make_rvt_pattern(pat_name, pat_lines, domain, model_pattern, scale)
    return _export_pat(revit_pat, export_dir)


# noinspection PyUnusedLocal
def adjust_pattern_lines(pat_lines, domain):
    # create the domain
    # create pattern
    # make a list of corrected lines
    # iterate over lines
        # for every line tuple info, call _RevitPattern.adjust_line() on the line
        # add to the corrected lines list in tuple format

    # return corrected lines
    pass
