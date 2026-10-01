""" Curve Wrappers """

from math import pi as PI

from rpw import revit, DB
from rpw.base import BaseObjectWrapper
from rpw.db.element import Element
from rpw.db.xyz import XYZ
from rpw.utils.mixins import ByNameCollectMixin


class Curve(BaseObjectWrapper):
    """
    DB.Curve Wrapper

    >>> curve = Curve.new(ExistingCurveObject)
    >>> curve.create_detail()

    """

    _revit_object_class = DB.Curve

    def create_detail(self, view=None, doc=revit.doc):
        """
        Args:
            view (``DB.View``): Optional View. Default: ``uidoc.ActiveView``
            doc (``DB.Document``): Optional Document. Default: ``doc``
        """
        # TODO: Accept Detail Type (GraphicStyle)
        view = view or revit.active_view.unwrap()
        return doc.Create.NewDetailCurve(view, self._revit_object)

    def create_model(self, view=None, doc=revit.doc):
        # http://www.revitapidocs.com/2017.1/b880c4d7-9841-e44e-2a1c-36fefe274e2e.htm
        raise NotImplemented


class Line(Curve):

    """
    DB.Line Wrapper

    >>> line = Line.new([-10,0], [10,0])
    >>> # or
    >>> line = Line.new(ExistingLineObject)
    >>> line.create_detail()

    """
    _revit_object_class = DB.Line

    @classmethod
    def new(cls, pt1, pt2):
        """
        Args:
            point1 (``point``): Point like object. See :any:`XYZ`
            point2 (``point``): Point like object. See :any:`XYZ`
        """
        pt1 = XYZ(pt1)
        pt2 = XYZ(pt2)
        line = DB.Line.CreateBound(pt1.unwrap(), pt2.unwrap())
        return cls(line)

    @property
    def start_point(self):
        """ Start Point of line """
        return XYZ(self._revit_object.GetEndPoint(0))

    @property
    def end_point(self):
        """ End Point of line """
        return XYZ(self._revit_object.GetEndPoint(1))

    @property
    def mid_point(self):
        """ Mid Point of line """
        return XYZ(self._revit_object.GetEndPoint(0.5))

    @property
    def end_points(self):
        """ End Points of line """
        return (XYZ(self.start_point), XYZ(self.end_point))


class Ellipse(Curve):
    """

    >>> ellipse = Ellipse.new([-10,0], [10,0])
    >>> # or
    >>> ellipse = Ellipse.new(ExistingEllipseObject)
    >>> ellipse.create_detail()

    """
    _revit_object_class = DB.Ellipse

    @classmethod
    def new(cls, center, x_radius, y_radius, x_axis=None, y_axis=None,
            start_param=0.0, end_param=2*PI):
        """
        Args:
            center (``point``): Center of Ellipse
            x_radius (``float``): X Radius
            y_radius (``float``): Y Radius
            x_axis (``point``): X Axis
            y_axis (``point``): Y Axis
            start_param (``float``): Start Parameter
            end_param (``float``): End Parameter
        """
        center = XYZ(center).unwrap()
        x_axis = DB.XYZ(1,0,0) if x_axis is None else XYZ(x_axis).unwrap().Normalize()
        y_axis = DB.XYZ(0,1,0) if y_axis is None else XYZ(y_axis).unwrap().Normalize()

        start_param = start_param or 0.0
        end_param = start_param or PI*2

        ellipse = DB.Ellipse.Create(center, x_radius, y_radius, x_axis, y_axis, start_param, end_param)
        return cls(ellipse)

class Circle(Ellipse):
    """

    >>> circle = Circle.new([-10,0], 2)
    >>> # or
    >>> circle = Circle.new(ExistingCircleObject)
    >>> circle.create_detail()

    """

    @classmethod
    def new(cls, center,
            radius,
            x_axis=None, y_axis=None,
            start_param=0.0, end_param=2*PI):
        """
        Args:
            center (``point``): Center of Ellipse
            x_radius (``float``): X Radius
            x_axis (``point``): X Axis
            y_axis (``point``): Y Axis
            start_param (``float``): Start Parameter
            end_param (``float``): End Parameter
        """
        center = XYZ(center).unwrap()
        x_axis = DB.XYZ(1,0,0) if x_axis is None else XYZ(x_axis).unwrap().Normalize()
        y_axis = DB.XYZ(0,1,0) if y_axis is None else XYZ(y_axis).unwrap().Normalize()

        start_param = start_param or 0.0
        end_param = start_param or PI*2

        circle = DB.Ellipse.Create(center, radius, radius, x_axis, y_axis, start_param, end_param)
        return cls(circle)


class Arc(Curve):
    """

    >>> arc = Arc.new([0,0], [0,0], [0,0])
    >>> # or
    >>> arc = Arc.new(ExistingArcObject)
    >>> arc.create_detail()

    """

    @classmethod
    def new(cls, *args):
            # http://www.revitapidocs.com/2017.1/19c3ba08-5443-c9d4-3a3f-0e78901fe6d4.htm
            # XYZ, XYZ, XYZ
            # Plane, Double, Double, Double (Plane, Radius, startAngle, endAngle)
            # XYZ, Double, Double, Double ,XYZ, XYZ (Center, radius, vectors, angles)
        """
        Args:
            start_pt (``point``): Start Point
            mid_pt (``point``): End Point
            end_pt (``point``): Mid Point
        """
        if len(args) == 3:
            start_pt, end_pt, mid_pt = [XYZ(pt).unwrap() for pt in args]
            arc = DB.Arc.Create(start_pt, end_pt, mid_pt)
        else:
            raise NotImplemented('only arc by 3 pts available')
        return cls(arc)
