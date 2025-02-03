"""
Parameter Wrapper

>>> wrapped_element.parameters['Length']
10.0
>>> wrapped_element.parameters['Length'] = 5
5.0

"""  #
from rpw import revit, DB
from rpw.db.builtins import BipEnum
from rpw.base import BaseObjectWrapper
from rpw.exceptions import RpwException, RpwWrongStorageType
from rpw.exceptions import RpwParameterNotFound, RpwTypeError
from rpw.utils.logger import logger
from pyrevit.compat import get_elementid_value_func


class ParameterSet(BaseObjectWrapper):
    """
    Allows you to treat an element's parameters as a dictionary.

    This is used internally by Element Wrapper.
    An instance of this class is returned on the ``parameters``
    attribute of wrapped elements.

    >>> element.parameters.all()
    >>> element.parameters['Comments'].value
    >>> element.parameters['Comments'].type

    ParameterSet can also be used for setting values:
    >>> element.parameters['Comments'].value = 'Something'

    >>> parameters = ParameterSet(Element)

    Attributes:
        _revit_object (DB.Element) = Revit Reference

    """

    _revit_object_class = DB.Element

    def __init__(self, element):
        """
        Args:
            element(DB.Element): Element to create ParameterSet
        """
        super(ParameterSet, self).__init__(element)
        self.builtins = _BuiltInParameterSet(self._revit_object)

    def get_value(self, param_name, default_value=None):
        try:
            return self.__getitem__(param_name).value
        except RpwParameterNotFound:
            return default_value

    def __getitem__(self, param_name):
        """ Get's parameter by name.

        Returns:
            :any:`Parameter`: The first parameter found with a matching name (wrapper),

        Raises:
            :class:`RpwParameterNotFound`

        """
        # TODO: Any advantage of using ParameterMap Instead
        parameter = self._revit_object.LookupParameter(param_name)
        # return _Parameter(parameter) if parameter else None
        if not parameter:
            raise RpwParameterNotFound(self._revit_object, param_name)
        return Parameter(parameter)

    def __setitem__(self, param_name, value):
        """ Sets value to element's parameter.
        This is a shorcut to using `parameters['Name'].value = value`

        >>> element.parameters['Height'] = value
        """
        parameter = self.__getitem__(param_name)
        parameter.value = value

    @property
    def all(self):
        """ Returns: Flat list of wrapped parameter elements
        """
        return [Parameter(parameter) for parameter in self._revit_object.Parameters]

    def to_dict(self):
        """ WIP: Returns a Serializable Dictionary """
        return [p.to_dict() for p in self.all]

    def __len__(self):
        return len(self.all)

    def __repr__(self):
        """ Adds data to Base __repr__ to add Parameter List Name """
        return super(ParameterSet, self).__repr__(data={'count': len(self)})


class _BuiltInParameterSet(BaseObjectWrapper):
    """ Built In Parameter Manager

    Usage:

        location_line = element.parameters.builtins['WALL_LOCATION_LINE']

    Note:
        Item Getter can take the BuilInParameter name string, or the Enumeration.
        >>> element.parameters.builtins['WALL_LOCATION_LINE']

        or

        >>>element.parameters.builtins[Revit.DB.BuiltInParameter.WALL_LOCATION_LINE]

    Attributes:
        _revit_object (DB.Element) = Revit Reference

    """

    _revit_object_class = DB.Element

    def __getitem__(self, builtin_enum):
        """ Retrieves Built In Parameter. """
        if isinstance(builtin_enum, str):
            builtin_enum = BipEnum.get(builtin_enum)
        parameter = self._revit_object.get_Parameter(builtin_enum)
        if not parameter:
            raise RpwParameterNotFound(self._revit_object, builtin_enum)
        return Parameter(parameter)

    def __setitem__(self, name, param_value):
        """ Sets value for an element's built in parameter. """
        builtin_parameter = self.__getitem__(name)
        builtin_parameter.value = param_value

    def __repr__(self):
        """ Adds data to Base __repr__ to add Parameter List Name """
        return super(_BuiltInParameterSet, self).__repr__()


