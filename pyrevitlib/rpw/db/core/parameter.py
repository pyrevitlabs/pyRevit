"""
Parameter Wrapper

"""

# noinspection PyUnresolvedReferences
from rpw import get_logger, RpwException, RpwTypeError, DB, BaseObjectWrapper
from rpw.db.core.builtins import BipEnum

logger = get_logger(__name__)


class RpwParameterNotFound(RpwException, AttributeError):
    """ Wrong Type"""
    def __init__(self, element, param_name):
        msg = 'parameter not found [element:{}]:[param_name:{}]' \
            .format(element, param_name)
        super(RpwParameterNotFound, self).__init__(msg)


class RpwWrongStorageType(RpwException, TypeError):
    """ Wrong Storage Type """
    def __init__(self, storage_type, value):
        msg = 'Wrong Storage Type: [{}]:[{}:{}]'.format(storage_type,
                                                        type(value), value)
        super(RpwWrongStorageType, self).__init__(msg)


class ParameterSet(BaseObjectWrapper):
    def __init__(self, element):
        super(ParameterSet, self).__init__(element)
        self.builtins = _BuiltInParameterSet(self._wrapped_object)

    def __getitem__(self, param_name):
        parameter = self._wrapped_object.LookupParameter(param_name)
        # return _Parameter(parameter) if parameter else None
        if not parameter:
            raise RpwParameterNotFound(self._wrapped_object, param_name)
        return Parameter(parameter)

    def __setitem__(self, param_name, value):
        parameter = self.__getitem__(param_name)
        parameter.value = value

    @property
    def all(self):
        if hasattr(self._wrapped_object, 'Parameters'):
            return [Parameter(parameter)
                    for parameter in self._wrapped_object.Parameters]
        else:
            return []

    def __len__(self):
        return len(self.all)

    # noinspection PyMethodOverriding
    def __repr__(self):
        return super(ParameterSet, self).__repr__(data={'count': len(self)})


class _BuiltInParameterSet(BaseObjectWrapper):
    def __getitem__(self, builtin_enum):
        """ Retrieves Built In Parameter. """
        if isinstance(builtin_enum, str):
            builtin_enum = BipEnum.get(builtin_enum)
        parameter = self._wrapped_object.get_Parameter(builtin_enum)
        if not parameter:
            raise RpwParameterNotFound(self._wrapped_object, builtin_enum)
        return Parameter(parameter)

    def __setitem__(self, name, param_value):
        """ Sets value for an element's built in parameter. """
        builtin_parameter = self.__getitem__(name)
        builtin_parameter.value = param_value

    # noinspection PyMethodOverriding
    def __repr__(self):
        """ Adds data to Base __repr__ to add Parameter List Name """
        return super(_BuiltInParameterSet, self).__repr__()


class Parameter(BaseObjectWrapper):
    storage_types = {
                    'Boolean': bool,
                    'String': str,
                    'Double': float,
                    'Integer': int,
                    'ElementId': DB.ElementId,
                    'None': None,
                     }

    def __init__(self, parameter):
        if not isinstance(parameter, DB.Parameter):
            raise RpwTypeError(DB.Parameter, type(parameter))
        super(Parameter, self).__init__(parameter)

    @property
    def type(self):
        storage_type_name = self._wrapped_object.StorageType.ToString()

        if storage_type_name == 'Integer' \
                and not unicode(self._wrapped_object.AsValueString()) \
                .lower().isdigit():
                return Parameter.storage_types['Boolean']
        return Parameter.storage_types[storage_type_name]

    @property
    def id(self):
        return self._wrapped_object.Id

    @property
    def value(self):
        if self.type is bool:
            return self._wrapped_object.AsInteger() == 1
        if self.type is str:
            return self._wrapped_object.AsString()
        if self.type is float:
            return self._wrapped_object.AsDouble()
        if self.type is int:
            return self._wrapped_object.AsInteger()
        if self.type is DB.ElementId:
            return self._wrapped_object.AsElementId()

        raise RpwException('could not get storage type: {}'.format(self.type))

    @value.setter
    def value(self, value):
        if self._wrapped_object.IsReadOnly:
            raise RpwException('Parameter is Read Only: {}'
                               .format(self._wrapped_object.Definition.Name))

        # Check if value provided matches storage type
        if not isinstance(value, self.type):
            # If not, try to handle
            if self.type is str and value is None:
                value = ''
            if self.type is str and value is not None:
                value = str(value)
            elif self.type is DB.ElementId and value is None:
                value = DB.ElementId.InvalidElementId
            elif isinstance(value, int) and self.type is float:
                value = float(value)
            elif isinstance(value, float) and self.type is int:
                value = int(value)
            else:
                raise RpwWrongStorageType(self.type, value)

        self._wrapped_object.Set(value)

    @property
    def name(self):
        return self._wrapped_object.Definition.Name

    @property
    def builtin(self):
        return self._wrapped_object.Definition.BuiltInParameter

    @property
    def builtin_id(self):
        return DB.ElementId(self.builtin)

    # noinspection PyMethodOverriding
    def __repr__(self):
        """ Adds data to Base __repr__ to add selection count"""
        return super(Parameter, self).__repr__(data={'name': self.name,
                                                     'value': self.value})
