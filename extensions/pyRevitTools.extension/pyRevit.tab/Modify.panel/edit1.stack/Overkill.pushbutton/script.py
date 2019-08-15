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
RESOLUTION = '{:.3f}'


CurvePoint = namedtuple('CurvePoint', ['x', 'y', 'cid'])


class LinearCurveGroup(object):
    supported_geoms = (DB.Line)

    def __init__(self, curve, include_style=False):
        self.points = set()
        # calculate cgroup parameters
        p1 = curve.GeometryCurve.GetEndPoint(0)
        p2 = curve.GeometryCurve.GetEndPoint(1)
        p1x = LinearCurveGroup.get_float(p1.X)
        p1y = LinearCurveGroup.get_float(p1.Y)
        p2x = LinearCurveGroup.get_float(p2.X)
        p2y = LinearCurveGroup.get_float(p2.Y)
        # get the direction vector
        curve_dir = curve.GeometryCurve.Direction
        self.dir_x, self.dir_y = \
            LinearCurveGroup.get_float(curve_dir.X), \
                LinearCurveGroup.get_float(curve_dir.Y)
        # unify the direction
        if (self.dir_x < 0.0 and self.dir_y <= 0.0) \
                or (self.dir_x > 0.0 and self.dir_y < 0.0):
            self.dir_x, self.dir_y = -self.dir_x, -self.dir_y
        # make sure there are no -0.0
        self.dir_x = 0.0 if self.dir_x == 0.0 else self.dir_x
        self.dir_y = 0.0 if self.dir_y == 0.0 else self.dir_y
        # calc curve offset from cgroup
        self.dir_offset = \
            self.shortest_dist(p1x, p1y,
                               p2x, p2y,
                               self.dir_x, self.dir_y)
        # get curve weight
        self.weight = \
            LinearCurveGroup.get_style_weight(curve) if include_style else None

        # set cgroup boundary
        self.dir_cid = curve.Id.IntegerValue
        self.add_points([
            CurvePoint(x=p1x, y=p1y, cid=self.dir_cid),
            CurvePoint(x=p2x, y=p2y, cid=self.dir_cid)
        ])

        # create identity
        # identity is a tuple (dir_x, dir_y, dir_offset, weight)
        self.identity = \
            (LinearCurveGroup.get_float(self.dir_x),
             LinearCurveGroup.get_float(self.dir_y),
             LinearCurveGroup.get_float(self.dir_offset),
             self.weight)

        # prepare a list for overlapping curves
        self.bounded = set()

    def __repr__(self):
        return '<%s max=%s, min=%s points=%s weight=%s id=%s hash=%s>' % (
            self.__class__.__name__,
            self.max_point,
            self.min_point,
            len(self.points),
            self.weight,
            self.identity,
            hash(self))

    def __hash__(self):
        return hash(self.identity)

    def __eq__(self, other):
        # if same direction vector
        if isinstance(other, LinearCurveGroup) \
                and hash(self) == hash(other):
            # and any of the points is inside the bounds of this curve group
            for cgroup_point in [other.min_point, other.max_point]:
                x_in = self.min_point.x <= cgroup_point.x <= self.max_point.x
                y_in = self.min_point.y <= cgroup_point.y <= self.max_point.y
                return x_in or y_in
        return False

    @staticmethod
    def shortest_dist(x1, y1, x2, y2, x0, y0):
        # https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line
        # line passes thru (x1, y1), (x2, y2)
        # point is (x0, y0)
        return (abs(x0*(y2-y1)-y0*(x2-x1)+x2*y1-y2*x1) /
                math.sqrt((y2-y1)**2 + (x2-x1)**2))

    @staticmethod
    def get_style_weight(curve):
        graphic_style_cat = curve.LineStyle.GraphicsStyleCategory
        graphic_style_type = curve.LineStyle.GraphicsStyleType
        return graphic_style_cat.GetLineWeight(graphic_style_type)

    @staticmethod
    def get_float(float_value):
        return float(RESOLUTION.format(float_value))

    @property
    def max_point(self):
        return max(self.points, key=lambda dp: abs(dp.x))

    @property
    def min_point(self):
        return min(self.points, key=lambda dp: abs(dp.x))

    def add_points(self, domain_points):
        for domain_point in domain_points:
            if isinstance(domain_point, CurvePoint):
                logger.debug('Adding cgroup point: %s', domain_point)
                self.points.add(domain_point)

    def merge(self, cgroup):
        if isinstance(cgroup, LinearCurveGroup):
            self.add_points(cgroup.points)

    def overkill(self, doc=None):
        bounded_curve_ids = set()
        if doc and len(self.points) > 2:
            # extend the root curve to cover the full cgroup
            root_curve = doc.GetElement(DB.ElementId(self.dir_cid))
            min_dpoint = self.min_point
            max_dpoint = self.max_point
            # create new geometry
            curve_z = root_curve.GeometryCurve.GetEndPoint(0).Z
            start_point = DB.XYZ(min_dpoint.x, min_dpoint.y, curve_z)
            end_point = DB.XYZ(max_dpoint.x, max_dpoint.y, curve_z)
            reset_dir_curve = False
            try:
                geom_curve = DB.Line.CreateBound(start_point, end_point)
                root_curve.GeometryCurve = geom_curve
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
                    logger.debug('Deleting %s', bounded_curve_ids)
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

    def extend(self, curve_element):
        logger.debug('Extending cruve group...')
        for cgroup_type in CURVE_GROUP_TYPES:
            logger.debug('Trying cgroup type %s', cgroup_type)
            if isinstance(curve_element.GeometryCurve,
                          cgroup_type.supported_geoms):
                logger.debug('cruve group type supports %s',
                             curve_element.GeometryCurve)
                cgroup = cgroup_type(curve_element,
                                     include_style=self._include_style)
                logger.debug('Domain is %s', cgroup)
                if cgroup in self.curve_groups:
                    logger.debug('Domain exists %s', cgroup)
                    idx = self.curve_groups.index(cgroup)
                    exst_domain = self.curve_groups[idx]
                    logger.debug('Merging into existing cgroup %s', exst_domain)
                    exst_domain.merge(cgroup)
                else:
                    logger.debug('New cgroup %s', cgroup)
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
    logger.debug('Extracting 2d cruve group...')
    cgroup_collection = CurveGroupCollection(include_style=include_style)
    for curve_element in filter_curves(curve_elements,
                                       view_specific=view_specific):
        logger.debug('Adding curve to cruve group: %s', curve_element.Id)
        cgroup_collection.extend(curve_element)

    del_count = 0
    with revit.Transaction('Overkill'):
        # process linear cruve group
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
        logger.debug('Collecting detail lines in current view...')
        curve_collector = \
            revit.query.get_elements_by_class(DB.CurveElement,
                                            view_id=revit.active_view.Id)
        overkill_curves(list(curve_collector),
                        view_specific=view_spec,
                        include_style=incl_style)

