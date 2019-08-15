"""Deletes the lines overlapped by other lines (similar to AutoCAD Overkill)"""

#pylint: disable=E0401,C0103
import math
from collections import namedtuple

from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


__authors__ = ["tylerk", "{{author}}"]

logger = script.get_logger()
output = script.get_output()

# configs
POINT_RESOLUTION = '{:.4f}'
DIRECTION_RESOLUTION = '{:.2f}'
OFFSET_RESOLUTION = '{:.4f}'


CurvePoint = namedtuple('CurvePoint', ['x', 'y', 'cid'])


class LinearCurveGroup(object):
    supported_geoms = (DB.Line)

    def __init__(self, curve, include_style=False):
        self.points = set()
        # calculate cgroup parameters
        p1 = curve.GeometryCurve.GetEndPoint(0)
        p2 = curve.GeometryCurve.GetEndPoint(1)
        # get the direction vector
        self.dir_x, self.dir_y = self.get_direction(curve)
        # calc curve offset from cgroup
        self.dir_offset = self.get_offset(p1, p2)
        # get curve weight
        self.weight = self.get_weight(curve) if include_style else None
        # create curve group identity
        # identity is a tuple (dir_x, dir_y, dir_offset, weight)
        self.cgroup_id = (self.dir_x, self.dir_y, self.dir_offset, self.weight)

        # set cgroup boundary
        self.dir_cid = curve.Id.IntegerValue
        self.add_points([
            self.get_point(p1.X, p1.Y),
            self.get_point(p2.X, p2.Y),
        ])

        # prepare a list for overlapping curves
        self.bounded = set()

    def __repr__(self):
        return '<%s max=%s, min=%s points=%s id(dir=[%s,%s],offset=%s,weight=%s)>' % (
            self.__class__.__name__,
            self.max_point,
            self.min_point,
            len(self.points),
            self.dir_x,
            self.dir_y,
            self.dir_offset,
            self.weight)

    @staticmethod
    def shortest_dist(x1, y1, x2, y2, x0, y0):
        # https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line
        # line passes thru (x1, y1), (x2, y2)
        # point is (x0, y0)
        return (
            abs(x0*(y2-y1) - y0*(x2-x1) + x2*y1 - y2*x1) /
            math.sqrt((y2-y1)**2 + (x2-x1)**2)
        )

    @staticmethod
    def is_inside(min_cpoint, max_cpoint, cpoint):
        x_range = max_cpoint.x - min_cpoint.x
        y_range = max_cpoint.y - min_cpoint.y
        if x_range == 0.0:
            return min_cpoint.y <= cpoint.y <= max_cpoint.y
        elif y_range == 0.0:
            return min_cpoint.x <= cpoint.x <= max_cpoint.x
        else:
            xr = LinearCurveGroup.get_float((cpoint.x - min_cpoint.x) / x_range)
            yr = LinearCurveGroup.get_float((cpoint.y - min_cpoint.y) / y_range)
            return xr == yr

    @staticmethod
    def get_style_weight(curve):
        graphic_style_cat = curve.LineStyle.GraphicsStyleCategory
        graphic_style_type = curve.LineStyle.GraphicsStyleType
        return graphic_style_cat.GetLineWeight(graphic_style_type)

    @staticmethod
    def get_float(float_value, res=POINT_RESOLUTION):
        return float(res.format(float_value))

    @property
    def max_point(self):
        return max(self.points, key=lambda p: p.x + p.y)

    @property
    def min_point(self):
        return min(self.points, key=lambda p: p.x + p.y)

    def get_point(self, x, y):
        return CurvePoint(x=LinearCurveGroup.get_float(x, res=POINT_RESOLUTION),
                          y=LinearCurveGroup.get_float(y, res=POINT_RESOLUTION),
                          cid=self.dir_cid)

    def get_direction(self, curve):
        dir_x, dir_y = \
            curve.GeometryCurve.Direction.X, curve.GeometryCurve.Direction.Y
        # unify the direction
        if (dir_x <= 0.0 and dir_y <= 0.0) \
                or (dir_x > 0.0 and dir_y < 0.0):
            dir_x, dir_y = -dir_x, -dir_y
        # make sure there are no -0.0
        dir_x = 0.0 if dir_x == 0.0 else dir_x
        dir_y = 0.0 if dir_y == 0.0 else dir_y
        # bring direction within tolerance
        return LinearCurveGroup.get_float(dir_x, res=DIRECTION_RESOLUTION), \
            LinearCurveGroup.get_float(dir_y, res=DIRECTION_RESOLUTION)

    def get_offset(self, p1, p2):
        dir_offset = \
            LinearCurveGroup.shortest_dist(
                LinearCurveGroup.get_float(p1.X, res=POINT_RESOLUTION),
                LinearCurveGroup.get_float(p1.Y, res=POINT_RESOLUTION),
                LinearCurveGroup.get_float(p2.X, res=POINT_RESOLUTION),
                LinearCurveGroup.get_float(p2.Y, res=POINT_RESOLUTION),
                self.dir_x, self.dir_y)
        return LinearCurveGroup.get_float(dir_offset, res=OFFSET_RESOLUTION)

    def get_weight(self, curve):
        return LinearCurveGroup.get_style_weight(curve)

    def add_points(self, curve_points):
        for curve_point in curve_points:
            if isinstance(curve_point, CurvePoint):
                self.points.add(curve_point)

    def merge(self, cgroup):
        if isinstance(cgroup, LinearCurveGroup):
            # and any of the points is inside the bounds of this curve group
            for cgroup_point in cgroup.points:
                if LinearCurveGroup.is_inside(
                        self.min_point, self.max_point, cgroup_point):
                    self.add_points(cgroup.points)
                    return True
        return False

    def overkill(self, doc=None):
        bounded_curve_ids = set()
        if doc and len(self.points) > 2:
            # extend the root curve to cover the full cgroup
            root_curve = doc.GetElement(DB.ElementId(self.dir_cid))
            min_dpoint = self.min_point
            max_dpoint = self.max_point
            # create new geometry
            curve_z = root_curve.GeometryCurve.GetEndPoint(0).Z
            min_point = DB.XYZ(min_dpoint.x, min_dpoint.y, curve_z)
            max_point = DB.XYZ(max_dpoint.x, max_dpoint.y, curve_z)
            reset_dir_curve = False
            try:
                geom_curve = DB.Line.CreateBound(min_point, max_point)
                root_curve.SetGeometryCurve(geom_curve, overrideJoins=True)
                reset_dir_curve = True
            except Exception as set_ex:
                logger.debug('Failed re-setting root curve | %s', set_ex)
            # now delete the overlapping lines
            if reset_dir_curve:
                bounded_curve_ids = \
                    {x.cid for x in self.points if x.cid != self.dir_cid}
                if bounded_curve_ids:
                    bounded_curve_ids = \
                        [DB.ElementId(x) for x in bounded_curve_ids]
                    doc.Delete(List[DB.ElementId](bounded_curve_ids))
        return len(bounded_curve_ids)