class Parameter(BaseObjectWrapper):
    """
    Primarily for internal use by :any:`rpw.db.Element`, but can be used on it's own.

    >>> parameter = Parameter(DB.Parameter)
    >>> parameter.type
    <type: str>
    >>> parameter.value
    'Some String'
    >>> parameter.name
    'Parameter Name'
    >>> parameter.builtin
    Revit.DB.BuiltInParameter.SOME_BUILT_IN_NAME

    Attributes:
        _revit_object (DB.Parameter) = Revit Reference

    Note:

        Parameter Wrapper handles the following types:

        * Autodesk.Revit.DB.StorageType.String
        * Autodesk.Revit.DB.StorageType.Double
        * Autodesk.Revit.DB.StorageType.ElementId
        * Autodesk.Revit.DB.StorageType.Integer
        * Autodesk.Revit.DB.StorageType.None


    """

    _revit_object_class = DB.Parameter
    STORAGE_TYPES = {
                    'String': str,
                    'Double': float,
                    'Integer': int,
                    'ElementId': DB.ElementId,
                    'None': None,
                     }

    def __init__(self, parameter):
        """ Parameter Wrapper Constructor

        Args:
            DB.Parameter: Parameter to be wrapped

        Returns:
            Parameter: Wrapped Parameter Class
        """
        if not isinstance(parameter, DB.Parameter):
            raise RpwTypeError(DB.Parameter, type(parameter))
        super(Parameter, self).__init__(parameter)

    @property
    def type(self):
        """ Returns the Python Type of the Parameter

        >>> element.parameters['Height'].type
        <type: float>

        Returns:
            (``type``): Python Built in type

        """
        storage_type_name = self._revit_object.StorageType.ToString()
        python_type = Parameter.STORAGE_TYPES[storage_type_name]

        return python_type

    @property
    def parameter_type(self):
        parameter_type = self._revit_object.Definition.ParameterType
        return parameter_type

    @property
    def id(self):
        return self._revit_object.Id

    @property
    def value(self):
        """
        Gets Parameter Value:

        >>> desk.parameters['Height'].value
        >>> 3.0

        Sets Parameter Value (must be in Transaction Context):

        >>> desk.parameters['Height'].value = 3

        Returns:
            (``type``): parameter value in python type


        Note:

            `Parameter` value setter automatically handles a few type castings:

            * Storage is ``str`` and value is ``None``; value is converted to ``blank_string``
            * Storage is ``str`` and value is ``any``; value is converted to ``string``
            * Storage is ``ElementId`` and value is ``None``; value is
              converted to ``ElemendId.InvalidElementId``
            * Storage is ``int`` and value is ``float``; value is converted to ``int``
            * Storage is ``float`` and value is ``int``; value is converted to ``float``

        """
        if self.type is str:
            return self._revit_object.AsString()
        if self.type is float:
            return self._revit_object.AsDouble()
        if self.type is DB.ElementId:
            return self._revit_object.AsElementId()
        if self.type is int:
            return self._revit_object.AsInteger()

        raise RpwException('could not get storage type: {}'.format(self.type))

    @value.setter
    def value(self, value):
        if self._revit_object.IsReadOnly:
            definition_name = self._revit_object.Definition.Name
            raise RpwException('Parameter is Read Only: {}'.format(definition_name))

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
            elif isinstance(value, bool) and self.type is int:
                value = int(value)
            else:
                raise RpwWrongStorageType(self.type, value)

        param = self._revit_object.Set(value)
        return param

    @property
    def value_string(self):
        """ Ensure Human Readable String Value """
        return self._revit_object.AsValueString() or \
               self._revit_object.AsString()

    def to_dict(self):
        """
        Returns Parameter as a dictionary. Included properties are:

            * name: Parameter.Definition.Name
            * type: Parameter.StorageType.Name
            * value: Uses best parameter method based on StorageType
            * value_string: Parameter.AsValueString
        """
        if not isinstance(self.value, DB.ElementId):
            value = self.value
        else:
            get_elementid_value = get_elementid_value_func()
            value = get_elementid_value(self.value)
        return {
                'name': self.name,
                'type': self.type.__name__,
                'value': value,
                'value_string': self.value_string
                }

    def __bool__(self):
        return bool(self.value)

    def __eq__(self, other):
        """ Equal Parameter Value Comparison """
        return self.value == other

    def __ne__(self, other):
        """ Not Equal Parameter Value Comparison """
        return self.value != other

    def __gt__(self, other):
        """ Greater than Parameter Value Comparison """
        return self.value > other

    def __ge__(self, other):
        """ Greater or Equal Parameter Value Comparison """
        return self.value >= other

    def __lt__(self, other):
        """ Less than Parameter Value Comparison """
        return self.value < other

    def __le__(self, other):
        """ Less or Equal Parameter Value Comparison """
        return self.value <= other

    @property
    def name(self):
        """
        Returns Parameter name

        >>> element.parameters['Comments'].name
        >>> 'Comments'
        """
        return self._revit_object.Definition.Name

    @property
    def builtin(self):
        """ Returns the BuiltInParameter name of Parameter.
        Same as DB.Parameter.Definition.BuiltIn

        Usage:
            >>> element.parameters['Comments'].builtin_name
            Revit.DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS

        Returns:
            Revit.DB.BuiltInParameter: BuiltInParameter Enumeration Member
        """
        return self._revit_object.Definition.BuiltInParameter

    @property
    def builtin_id(self):
        """ ElementId of BuiltIn

        Usage:
            >>> wall.parameters['Unconnected Height'].builtin_id
            Revit.DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM
        """
        return DB.ElementId(self.builtin)

    def __repr__(self):
        """ Adds data to Base __repr__ to add selection count"""
        return super(Parameter, self).__repr__(data={
                                            'name': self.name,
                                            'value': self.value,
                                            'type': self.type.__name__
                                            })
