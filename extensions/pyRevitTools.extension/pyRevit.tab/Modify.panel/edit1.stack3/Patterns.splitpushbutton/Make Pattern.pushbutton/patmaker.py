"""Create patterns based on AutoCAD .pat standard."""
#pylint: disable=import-error,invalid-name
import os.path as op
import re
from math import sqrt, pi, sin, cos, degrees

from pyrevit import PyRevitException
from pyrevit import framework
from pyrevit.framework import List
from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import versionmgr


logger = coreutils.logger.get_logger(__name__)


PI = pi
HALF_PI = PI/2.0
ZERO_TOL = 5e-06

COORD_RESOLUTION = 16

# 0.5 < MODEL < 848.5 inches, source: http://hatchkit.com.au/faq.php#Tip7
MAX_MODEL_DOMAIN = 100.0

# 0.002 < DRAFTING < 84.85 inches
MAX_DETAIL_DOMAIN = MAX_MODEL_DOMAIN/10.0

MAX_DOMAIN_MULT = 8

RATIO_RESOLUTION = 2
ANGLE_CORR_RATIO = 0.01


PAT_SEPARATOR = ', '
PAT_FILE_TEMPLATE = \
    ";        Written by \"Make Pattern\" tool for pyRevit\n"                 \
    ";          http://eirannejad.github.io/pyRevit/\n"                       \
    ";-Date                                   : {date}\n"                     \
    ";-Time                                   : {time}\n"                     \
    ";-pyRevit Version                        : {version}\n"                  \
    ";---------------------------------------------------------------------\n"\
    ";%UNITS={units}\n"                                                       \
    "*{name},exported by pyRevit\n"                                            \
    ";%TYPE={type}\n"


def round_vector(length):
    length = length if abs(length) > ZERO_TOL else 0.0
    return round(length, COORD_RESOLUTION)


def flatten_zeros(length):
    length_str = ('{:.' + str(COORD_RESOLUTION) + 'f}').format(length)
    return re.sub(r'\.0+$', '.0', length_str)


class _PatternPoint:
    def __init__(self, u_point, v_point):
        self.u = round_vector(u_point)
        self.v = round_vector(v_point)

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

    def rotate(self, angle, origin=None):
        # default origin to 0,0 if not set
        origin = origin or _PatternPoint(0, 0)
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
        self.u_vector = DB.UV(1, 0)

    def __repr__(self):
        return '<_PatternLine Start:{} End:{} Length:{} Angle:{}>'\
               .format(self.start_point,
                       self.end_point,
                       self.length,
                       self.angle)

    @property
    def direction(self):
        return _PatternPoint(self.end_point.u - self.start_point.u,
                             self.end_point.v - self.start_point.v)

    @property
    def angle(self):
        # always return angle to u direction
        # todo: fix and use actual math for angles to remove revit dependency
        return self.u_vector.AngleTo(DB.UV(self.direction.u, self.direction.v))

    @property
    def center_point(self):
        return _PatternPoint((self.end_point.u + self.start_point.u)/2.0,
                             (self.end_point.v + self.start_point.v)/2.0)

    @property
    def length(self):
        return abs(sqrt(self.direction.u**2 + self.direction.v**2))

    def point_on_line(self, point, tolerance=ZERO_TOL):
        a = self.start_point
        b = self.end_point
        c = point
        if 0.0 <= abs((a.u - c.u) * (b.v - c.v)
                      - (a.v - c.v) * (b.u - c.u)) <= tolerance:
            return True
        else:
            return False

    def intersect(self, pat_line):
        xdiff = _PatternPoint(self.start_point.u - self.end_point.u,
                              pat_line.start_point.u - pat_line.end_point.u)
        ydiff = _PatternPoint(self.start_point.v - self.end_point.v,
                              pat_line.start_point.v - pat_line.end_point.v)

        def det(a, b):
            return a.u * b.v - a.v * b.u

        div = det(xdiff, ydiff)
        if div == 0:
            raise PyRevitException('Lines do not intersect.')

        d = _PatternPoint(det(self.start_point, self.end_point),
                          det(pat_line.start_point, pat_line.end_point))
        int_point_x = det(d, xdiff) / div
        int_point_y = det(d, ydiff) / div

        return _PatternPoint(int_point_x, int_point_y)

    def rotate(self, angle, origin=None):
        self.start_point.rotate(angle, origin=origin)
        self.end_point.rotate(angle, origin=origin)


