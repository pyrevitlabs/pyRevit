import rpw
from rpw import revit, DB
from rpw.base import BaseObjectWrapper


class BoundingBox(BaseObjectWrapper):

#     """ BoundingBoxElement receives a Revit Object for access to properties.
#     Usage:
#     bbox = BoundingBoxElement(element)
#     bbox.element: element
#     Properties:
#     bbox.min: min coordinate of bounding box
#     bbox.max: min coordinate of bounding box
#     bbox.average: min coordinate of bounding box
#     """
#
    def __init__(self, element):
        raise NotImplemented
#         self.element = element
#         self.bbox = element.get_BoundingBox(revit.doc.ActiveView)
#
#     @property
#     def min(self):
#         x, y, z = self.bbox.Min.X, self.bbox.Min.Y, self.bbox.Min.Z
#         return PointElement(x, y, z)
#
#     @property
#     def max(self):
#         x, y, z = self.bbox.Max.X, self.bbox.Max.Y, self.bbox.Max.Z
#         return PointElement(x, y, z)
#
#     @property
#     def average(self):
#         return PointCollection(self.min, self.max).average
#
#     def __repr__(self):
#         return '<BB: MIN{} MAX={} CENTER={}>'.format(self.min, self.max,
#                                                      self.center)
#
#     def __str__(self):
#         return repr(self)
#
# class Curve():
#     pass
