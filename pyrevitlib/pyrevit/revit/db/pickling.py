# pylint: disable=missing-docstring,invalid-name,too-few-public-methods
"""Methods and Classes to convert Revit types to serializable."""
from pyrevit import PyRevitException, api
from pyrevit import DB
from pyrevit.compat import Iterable
from pyrevit import coreutils
from pyrevit.coreutils import logger
from pyrevit.compat import get_elementid_value_func


__all__ = ('serialize', 'deserialize')


mlogger = logger.get_logger(__name__)


class Serializable(object):
    # single type or a tuple of types
    api_types = None

    def __init__(self):
        pass

    def deserialize(self):
        return None


class EnumSerializable(Serializable):
    def __init__(self, enum_value):
        self.value = str(enum_value)

    def deserialize(self):
        return coreutils.get_enum_value(self.api_types, self.value)


class NoneSerializer(Serializable):
    pass


class ElementId(Serializable):
    api_types = DB.ElementId
    def __init__(self, element_id):
        get_elementid_value = get_elementid_value_func()
        self.integer_value = get_elementid_value(element_id)

    def deserialize(self):
        return DB.ElementId(self.integer_value)


class XYZ(Serializable):
    api_types = DB.XYZ

    def __init__(self, xyz):
        self.x = xyz.X
        self.y = xyz.Y
        self.z = xyz.Z

    def deserialize(self):
        return DB.XYZ(self.x, self.y, self.z)


class UV(Serializable):
    api_types = DB.UV

    def __init__(self, uv):
        self.u = uv.U
        self.v = uv.V

    def deserialize(self):
        return DB.UV(self.u, self.v)


class Line(Serializable):
    api_types = DB.Line

    def __init__(self, line):
        self.start = XYZ(line.GetEndPoint(0))
        self.end = XYZ(line.GetEndPoint(1))

    def deserialize(self):
        return DB.Line.CreateBound(self.start.deserialize(),
                                   self.end.deserialize())


class CurveLoop(Serializable):
    api_types = DB.CurveLoop

    def __init__(self, crv_loop):
        self.curves = []
        for crv in crv_loop:
            self.curves.append(serialize(crv))

    def deserialize(self):
        crv_loop = DB.CurveLoop()
        for crv in self.curves:
            crv_loop.Append(crv.deserialize())
        return crv_loop


class ViewOrientation3D(Serializable):
    api_types = DB.ViewOrientation3D

    def __init__(self, view_orientation_3d):
        self.eye = XYZ(view_orientation_3d.EyePosition)
        self.forward = XYZ(view_orientation_3d.ForwardDirection)
        self.up = XYZ(view_orientation_3d.UpDirection)

    def deserialize(self):
        return DB.ViewOrientation3D(self.eye.deserialize(),
                                    self.up.deserialize(),
                                    self.forward.deserialize())


class Transform(Serializable):
    api_types = DB.Transform

    def __init__(self, transform):
        self.basis_x = XYZ(transform.BasisX)
        self.basis_y = XYZ(transform.BasisY)
        self.basis_z = XYZ(transform.BasisZ)
        self.origin = XYZ(transform.Origin)
        self.scale = transform.Scale

    def deserialize(self):
        transform = DB.Transform.Identity
        transform.BasisX = self.basis_x.deserialize()
        transform.BasisY = self.basis_y.deserialize()
        transform.BasisZ = self.basis_z.deserialize()
        transform.Origin = self.origin.deserialize()
        transform.ScaleBasis(self.scale)
        return transform


class BoundingBoxXYZ(Serializable):
    api_types = DB.BoundingBoxXYZ

    def __init__(self, bbox_xyz):
        self.min = XYZ(bbox_xyz.Min)
        self.max = XYZ(bbox_xyz.Max)
        self.transform = Transform(bbox_xyz.Transform)

    def deserialize(self):
        bbox_xyz = DB.BoundingBoxXYZ()
        bbox_xyz.Min = self.min.deserialize()
        bbox_xyz.Max = self.max.deserialize()
        bbox_xyz.Transform = self.transform.deserialize()
        return bbox_xyz


class ViewType(EnumSerializable):
    api_types = DB.ViewType