class _PatternSafeGrid:
    def __init__(self, domain, diag_angle, u_tiles, v_tiles, flipped=False):
        self._domain = domain
        self._flipped = flipped
        self._diag_angle = diag_angle
        # find out the axis line to calculate angle and length
        self._axis_line = _PatternLine(_PatternPoint(0, 0),
                                       _PatternPoint(self._domain.u * u_tiles,
                                                     self._domain.v * v_tiles))
        # now determine the parameters necessary to
        # calculate span, offset, and shift
        self._determine_abstract_params(u_tiles, v_tiles)

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

            self._angle = \
                HALF_PI - self._axis_line.angle \
                if not self._flipped else self._axis_line.angle - HALF_PI
            self._u_tiles = v_tiles
            self._v_tiles = u_tiles
            self._domain_u = self._domain.v
            self._domain_v = self._domain.u

    def is_valid(self):
        return self.shift

    def __repr__(self):
        return '<_PatternSafeGrid GridAngle:{} Angle:{} '\
               'U_Tiles:{} V_Tiles:{} '\
               'Domain_U:{} Domain_V:{} Offset_Dir:{} '\
               'Span:{} Offset:{} Shift:{}>'\
               .format(self.grid_angle, self._angle,
                       self._u_tiles, self._v_tiles,
                       self._domain_u, self._domain_v, self._offset_direction,
                       self.span, self.offset, self.shift)

    @property
    def grid_angle(self):
        return self._axis_line.angle \
               if not self._flipped else PI - self._axis_line.angle

    @property
    def span(self):
        return self._axis_line.length

    @property
    def offset(self):
        if self._angle == 0.0:
            total_offset = self._domain_v * self._offset_direction
        else:
            total_offset = abs(self._domain_u * sin(self._angle)
                               / self._v_tiles) * self._offset_direction
        return total_offset

    @property
    def shift(self):
        if self._angle == 0.0:
            return 0

        def find_nxt_grid_point(offset_line):
            u_mult = 0
            while u_mult < self._u_tiles:
                for v_mult in range(0, self._v_tiles):
                    grid_point = _PatternPoint(self._domain_u * u_mult,
                                               self._domain_v * v_mult)
                    if offset_line.point_on_line(grid_point):
                        return grid_point
                u_mult += 1
            if u_mult >= self._u_tiles:
                logger.debug('Can not determine next repeating grid.')
                return None

        if self._u_tiles == self._v_tiles == 1:
            return abs(self._domain_u * cos(self._angle))
        else:
            # calculate the abstract offset axis
            offset_u = abs(self.offset * sin(self._angle))
            offset_v = -abs(self.offset * cos(self._angle))
            offset_vector = _PatternPoint(offset_u, offset_v)
            # find the offset line
            abstract_axis_start_point = _PatternPoint(0, 0)
            abstract_axis_end_point = \
                _PatternPoint(self._domain_u * self._u_tiles,
                              self._domain_v * self._v_tiles)
            offset_vector_start = abstract_axis_start_point + offset_vector
            offset_vector_end = abstract_axis_end_point + offset_vector
            offset_axis = _PatternLine(offset_vector_start, offset_vector_end)

            # try to find the next occurance on the abstract offset axis
            nxt_grid_point = find_nxt_grid_point(offset_axis)

            if nxt_grid_point:
                total_shift = \
                    offset_axis.start_point.distance_to(nxt_grid_point)
                return total_shift
            else:
                return None


