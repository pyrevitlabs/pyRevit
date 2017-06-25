from rpw import DB
from rpw.base import BaseObjectWrapper
from rpw.exceptions import RpwCoerceError


class XYZ(BaseObjectWrapper):
    """
    `DB.XYZ` Wrapper

    XYZ light wrapper with a few helpful methods:

    >>> from rpw.db import XYZ
    >>> pt = XYZ(some_point)
    >>> pt.as_tuple
    (0,0,0)
    >>> pt.x = 10
    <rpw:XYZ % DB.XYZ: 0,0,10>
    >>> pt.at_z(5)
    <rpw:XYZ % DB.XYZ: 0,0,5>
    >>> pt.as_dict()
    {'x': 0, 'y':0, 'z':5}

    Attributes:
        _revit_object (DB.XYZ): Wrapped ``DB.XYZ``
    """

    _revit_object_class = DB.XYZ

    def __init__(self, *xyz_or_tuple):
        """
        Args:
            instance (``DB.XYZ``): Instance of XYZ to be wrapped
        """
        if len(xyz_or_tuple) == 3:
            xyz = DB.XYZ(*xyz_or_tuple)
        elif len(xyz_or_tuple) == 2:
            xyz = DB.XYZ(xyz_or_tuple[0], xyz_or_tuple[1], 0)
        elif len(xyz_or_tuple) == 1 and isinstance(xyz_or_tuple[0], (tuple, list)):
            # Assumes one arg, tuple
            xyz = DB.XYZ(*xyz_or_tuple[0])
        elif isinstance(xyz_or_tuple, (list, tuple)):
            # Assumes one arg, DB.XYZ
            xyz = xyz_or_tuple[0]
        else:
            raise RpwCoerceError(xyz_or_tuple, 'point-like object')
        super(XYZ, self).__init__(xyz)

    @property
    def x(self):
        """X Value"""
        return self._revit_object.X

    @property
    def y(self):
        """Y Value"""
        return self._revit_object.Y

    @property
    def z(self):
        """Z Value"""
        return self._revit_object.Z

    @x.setter
    def x(self, value):
        self._revit_object = DB.XYZ(value, self.y, self.z)

    @y.setter
    def y(self, value):
        self._revit_object = DB.XYZ(self.x, value, self.z)

    @z.setter
    def z(self, value):
        self._revit_object = DB.XYZ(self.x, self.y, value)

    def at_z(self, z):
        """ Returns a new point at the passed Z value

        Args:
            z(float): Elevation of new Points

        Returns:
            (:any:`XYZ`): New Points
        """
        return XYZ(self.x, self.y, z)

    @property
    def as_tuple(self):
        """
        Tuple representing the xyz coordinate of the Point

        Returns:
            (tuple): tuple float of XYZ values

        """
        return (self.x, self.y, self.z)

    @property
    def as_dict(self):
        """
        Dictionary representing the xyz coordinate of the Point

        Returns:
            (dict): dict with float of XYZ values

        """
        return {'x': self.x, 'y': self.y, 'z':self.z}

    def __repr__(self):
        return super(XYZ, self).__repr__(data=self.as_dict,
                                         to_string='Autodesk.Revit.DB.XYZ')