class Grid(Serializable):
    api_types = DB.Grid

    def __init__(self, gridline):
        from rpw import doc

        cView = doc.ActiveView
        curves=gridline.GetCurvesInView(DB.DatumExtentType.ViewSpecific, cView)
        cCurve = curves[0]
        start_curve = gridline.GetLeader(DB.DatumEnds.End0, cView)
        end_curve = gridline.GetLeader(DB.DatumEnds.End1, cView)

        if start_curve:
          self.start_elbow = XYZ(start_curve.Elbow.X, start_curve.Elbow.Y, start_curve.Elbow.Z)
          self.start_leader = XYZ(start_curve.End.X, start_curve.End.Y, start_curve.End.Z)
          self.start_anchor = XYZ(start_curve.Anchor.X, start_curve.Anchor.Y, start_curve.Anchor.Z)

        if end_curve:
          self.end_elbow = XYZ(end_curve.Elbow.X, end_curve.Elbow.Y, end_curve.Elbow.Z)
          self.end_leader = XYZ(end_curve.End.X, end_curve.End.Y, end_curve.End.Z)
          self.end_anchor = XYZ(end_curve.Anchor.X, end_curve.Anchor.Y, end_curve.Anchor.Z)

        self.grid_name = gridline.Name
        self.start = XYZ(cCurve.GetEndPoint(0))
        self.end = XYZ(cCurve.GetEndPoint(1))

        if isinstance(cCurve, DB.Arc):
          self.center = XYZ(cCurve.Center.X, cCurve.Center.Y, cCurve.Center.Z)

        self.starts_with_bubble = gridline.HasBubbleInView(DB.DatumEnds.End0, cView)
        self.start_bubble_visible = gridline.IsBubbleVisibleInView(DB.DatumEnds.End0, cView)

        self.ends_with_bubble = gridline.HasBubbleInView(DB.DatumEnds.End1, cView)
        self.end_bubble_visible = gridline.IsBubbleVisibleInView(DB.DatumEnds.End1, cView)

    def deserialize(self):
        name = self.grid_name
        start = DB.XYZ(self.start.deserialize())
        end = DB.XYZ(self.end.deserialize())
        center = DB.XYZ(self.center.deserialize())
        bubble_start = {self.starts_with_bubble, self.start_bubble_visible}
        bubble_end = {self.ends_with_bubble, self.end_bubble_visible}
        start_curve = {self.start_leader, self.start_elbow, self.start_anchor}
        end_curve = {self.end_leader, self.end_elbow, self.end_anchor}

        return name, start, end, center, bubble_start, bubble_end, start_curve, end_curve


def _serialize_items(iterable_obj):
    result_list = []
    for api_item in iterable_obj:
        result_list.append(serialize(api_item))
    return result_list


def serialize(api_object):
    mlogger.debug('Attemping to serialize: %s', api_object)

    # wrap none in a none serializer for none values
    if api_object is None:
        return NoneSerializer()

    # make sure given type is a Revit API type
    if not api.is_api_object(api_object):
        raise PyRevitException("Only Revit API types are supported.")

    # get available serializers
    serializers = coreutils.get_all_subclasses(
        [Serializable, EnumSerializable]
        )

    # pick the compatible serializer
    try:
        compatible_serializer = \
            next(
                x for x in serializers
                if x.api_types and isinstance(api_object, x.api_types)
                )
        mlogger.debug('Serializer found for: %s', api_object)
        return compatible_serializer(api_object)
    except StopIteration:
        mlogger.debug('Serializer not found for: %s', api_object)
        # if no deserializer found,
        # see if given data is iterable
        # NOTE: commented this out since .serialize should only get api objects
        # if isinstance(api_object, Iterable):
        #     mlogger.debug('Iterating over: %s', api_object)
        #     return _serialize_items(api_object)

        # otherwise throw an exception
        raise PyRevitException(
            "No serializers have been implemented for \"%s\"" % repr(api_object)
            )


def deserialize(python_object):
    if isinstance(python_object, Iterable):
        result_list = []
        for python_item in python_object:
            result_list.append(deserialize(python_item))
        return result_list

    if isinstance(python_object, Serializable):
        return python_object.deserialize()