class _PatternDomain:
    def __init__(self, start_u, start_v, end_u, end_v,
                 model_pattern, expandable):
        self._origin = _PatternPoint(min(start_u, end_u), min(start_v, end_v))
        self._corner = _PatternPoint(max(start_u, end_u), max(start_v, end_v))
        self._bounds = self._corner - self._origin
        self._normalized_domain = \
            _PatternPoint(1.0, 1.0 * (self._bounds.v / self._bounds.u))
        if self._zero_domain():
            raise PyRevitException('Can not process zero domain.')

        self.u_vec = _PatternLine(_PatternPoint(0, 0),
                                  _PatternPoint(self._bounds.u, 0))
        self.v_vec = _PatternLine(_PatternPoint(0, 0),
                                  _PatternPoint(0, self._bounds.v))

        if model_pattern:
            self._max_domain = MAX_MODEL_DOMAIN
        else:
            self._max_domain = MAX_DETAIL_DOMAIN

        self._expandable = expandable
        self._target_domain = self._max_domain

        self.diagonal = _PatternLine(_PatternPoint(0.0, 0.0),
                                     _PatternPoint(self._bounds.u,
                                                   self._bounds.v))

        self._calculate_safe_angles()

    def __repr__(self):
        return '<_PatternDomain U:{} V:{} SafeAngles:{}>'\
               .format(self._bounds.u,
                       self._bounds.v,
                       len(self.safe_angles))

    def _zero_domain(self):
        return self._bounds.u == 0 or self._bounds.v == 0

    def _calculate_safe_angles(self):
        # setup tile counters
        u_mult = v_mult = 1
        self.safe_angles = []
        processed_ratios = {1.0}

        # add standard angles to the list
        self.safe_angles.append(
            _PatternSafeGrid(self._bounds,
                             self.diagonal.angle,
                             u_mult, 0)
            )

        self.safe_angles.append(
            _PatternSafeGrid(self._bounds,
                             self.diagonal.angle,
                             u_mult, 0, flipped=True)
            )

        self.safe_angles.append(
            _PatternSafeGrid(self._bounds,
                             self.diagonal.angle,
                             u_mult, v_mult)
            )

        self.safe_angles.append(
            _PatternSafeGrid(self._bounds,
                             self.diagonal.angle,
                             u_mult, v_mult, flipped=True)
            )

        self.safe_angles.append(
            _PatternSafeGrid(self._bounds,
                             self.diagonal.angle,
                             0, v_mult)
            )

        # traverse the tile space and add safe grids to the list
        while self._bounds.u * u_mult <= self._target_domain / 2.0:
            v_mult = 1
            while self._bounds.v * v_mult <= self._target_domain / 2.0:
                ratio = round(v_mult / float(u_mult), RATIO_RESOLUTION)
                if ratio not in processed_ratios:
                    # for every tile, also add the mirrored tile
                    angle1 = _PatternSafeGrid(self._bounds,
                                              self.diagonal.angle,
                                              u_mult,
                                              v_mult)

                    angle2 = _PatternSafeGrid(self._bounds,
                                              self.diagonal.angle,
                                              u_mult,
                                              v_mult,
                                              flipped=True)

                    if angle1.is_valid() and angle2.is_valid():
                        self.safe_angles.append(angle1)
                        self.safe_angles.append(angle2)
                        processed_ratios.add(ratio)
                    else:
                        logger.warning('Skipping safe angle '
                                       'for grid point U:{} V:{}'
                                       .format(u_mult, v_mult))
                v_mult += 1
            u_mult += 1

    def expand(self):
        # expand target domain for more safe angles
        if self._target_domain > self._max_domain * MAX_DOMAIN_MULT:
            return False
        else:
            self._target_domain += self._max_domain / 2
            self._calculate_safe_angles()
            return True

    def get_domain_coords(self, pat_line):
        return _PatternLine(pat_line.start_point - self._origin,
                            pat_line.end_point - self._origin)

    def get_grid_params(self, axis_angle):
        return min(self.safe_angles,
                   key=lambda x: abs(x.grid_angle - axis_angle))

    def get_required_correction(self, axis_angle):
        return abs(axis_angle - self.get_grid_params(axis_angle).grid_angle)

    def get_best_angle(self, axis_angle):
        if self._expandable:
            while self.get_required_correction(axis_angle) >= ANGLE_CORR_RATIO:
                if not self.expand():
                    break
        return self.get_grid_params(axis_angle)


