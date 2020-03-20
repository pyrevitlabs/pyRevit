# pylint: disable=missing-docstring,invalid-name,too-few-public-methods
"""Methods and Classes to convert Revit types to serializable"""
from pyrevit import PyRevitException, api
from pyrevit import DB
from pyrevit.compat import Iterable
from pyrevit import coreutils


__all__ = ('serialize', 'deserialize')


class Serializable(object):
    def __init__(self):
        pass

    def deserialize(self):
        return None


class EnumSerializable(Serializable):
    enum_type = None

    def __init__(self, enum_value):
        self.value = str(enum_value)

    def deserialize(self):
        return coreutils.get_enum_value(self.enum_type, self.value)


class NoneSerializer(Serializable):
    pass


class ElementId(Serializable):
    def __init__(self, element_id):
        self.integer_value = element_id.IntegerValue

    def deserialize(self):
        return DB.ElementId(self.integer_value)


class XYZ(Serializable):
    def __init__(self, xyz):
        self.x = xyz.X
        self.y = xyz.Y
        self.z = xyz.Z

    def deserialize(self):
        return DB.XYZ(self.x, self.y, self.z)


class UV(Serializable):
    def __init__(self, uv):
        self.u = uv.U
        self.v = uv.V

    def deserialize(self):
        return DB.UV(self.u, self.v)


class Line(Serializable):
    def __init__(self, line):
        self.start = XYZ(line.GetEndPoint(0))
        self.end = XYZ(line.GetEndPoint(1))

    def deserialize(self):
        return DB.Line.CreateBound(self.start.deserialize(),
                                   self.end.deserialize())


class CurveLoop(Serializable):
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
    def __init__(self, view_orientation_3d):
        self.eye = XYZ(view_orientation_3d.EyePosition)
        self.forward = XYZ(view_orientation_3d.ForwardDirection)
        self.up = XYZ(view_orientation_3d.UpDirection)

    def deserialize(self):
        return DB.ViewOrientation3D(self.eye.deserialize(),
                                    self.up.deserialize(),
                                    self.forward.deserialize())


class Transform(Serializable):
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
    enum_type = DB.ViewType


def serialize(api_object):
    if api_object is None:
        return NoneSerializer()

    if isinstance(api_object, Iterable):
        result_list = []
        for api_item in api_object:
            result_list.append(serialize(api_item))
        return result_list

    serializers = coreutils.get_all_subclasses(
        [Serializable, EnumSerializable]
        )

    try:
        compatible_serializer = \
            next(
                x for x in serializers
                if x.__name__ == api_object.GetType().Name
                )
        return compatible_serializer(api_object)
    except StopIteration:
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