CURVE_GROUP_TYPES = [
    LinearCurveGroup,
]


class CurveGroupCollection(object):
    def __init__(self, include_style=False):
        self.curve_groups = []
        self._include_style = include_style

    def __iter__(self):
        return iter(self.curve_groups)

    def merge(self, cgroup):
        matching_cgroups = \
            [x for x in self.curve_groups if x.cgroup_id == cgroup.cgroup_id]
        if matching_cgroups:
            first_matching = matching_cgroups[0]
            matching_cgroups.remove(first_matching)
            if matching_cgroups:
                for matching_cgroup in matching_cgroups:
                    cgroup.merge(matching_cgroup)
                    self.curve_groups.remove(matching_cgroup)
            return first_matching.merge(cgroup)

    def extend(self, curve_element):
        for cgroup_type in CURVE_GROUP_TYPES:
            if isinstance(curve_element.GeometryCurve,
                          cgroup_type.supported_geoms):
                cgroup = cgroup_type(curve_element,
                                     include_style=self._include_style)
                if not self.merge(cgroup):
                    self.curve_groups.append(cgroup)
                return True


def filter_curves(elements, view_specific=None):
    """Filter given curves for view specific."""
    filtered_elements = \
        revit.query.get_elements_by_class(DB.CurveElement, elements=elements) \
            if elements else []
    if view_specific is None:
        return filtered_elements
    else:
        return [x for x in filtered_elements if x.ViewSpecific == view_specific]


def ask_for_curve_type():
    # ask user for options and process
    options = ['All Lines', 'Detail Lines', 'Model Lines']
    switches = {'Consider Line Weights': True}
    selected_option, switches = \
        forms.CommandSwitchWindow.show(
            options,
            switches=switches,
            message='Pick overkill option:'
            )

    return (selected_option, switches['Consider Line Weights'])


def ask_consider_weight():
    # ask user for options and process
    return True


def overkill_curves(curve_elements,
                    view_specific=None,
                    include_style=True):
    # collect comparison info on each detail-lines geomtery
    cgroup_collection = CurveGroupCollection(include_style=include_style)
    for curve_element in filter_curves(curve_elements,
                                       view_specific=view_specific):
        cgroup_collection.extend(curve_element)

    del_count = 0
    with revit.Transaction('Overkill', swallow_errors=True):
        # process linear curve group
        for cgroup in cgroup_collection:
            del_count += cgroup.overkill(doc=revit.doc)

    if del_count > 0:
        forms.alert('{} lines were removed.'.format(del_count))
    else:
        forms.alert('Pretty clean! No lines were removed.')


selected_curves = filter_curves(revit.get_selection())
if selected_curves:
    overkill_curves(selected_curves, include_style=ask_consider_weight())
else:
    selected_opt, incl_style = ask_for_curve_type()

    if selected_opt == 'All Lines':
        view_spec = None
    elif selected_opt == 'Model/Symbolic Lines':
        view_spec = False
    elif selected_opt == 'Detail Lines':
        view_spec = True

    if selected_opt:
        # collect all detail-lines in active view
        curve_collector = \
            revit.query.get_elements_by_class(DB.CurveElement,
                                            view_id=revit.active_view.Id)
        overkill_curves(list(curve_collector),
                        view_specific=view_spec,
                        include_style=incl_style)