class _PatternGrid:
    def __init__(self, pat_domain, init_line):
        self._domain = pat_domain
        self._grid = self._domain.get_best_angle(init_line.angle)
        logger.debug('Closest safe angle is: {}'.format(self._grid))
        self.angle = self._grid.grid_angle
        self.span, self.offset, self.shift = \
            self._grid.span, self._grid.offset, self._grid.shift

        self.segment_lines = []
        init_line.rotate(self.angle - init_line.angle,
                         origin=init_line.center_point)
        self.segment_lines.append(init_line)

    def __repr__(self):
        return '<_PatternGrid Angle:{} Span:{} Offset:{} Shift:{}>'\
               .format(self.angle, self.span, self.offset, self.shift)

    def adopt_line(self, pat_line):
        # todo: optimise grid creation. check overlap and combine
        # overlapping lines into one grid
        return False

    @property
    def origin(self):
        # collect all line segment points
        point_list = []
        for seg_line in self.segment_lines:
            point_list.extend([seg_line.start_point, seg_line.end_point])

        # origin is the point that is closest to zero
        if self.angle <= HALF_PI:
            return min(point_list,
                       key=lambda x: x.distance_to(_PatternPoint(0, 0)))
        else:
            return min(point_list,
                       key=lambda x: x.distance_to(
                           _PatternPoint(self._domain.u_vec.length, 0)
                           ))

    @property
    def segments(self):
        pen_down = self.segment_lines[0].length
        return [pen_down, self.span - pen_down]

    @property
    def segments_as_lines(self):
        # todo: see _RevitPattern.adjust_line()
        return self.segment_lines


class _RevitFillGrid:
    def __init__(self, rvt_fillgrid, scale):
        self._rvt_fillgrid = rvt_fillgrid
        self._scale = scale

    @property
    def origin(self):
        return _PatternPoint(self._rvt_fillgrid.Origin.U,
                             self._rvt_fillgrid.Origin.V)

    @property
    def angle(self):
        return self._rvt_fillgrid.Angle

    @property
    def offset(self):
        return self._rvt_fillgrid.Offset

    @property
    def shift(self):
        return self._rvt_fillgrid.Shift

    @property
    def segments(self):
        return self._rvt_fillgrid.GetSegments()

    def get_rvt_fillgrid(self):
        rvt_fill_grid = DB.FillGrid()
        rvt_fill_grid.Origin = DB.UV(self.origin.u * self._scale,
                                     self.origin.v * self._scale)
        rvt_fill_grid.Angle = self.angle
        rvt_fill_grid.Offset = self.offset * self._scale
        rvt_fill_grid.Shift = self.shift * self._scale

        scaled_segments = [x * self._scale
                           for x in self._rvt_fillgrid.GetSegments()]
        rvt_fill_grid.SetSegments(scaled_segments)

        return rvt_fill_grid


