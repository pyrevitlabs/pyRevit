"""
Spatial Element Wrappers

"""  #

import rpw
from rpw import revit, DB
from rpw.db import Element
from rpw.utils.logger import logger
from rpw.db.builtins import BipEnum


class Room(Element):
    """
    `DB.Architecture.Room` Wrapper
    Inherits from :any:`Element`

    >>> from rpw import db
    >>> room = db.Room(SomeRoom)
    <rpw:Room % DB.Architecture.Room | name:Office number:122>
    >>> room.name
    'Office'
    >>> room.number
    '122'
    >>> room.is_placed
    True
    >>> room.is_bounded
    True

    Attribute:
        _revit_object (DB.Architecture.Room): Wrapped ``DB.Architecture.Room``
    """

    _revit_object_class = DB.Architecture.Room
    _revit_object_category = DB.BuiltInCategory.OST_Rooms
    _collector_params = {'of_category': _revit_object_category,
                         'is_not_type': True}

    @property
    def name(self):
        """ Room Name as parameter Value: ``ROOM_NAME`` built-in parameter"""
        # Note: For an unknown reason, roominstance.Name does not work on IPY
        return self.parameters.builtins['ROOM_NAME'].value

    @name.setter
    def name(self, value):
        self.parameters.builtins['ROOM_NAME'].value = value

    @property
    def number(self):
        """ Room Number as parameter Value: ``ROOM_NUMBER`` built-in parameter"""
        return self.parameters.builtins['ROOM_NUMBER'].value

    @number.setter
    def number(self, value):
        self.parameters.builtins['ROOM_NUMBER'].value = value

    # @property
    # def from_room(self, value):
        # TODO: from_room

    @property
    def is_placed(self):
        """ ``bool`` for whether Room is Placed.
        Uses result of ``Room.Location`` attribute to define if room is Placed.
        """
        return bool(self._revit_object.Location)

    @property
    def is_bounded(self):
        """ ``bool`` for whether Room is Bounded.
        Uses result of ``Room.Area`` attribute to define if room is Bounded.
        """
        return self._revit_object.Area > 0

    def __repr__(self):
        return super(Room, self).__repr__(data={'name': self.name,
                                                'number': self.number})


class Area(Room):
    """
    `DB.Area` Wrapper
    Inherits from :any:`Room`

    >>> from rpw import db
    >>> area = db.Area(SomeArea)
    <rpw:Area % DB.Area | name:USF area: 100.0>
    >>> area.name
    'Rentable'
    >>> area.is_placed
    True
    >>> area.is_bounded
    True

    Attribute:
        _revit_object (DB.Area): Wrapped ``DB.Area``
    """

    _revit_object_class = DB.Area
    _revit_object_category = DB.BuiltInCategory.OST_Areas
    _collector_params = {'of_category': _revit_object_category,
                         'is_not_type': True}

    @property
    def name(self):
        """ Area Scheme Name: Area attribute parameter"""
        return self.scheme.name

    @property
    def scheme(self):
        """ Area Scheme: Wrapped Area Scheme"""
        return AreaScheme(self._revit_object.AreaScheme)

    @property
    def area(self):
        """ Area: .Area attribute"""
        return self._revit_object.Area

    def __repr__(self):
        return super(Element, self).__repr__(data={'name': self.name,
                                                   'area': self.area})


class AreaScheme(Element):
    """
    `DB.AreaScheme` Wrapper
    Inherits from :any:`Element`

    >>> scheme = wrapped_area.scheme
    <rwp:AreaScheme % DB.AreaScheme | name:USF>
    >>> scheme.areas
    [ < Autodesk.Revit.DB.Area>, ...]
    >>> scheme.name
    'USF'

    Attribute:
        _revit_object (DB.AreaScheme): Wrapped ``DB.AreaScheme``
    """

    _revit_object_class = DB.AreaScheme
    _collector_params = {'of_class': _revit_object_class}

    @property
    def name(self):
        """ Area Scheme Name: Area attribute parameter"""
        return self._revit_object.Name

    @property
    def areas(self):
        """ Returns all Area Instances of this Area Scheme """
        bip = BipEnum.get_id('AREA_SCHEME_ID')
        param_filter = rpw.db.Collector.ParameterFilter(bip, equals=self._revit_object.Id)
        collector = rpw.db.Collector(parameter_filter=param_filter,
                                     **Area._collector_params)
        return collector.wrapped_elements

    def __repr__(self):
        return super(AreaScheme, self).__repr__(data={'name': self.name})
