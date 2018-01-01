""" Transform Wrappers """

import math
import rpw
from rpw import DB
from rpw.base import BaseObjectWrapper

class Transform(BaseObjectWrapper):
    """
    `DB.Transform` Wrapper

    Attributes:
        _revit_object (DB.XYZ): Wrapped ``DB.Transform``
    """

    _revit_object_class = DB.Transform

    @classmethod
    def rotate_vector(cls, vector, rotation, center=None, axis=None, radians=False):
        """ Rotate a Vector or point

        Usage:
        >>> from rpw import db
        >>> db.Transform.rotate_vector(SomeVector, 90.0)

        Args:
            vector (``point-like``): Point like element.
            rotation (``float``): Rotation in degrees.
            center (``point-like``, optional): Center of rotation [default: 0,0,0]
            axis (``point-like``, optional): Axis of rotation [default: 0,0,1]
            radians (``bool``, optional): True for rotation angle is in radians [default: False]

        Returns:
            ``point-like``: Rotate Vector
            """
        XYZ = rpw.db.XYZ
        vector = XYZ(vector)
        if radians:
            angle_rad = rotation
        else:
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
