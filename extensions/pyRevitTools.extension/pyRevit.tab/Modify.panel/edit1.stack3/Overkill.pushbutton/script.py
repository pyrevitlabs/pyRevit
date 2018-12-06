"""Deletes the lines overlapped by other lines (similar to AutoCAD Overkill)"""

#pylint: disable=E0401,C0103
import math
from collections import namedtuple

from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


__author__ = "Ehsan Iran-Nejad\ntylerk"

logger = script.get_logger()
output = script.get_output()

INCLUDE_STYLE = True
VIEW_SPECIFIC = True

DomainBound = namedtuple('DomainBound', ['x', 'y', 'dlid'])


class DetailLineDomain(object):
    def __init__(self, dline, include_style=False):
        # calculate domain parameters
        dvector = dline.GeometryCurve.Direction
        p1 = dline.GeometryCurve.GetEndPoint(0)
        p2 = dline.GeometryCurve.GetEndPoint(1)
        self.offset = \
            self.shortest_dist(p1.X, p1.Y, p2.X, p2.Y, dvector.X, dvector.Y)
        self.direction = dvector.X, dvector.Y
        self.reverse = (dvector.X * dvector.Y) < 0
        self.weight = None
        if include_style:
            self.weight = DetailLineDomain.get_style_weight(dline)

        # set domain boundary
        self.max = DomainBound(x=p1.X, y=p1.Y, dlid=dline.Id.IntegerValue)
        self.min = DomainBound(x=p2.X, y=p2.Y, dlid=dline.Id.IntegerValue)
        if self.max.x < self.min.x \
                or self.min.x > self.max.x:
            self.min, self.max = self.max, self.min

        # prepare a list for overlapping curves
        self.bounded = set()

    def __repr__(self):
        return '<%s max=%s, min=%s weight=%s>' % (
            self.__class__.__name__,
            self.max,
            self.min,
            self.weight)

    def __hash__(self):
        d1 = self.direction[0]
        d2 = self.direction[1]
        if d1 < 0 and d2 < 0:
            d1 = abs(d1)
            d2 = abs(d2)
        elif d1 < 0 and d2 > 0:
            d1 = abs(d1)
            d2 = -d2
        return hash(('{:.3f}'.format(d1),
                     '{:.3f}'.format(d2),
                     '{:.3f}'.format(self.offset),
                     self.weight))

    def __eq__(self, other):
        return hash(self) == hash(other)

    @staticmethod
    def shortest_dist(x1, y1, x2, y2, x0, y0):
        # https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line
        # line passes thru (x1, y1), (x2, y2)
        # point is (x0, y0)
        return (abs(x0*(y2-y1)-y0*(x2-x1)+x2*y1-y2*x1) /
                math.sqrt((y2-y1)**2 + (x2-x1)**2))

    @staticmethod
    def get_style_weight(dline):
        graphic_style_cat = dline.LineStyle.GraphicsStyleCategory
        graphic_style_type = dline.LineStyle.GraphicsStyleType
        return graphic_style_cat.GetLineWeight(graphic_style_type)

    def dline_ids(self):
        return list(set([self.max.dlid, self.min.dlid]))

    def extends_max(self, dbound):
        if self.reverse:
            if dbound.x > self.max.x:
                if dbound.y < self.max.y:
                    return True
        else:
            if dbound.x > self.max.x:
                if dbound.y > self.max.y:
                    return True
        return False

    def extends_min(self, dbound):
        if self.reverse:
            if dbound.x < self.min.x:
                if dbound.y > self.min.y:
                    return True
        else:
            if dbound.x < self.min.x:
                if dbound.y < self.min.y:
                    return True
        return False

    def merge(self, dldomain):
        extends_max = self.extends_max(dldomain.max)
        extends_min = self.extends_min(dldomain.min)
        if extends_max and extends_min:
            logger.debug('Domain overlaps existing: %s', dldomain)
            logger.debug('Mark as bounded: %s', self.dline_ids())
            self.bounded.update(self.dline_ids())
            logger.debug('Extending max: %s -> %s', self.max, dldomain.max)
            self.max = dldomain.max
            logger.debug('Extending min: %s -> %s', self.min, dldomain.min)
            self.min = dldomain.min
        elif not extends_max and not extends_min:
            logger.debug('Domain is contained: %s', dldomain)
            logger.debug('Mark as bounded: %s', dldomain.dline_ids())
            self.bounded.update(dldomain.dline_ids())


class DetailLineDomainCollection(object):
    def __init__(self, include_style=False):
        self.domains = []
        self._include_style = include_style

    def __iter__(self):
        return iter(self.domains)

    def extend(self, dline):
        dldomain = DetailLineDomain(dline, include_style=self._include_style)
        if dldomain not in self.domains:
            logger.debug('New domain %s', dldomain)
            self.domains.append(dldomain)
        else:
            idx = self.domains.index(dldomain)
            ext_dldomain = self.domains[idx]
            logger.debug('Merging into existing domain %s', ext_dldomain)
            ext_dldomain.merge(dldomain)


def filter_lines(lines, view_specific):
    if view_specific is None:
        return lines
    else:
        return [x for x in lines if x.ViewSpecific == view_specific]


# ask user for options and process
options = ['All Lines', 'Detail Lines', 'Model Lines']
switches = {'Consider Line Weights': True}
selected_option, switches = \
    forms.CommandSwitchWindow.show(
        options,
        switches=switches,
        message='Pick overkill option:'
        )

if not switches['Consider Line Weights']:
    INCLUDE_STYLE = False

if selected_option == 'All Lines':
    VIEW_SPECIFIC = None
elif selected_option == 'Model Lines':
    VIEW_SPECIFIC = False
elif selected_option == 'Detail Lines':
    VIEW_SPECIFIC = True

if selected_option:
    # collect all detail-lines in active view
    logger.debug('Collecting detail lines in current view...')
    detline_collector = \
        revit.query.get_elements_by_class(DB.CurveElement,
                                        view_id=revit.activeview.Id)

    # collect comparison info on each detail-lines geomtery
    logger.debug('Extracting 2d domains...')
    detline_domaincl = DetailLineDomainCollection(include_style=INCLUDE_STYLE)
    for detline in filter_lines(detline_collector, view_specific=VIEW_SPECIFIC):
        logger.debug('Adding detail line to domains: %s', detline.Id.IntegerValue)
        detline_domaincl.extend(detline)

    del_count = 0
    with revit.Transaction('Overkill'):
        for detline_domain in detline_domaincl:
            bounded_detline_ids = \
                [DB.ElementId(x) for x in detline_domain.bounded]
            del_count += len(bounded_detline_ids)
            revit.doc.Delete(List[DB.ElementId](bounded_detline_ids))

    if del_count > 0:
        forms.alert('{} lines were removed.'.format(del_count))
    else:
        forms.alert('Pretty clean! No lines were removed.')
