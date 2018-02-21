from rpw import DB
from rpw.base import BaseObjectWrapper
from rpw.exceptions import RpwCoerceError
from rpw.db.transform import Transform
from collections import OrderedDict

class XYZ(BaseObjectWrapper):
    """
    `DB.XYZ` Wrapper

    XYZ light wrapper with a few helpful methods:

    >>> from rpw.db import db
    >>> pt = db.XYZ(some_point)
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

    def __init__(self, *point_reference):
        """
        XYZ Supports a wide variety of instantiation overloads:

        >>> XYZ(0,0)
        >>> XYZ(0,0,0)
        >>> XYZ([0,0])
        >>> XYZ([0,0,0])
        >>> XYZ(DB.XYZ(0,0,0))

        Args:
            point_reference (``DB.XYZ``,``iterable``, ``args``): Point like data
        """
        # XYZ(0,0,0)
        if len(point_reference) == 3:
            xyz = DB.XYZ(*point_reference)
        # XYZ(0,0)
        elif len(point_reference) == 2:
            xyz = DB.XYZ(point_reference[0], point_reference[1], 0)
        # XYZ([0,0,0]) or # XYZ([0,0])
        elif len(point_reference) == 1 and isinstance(point_reference[0], (tuple, list)):
            # Assumes one arg, tuple
            xyz = XYZ(*point_reference[0])
            xyz = DB.XYZ(*xyz.as_tuple)
        # XYZ(DB.XYZ(0,0,0))
        elif len(point_reference) == 1 and isinstance(point_reference[0], DB.XYZ):
            # Assumes one arg, DB.XYZ
            xyz = point_reference[0]
        elif len(point_reference) == 1 and isinstance(point_reference[0], XYZ):
            # Assumes one arg, DB.XYZ
            xyz = point_reference[0].unwrap()
        else:
            raise RpwCoerceError(point_reference, 'point-like object')
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

    def at_z(self, z, wrapped=True):
        """ Returns a new point at the passed Z value

        Args:
            z(float): Elevation of new Points

        Returns:
            (:any:`XYZ`): New Points
        """
        return XYZ(self.x, self.y, z) if wrapped else DB.XYZ(self.x, self.y, z)

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
        return OrderedDict([('x', self.x), ('y', self.y), ('z', self.z)])

    def rotate(self, rotation, axis=None, radians=False):
        rotated_xyz = Transform.rotate_vector(self.unwrap(),
                                              rotation,
                                              center=None,
                                              axis=axis,
                                              radians=radians)
        return rotated_xyz

    def __mul__(self, value):
        """ Multiplication Method """
        return XYZ(self.unwrap() * value)

    def __add__(self, point):
        """ Addition Method """
        return XYZ(self.unwrap() + XYZ(point).unwrap())

    def __sub__(self, point):
        """ Subtraction Method """
        return XYZ(self.unwrap() - XYZ(point).unwrap())

    def __eq__(self, other):
        """ Equality Method """
        return self._revit_object.IsAlmostEqualTo(XYZ(other).unwrap())

    def __repr__(self):
        return super(XYZ, self).__repr__(data=self.as_dict,
                                         to_string='Autodesk.Revit.DB.XYZ')