class _RevitPattern:
    def __init__(self, pat_domain, pat_name, model_pat=True,
                 scale=1.0, rotation=0, flip_u=False, flip_v=False):
        self._domain = pat_domain
        self._pattern_grids = []
        self._input_fillgrids = []

        self._name = pat_name
        self._model_pat = model_pat
        self._scale = scale
        self._rotation = rotation
        self._flip_u = flip_u
        self._flip_v = flip_v

    def __repr__(self):
        return '<_RevitPattern Name:{} Model:{} Scale:{}>'\
               .format(self._name, self._model_pat, self._scale)

    def append_fillgrid(self, rvt_fillgrid):
        self._pattern_grids.append(_RevitFillGrid(rvt_fillgrid, self._scale))

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

    def _make_fill_grid(self, pattern_grid):
        fg_scale = self._scale

        fg_rotation = self._rotation
        if (self._flip_u and not self._flip_v) \
                or (self._flip_v and not self._flip_u):
            fg_rotation = -fg_rotation

        rvt_fill_grid = DB.FillGrid()

        # determine and set angle
        if self._flip_u and self._flip_v:
            rvt_fill_grid.Angle = PI + pattern_grid.angle
        elif self._flip_u:
            rvt_fill_grid.Angle = PI - pattern_grid.angle
        elif self._flip_v:
            rvt_fill_grid.Angle = -pattern_grid.angle
        else:
            rvt_fill_grid.Angle = pattern_grid.angle
        rvt_fill_grid.Angle += fg_rotation

        # determine and set origin
        # apply flips
        origin_u = -pattern_grid.origin.u if self._flip_u \
            else pattern_grid.origin.u
        origin_v = -pattern_grid.origin.v if self._flip_v \
            else pattern_grid.origin.v
        # apply rotation if any
        fg_origin = _PatternPoint(origin_u, origin_v)
        if fg_rotation:
            fg_origin.rotate(fg_rotation)
        rvt_fill_grid.Origin = \
            DB.UV(fg_origin.u * fg_scale, fg_origin.v * fg_scale)

        # determine and set offset
        if self._flip_u and self._flip_v:
            rvt_fill_grid.Offset = pattern_grid.offset * fg_scale
        elif self._flip_u or self._flip_v:
            rvt_fill_grid.Offset = -pattern_grid.offset * fg_scale
        else:
            rvt_fill_grid.Offset = pattern_grid.offset * fg_scale

        # determine and set shift
        rvt_fill_grid.Shift = pattern_grid.shift * fg_scale

        # build and set segments list
        if pattern_grid.segments:
            scaled_segments = \
                [seg * fg_scale for seg in pattern_grid.segments]
            rvt_fill_grid.SetSegments(scaled_segments)

        return rvt_fill_grid

    @staticmethod
    def _make_fillpattern_element(rvt_fill_pat):
        # find existing filled pattern element matching name and pattern target
        existing_fillpatternelements = \
            DB.FilteredElementCollector(revit.doc)\
              .OfClass(framework.get_type(DB.FillPatternElement))
        fill_pat_element = None
        for exfpe in existing_fillpatternelements:
            exfp = exfpe.GetFillPattern()
            if rvt_fill_pat.Name == exfp.Name \
                    and rvt_fill_pat.Target == exfp.Target:
                fill_pat_element = exfpe

        if fill_pat_element:
            with revit.Transaction('Create Fill Pattern'):
                fill_pat_element.SetFillPattern(rvt_fill_pat)
                logger.debug('Updated FillPatternElement with id:{}'
                             .format(fill_pat_element.Id))
        else:
            with revit.Transaction('Create Fill Pattern'):
                fill_pat_element =\
                    DB.FillPatternElement.Create(revit.doc, rvt_fill_pat)
                logger.debug('Created FillPatternElement with id:{}'
                             .format(fill_pat_element.Id))

        logger.debug('Fill Pattern:{}'.format(fill_pat_element.Name))
        fp = fill_pat_element.GetFillPattern()
        logger.debug('Fill Grids Count: {}'.format(len(fp.GetFillGrids())))
        for idx, fg in enumerate(fp.GetFillGrids()):
            logger.debug('FillGrid #{} '
                         'Origin:{} Angle:{} Shift:{} Offset:{} Segments:{}'
                         .format(idx, fg.Origin,
                                 fg.Angle, fg.Shift,
                                 fg.Offset, fg.GetSegments()))
        return fill_pat_element

    def create_pattern(self):
        fill_grids = [self._make_fill_grid(x) for x in self._pattern_grids]

        # Make new FillPattern
        fp_target = \
            DB.FillPatternTarget.Model \
            if self._model_pat else DB.FillPatternTarget.Drafting

        fill_pat = DB.FillPattern(self._name,
                                  fp_target,
                                  DB.FillPatternHostOrientation.ToHost)

        # Apply the FillGrids
        fill_pat.SetFillGrids(List[DB.FillGrid](fill_grids))

        # Create the FillPatternElement in current document
        return self._make_fillpattern_element(fill_pat)

    def get_pat_data(self):
        pat_type = 'MODEL' if self._model_pat else 'DRAFTING'
        unit_type = 'INCH' if self._scale == 12 else 'MM'
        pyrvtver = versionmgr.get_pyrevit_version()
        pattern_desc = \
            PAT_FILE_TEMPLATE.format(time=coreutils.current_time(),
                                     date=coreutils.current_date(),
                                     version=pyrvtver.get_formatted(),
                                     units=unit_type,
                                     name=self._name,
                                     type=pat_type)

        for pat_grid in self._pattern_grids:
            # angle, u, v, shift, offset, segments....
            grid_desc = \
                PAT_SEPARATOR.join([
                    flatten_zeros(
                        degrees(pat_grid.angle)),
                    flatten_zeros(pat_grid.origin.u * self._scale),
                    flatten_zeros(pat_grid.origin.v * self._scale),
                    flatten_zeros(pat_grid.shift * self._scale),
                    flatten_zeros(pat_grid.offset * self._scale)])
            grid_desc += PAT_SEPARATOR
            if pat_grid.segments:
                scaled_segments = []
                for idx, seg in enumerate(pat_grid.segments):
                    if idx % 2 != 0:
                        seg *= -1
                    scaled_segments.append(seg * self._scale)

                grid_desc += PAT_SEPARATOR.join(
                    [flatten_zeros(x) for x in scaled_segments]
                    )

            pattern_desc += grid_desc + '\n'

        return pattern_desc


