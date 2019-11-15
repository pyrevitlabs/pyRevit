"""Methods and Classes to convert Revit types to serializable"""
from pyrevit import DB


class XYZ:
    def __init__(self, xyz):
        self.x = xyz.X
        self.y = xyz.Y
        self.z = xyz.Z

    def deserialize(self):
        return DB.XYZ(self.x, self.y, self.z)



class ViewOrientation3D:
    def __init__(self, view_orientation_3d):
        self.eye = XYZ(view_orientation_3d.EyePosition)
        self.forward = XYZ(view_orientation_3d.ForwardDirection)
        self.up = XYZ(view_orientation_3d.UpDirection)

    def deserialize(self):
        return DB.ViewOrientation3D(self.eye.deserialize(),
                                    self.up.deserialize(),
                                    self.forward.deserialize())


class Transform:
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


class BoundingBoxXYZ:
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


def serialize_list(input_list):
    result = []
    for item in input_list:
        item_serialized = None
        if isinstance(item, list):
            item_serialized = serialize_list(item)
        elif isinstance(item, DB.XYZ):
            item_serialized = XYZ(item)
        elif isinstance(item, DB.Transform):
            item_serialized = Transform(item)
        result.append(item_serialized)
    return result


def deserialize_list(input_list):
    for item in input_list:
        if isinstance(item, list):
            yield deserialize_list(item)
        else:
            if callable(getattr(item, "deserialize", None)):
                yield item.deserialize()
            else:
                yield item
