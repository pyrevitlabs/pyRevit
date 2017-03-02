from math import sqrt, pi, sin, cos, tan, radians

from pyrevit import PyRevitException
from pyrevit.coreutils.logger import get_logger
from revitutils import doc

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


class LinesDoNotIntersectException(PyRevitException):
    pass


class PatternPoint:
    def __init__(self, u_point, v_point):
        self.u = u_point
        self.v = v_point

    def __repr__(self):
        return '<PatternPoint U:{0:.20f} V:{1:.20f}>'.format(self.u, self.v)

    def __eq__(self, other):
        return self.u == other.u and self.v == other.v

    def __hash__(self):
        # todo: come up with method for sorting lines
        return hash(self.u + self.v)

    def __add__(self, other):
        return PatternPoint(self.u + other.u, self.v + other.v)

    def __sub__(self, other):
        return PatternPoint(self.u - other.u, self.v - other.v)

    def distance_to(self, point):
        return sqrt((point.u - self.u)**2 + (point.v - self.v)**2)

    def rotate(self, origin, angle):
        tu = self.u - origin.u
        tv = self.v - origin.v
        self.u = origin.u + (tu*cos(angle) - tv*sin(angle))
        self.v = origin.v + (tu*sin(angle) + tv*cos(angle))
        return True


class PatternLine:
    def __init__(self, start_p, end_p):
        self.start_point = start_p if start_p.v <= end_p.v else end_p
        self.end_point = end_p if start_p.v <= end_p.v else start_p
        self.u_vector = UV(1,0)

    def __repr__(self):
        return '<PatternLine Start:{} End:{} Length:{} Angle:{}>'.format(self.start_point, self.end_point,
                                                                         self.length, self.angle)

    @property
    def direction(self):
        return PatternPoint(self.end_point.u - self.start_point.u, self.end_point.v - self.start_point.v)

    @property
    def angle(self):
        # always return angle to u direction
        # todo: fix and use actual math for angles to remove revit dependency
        return self.u_vector.AngleTo(UV(self.direction.u, self.direction.v))

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
           raise LinesDoNotIntersectException()

        d = PatternPoint(det(self.start_point, self.end_point), det(pat_line.start_point, pat_line.end_point))
        int_point_x = det(d, xdiff) / div
        int_point_y = det(d, ydiff) / div

        return PatternPoint(int_point_x, int_point_y)

    def rotate(self, origin, angle):
        self.start_point.rotate(origin, angle)
        self.end_point.rotate(origin, angle)


# class PatternGrid:
#     def __init__(self, pattern_domain, u_tiles, v_tiles):
#         self._domain = pattern_domain
#         self.u_tiles = u_tiles
#         self.v_tiles = v_tiles
#         self.origin = PatternPoint(0, 0)
#         self._axis_line = PatternLine(self.origin, end_p + self.origin)
#         self._offset_direction = 1
#
#     @property
#     def angle(self):
#         return self._axis_line.angle
#
#     @property
#     def span(self):
#         return self._axis_line.length
#
#     @property
#     def offset(self):
#         if self.angle == 0.0:
#             return self._domain.v_vec.length
#         else:
#             offset = abs(self._domain.u_vec.length * sin(self.angle) / self.v_tiles) * self._offset_direction
