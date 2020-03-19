# pylint: disable=missing-docstring,invalid-name,too-few-public-methods
"""Methods and Classes to convert Revit types to serializable"""
import sys
import inspect
from pyrevit import DB


__all__ = ('ElementId', 'XYZ', 'UV', 'Line', 'CurveLoop', 'ViewOrientation3D',
           'Transform', 'BoundingBoxXYZ')


class ElementId(object):
    def __init__(self, element_id):
        self.integer_value = element_id.IntegerValue

    def deserialize(self):
        return DB.ElementId(self.integer_value)


class XYZ(object):
    def __init__(self, xyz):
        self.x = xyz.X
        self.y = xyz.Y
        self.z = xyz.Z

    def deserialize(self):
        return DB.XYZ(self.x, self.y, self.z)


class UV(object):
    def __init__(self, uv):
        self.u = uv.U
        self.v = uv.V

    def deserialize(self):
        return DB.UV(self.u, self.v)


class Line(object):
    def __init__(self, line):
        self.start = XYZ(line.GetEndPoint(0))
        self.end = XYZ(line.GetEndPoint(1))

    def deserialize(self):
        return DB.Line.CreateBound(self.start.deserialize(),
                                   self.end.deserialize())


class CurveLoop(object):
    def __init__(self, crv_loop):
        self.curves = []
        for crv in crv_loop:
            self.curves.append(serialize(crv))

    def deserialize(self):
        crv_loop = DB.CurveLoop()
        for crv in self.curves:
            crv_loop.Append(crv.deserialize())
        return crv_loop


class ViewOrientation3D(object):
    def __init__(self, view_orientation_3d):
        self.eye = XYZ(view_orientation_3d.EyePosition)
        self.forward = XYZ(view_orientation_3d.ForwardDirection)
        self.up = XYZ(view_orientation_3d.UpDirection)

    def deserialize(self):
        return DB.ViewOrientation3D(self.eye.deserialize(),
                                    self.up.deserialize(),
                                    self.forward.deserialize())


class Transform(object):
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


class BoundingBoxXYZ(object):
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


def serialize(value):
    if isinstance(value, list) or value.__class__.__name__.startswith('List['):
        result_list = []
        for value_item in value:
            result_list.append(serialize(value_item))
        return result_list
    elif value.__class__.__name__ in __all__:
        for mem in inspect.getmembers(sys.modules[__name__]):
            moduleobject = mem[1]
            if inspect.isclass(moduleobject) \
                    and hasattr(moduleobject, 'deserialize'):
                if moduleobject.__name__ == value.__class__.__name__:
                    return moduleobject(value)
    else:
        return value


def deserialize(value):
    if isinstance(value, list):
        result_list = []
        for value_item in value:
            result_list.append(deserialize(value_item))
        return result_list
    elif value.__class__.__name__ in __all__:
        if callable(getattr(value, "deserialize", None)):
            return value.deserialize()
    return value