def _make_filledregion(fillpattern_name, fillpattern_id):
    filledregion_types = DB.FilteredElementCollector(revit.doc)\
                           .OfClass(framework.get_type(DB.FilledRegionType))

    source_fr = filledregion_types.FirstElement()
    with revit.Transaction('Create Filled Region'):
        new_fr = source_fr.Duplicate(fillpattern_name)
        new_fr.FillPatternId = fillpattern_id


def _export_pat(revit_pat, export_dir):
    pat_file_contents = revit_pat.get_pat_data()
    pat_file_name = coreutils.cleanup_filename(revit_pat.name)
    pat_file_path = op.join(export_dir, '{}.pat'.format(pat_file_name))
    logger.debug('Exporting pattern to: %s', pat_file_path)
    with open(pat_file_path, 'w') as pat_file:
        pat_file.write(pat_file_contents)


def _create_fill_pattern(revit_pat, create_filledregion=False):
    try:
        fillpat_element = revit_pat.create_pattern()
        if create_filledregion:
            _make_filledregion(fillpat_element.Name, fillpat_element.Id)
        return fillpat_element
    except Exception as create_pat_err:
        logger.error('Error creating pattern element. | {}'
                     .format(create_pat_err))


def _make_rvt_pattern(pat_name, pat_lines, domain, fillgrids=None,
                      scale=1.0, rotation=0, flip_u=False, flip_v=False,
                      model_pattern=True, allow_expansion=False):
    pat_domain = _PatternDomain(domain[0][0],
                                domain[0][1],
                                domain[1][0],
                                domain[1][1],
                                model_pattern,
                                allow_expansion)

    logger.debug('New pattern domain: {}'.format(pat_domain))

    revit_pat = _RevitPattern(
        pat_domain,
        pat_name,
        model_pattern,
        scale,
        rotation,
        flip_u,
        flip_v
        )
    logger.debug('New revit pattern: {}'.format(revit_pat))

    for line_coords in pat_lines:
        startp = _PatternPoint(line_coords[0][0], line_coords[0][1])
        endp = _PatternPoint(line_coords[1][0], line_coords[1][1])
        pat_line = _PatternLine(startp, endp)
        try:
            revit_pat.append_line(pat_line)
        except Exception as pat_line_err:
            logger.error('Error adding line: {} | {}'
                         .format(line_coords, pat_line_err))

    if fillgrids:
        for pgrid in fillgrids:
            revit_pat.append_fillgrid(pgrid)

    return revit_pat


def make_pattern(pat_name, pat_lines, domain, fillgrids=None,
                 scale=1.0, rotation=0,
                 flip_u=False, flip_v=False,
                 model_pattern=True, allow_expansion=False,
                 create_filledregion=False):
    revit_pat = \
        _make_rvt_pattern(
            pat_name,
            pat_lines,
            domain,
            fillgrids=fillgrids,
            scale=scale,
            rotation=rotation,
            flip_u=flip_u,
            flip_v=flip_v,
            model_pattern=model_pattern,
            allow_expansion=allow_expansion
            )
    return _create_fill_pattern(revit_pat, create_filledregion)


def export_pattern(export_dir, pat_name, pat_lines, domain,
                   fillgrids=None, scale=12.0,
                   model_pattern=True, allow_expansion=False):
    revit_pat = \
        _make_rvt_pattern(
            pat_name,
            pat_lines,
            domain,
            fillgrids=fillgrids,
            scale=scale,
            model_pattern=model_pattern,
            allow_expansion=allow_expansion
            )
    return _export_pat(revit_pat, export_dir)
