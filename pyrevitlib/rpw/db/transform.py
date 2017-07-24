""" Transform Wrappers """

import math
import rpw
from rpw import DB
from rpw.base import BaseObjectWrapper
from rpw.db.xyz import XYZ

class Transform(BaseObjectWrapper):
    """
    `DB.Transform` Wrapper

    >>> from rpw.db import Transform
    >>> Transform

    Attributes:
        _revit_object (DB.XYZ): Wrapped ``DB.Transform``
    """

    _revit_object_class = DB.Transform

    @classmethod
    def rotate_vector(cls, vector, rotation, center=None, axis=None):
        """ Rotate a Vector by Degrees """

        vector = XYZ(vector)
        angle_rad = math.radians(rotation)
        axis =  XYZ(DB.XYZ(0,0,1)) if not axis else XYZ(axis)
        center =  XYZ(DB.XYZ(0,0,0)) if not center else XYZ(center)
        transform = cls._revit_object_class.CreateRotationAtPoint(
                                                        axis.unwrap(),
                                                        angle_rad,
                                                        center.unwrap())

        return XYZ(transform.OfVector(vector.unwrap()))

    @classmethod
    def move(cls, vector, object):
        """ Rotate a Vector by Degrees """

        raise NotImplemented
        # vector = XYZ(vector)
        # transform = cls._revit_object_class.CreateTranslation(vector)
