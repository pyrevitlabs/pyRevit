# noinspection PyUnresolvedReferences
from rpw import DB, doc
from rpw.db.core import BipEnum
from rpw.db.core import Element, Collector


class Room(Element):
    _wrapped_class = DB.Architecture.Room
    _wrapped_category = DB.BuiltInCategory.OST_Rooms
    _collector_params = {'of_category': _wrapped_category,
                         'is_not_type': True}

    def __init__(self, room, enforce_type=_wrapped_class):
        super(Room, self).__init__(room, enforce_type=enforce_type)

    @property
    def name(self):
        return self.parameters.builtins['ROOM_NAME'].value

    @name.setter
    def name(self, value):
        self.parameters.builtins['ROOM_NAME'].value = value

    @property
    def number(self):
        return self.parameters.builtins['ROOM_NUMBER'].value

    @number.setter
    def number(self, value):
        self.parameters.builtins['ROOM_NUMBER'].value = value

    @property
    def is_placed(self):
        return bool(self._wrapped_object.Location)

    @property
    def is_bounded(self):
        return self._wrapped_object.Area > 0

    def __repr__(self, data=None):
        room_data = {'name': self.name, 'number': self.number}
        if data:
            room_data.update(data)
        return super(Room, self).__repr__(data=room_data)


class Area(Room):
    _wrapped_class = DB.Area
    _wrapped_category = DB.BuiltInCategory.OST_Areas
    _collector_params = {'of_category': _wrapped_category,
                         'is_not_type': True}

    def __init__(self, area, enforce_type=None):
        super(Area, self).__init__(area, enforce_type=enforce_type)

    @property
    def name(self):
        return self.scheme.name

    @property
    def scheme(self):
        return Element(self._wrapped_object.AreaScheme)

    @property
    def area(self):
        return self._wrapped_object.Area

    def __repr__(self, data=None):
        area_data = {'name': self.name, 'area': self.area}
        if data:
            area_data.update(data)
        return super(Element, self).__repr__(data=area_data)


class AreaScheme(Element):
    _wrapped_class = DB.AreaScheme
    _collector_params = {'of_class': _wrapped_class}

    def __init__(self, area_scheme):
        enforce_type = self.__class__._wrapped_class
        super(AreaScheme, self).__init__(area_scheme, enforce_type=enforce_type)

    @property
    def name(self):
        return self._wrapped_object.Name

    @property
    def areas(self):
        bip = BipEnum.get_id('AREA_SCHEME_ID')
        param_filter = \
            Collector.ParameterFilter(bip, equals=self._wrapped_object.Id)
        collector = Collector(parameter_filter=param_filter,
                              **Area._collector_params)
        return collector.wrapped_elements

    def __repr__(self, data=None):
        areascheme_data = {'name': self.name}
        if data:
            areascheme_data.update(data)
        return super(AreaScheme, self).__repr__(data=areascheme_data)
