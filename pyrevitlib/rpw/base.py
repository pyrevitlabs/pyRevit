"""
All Wrappers inherit from this base class, which has 4 responsibilities:

* Instantiating python class and storing wrapped element (from Revit API).
* Provides a ``unwrap()`` method, which returns the wrapped object.
* Provides access to all original methods and attributes of the wrapped object.
* Create a ``__repr__()`` method for consistent representation

Because access to original methods and properties is maintained, you can keep
the elements wrapped throughout your code. You would only need to unwrap when
when passing the element into function where the original Type is expected.
"""

# noinspection PyUnresolvedReferences
from rpw import DB, get_logger, HOST_API_NAMESPACE
from rpw import RpwException, RpwTypeError, RpwAttributeError


logger = get_logger(__name__)


class BaseObject(object):
    def __init__(self, *args, **kwargs):
        pass

    def __repr__(self, data=None, wrapping=None):
        base_repr = '%s' % self.__class__.__name__

        # inserting wrapperd element, read '%' as 'wrapping'
        # e.g. <rpw.BaseObjectWrapper % Autodesk.Revit.DB.ElementType>
        if wrapping:
            base_repr += ' %% %s' % wrapping

        if not data:
            # basic repr if no data
            return '<%s>' % base_repr
        else:
            # if data dict is provided, make a str repr of the data
            data_repr = ''
            for k, v in data.items():
                data_repr += ' %s:%s' % (k, v)
            # add data repr to the output
            return '<%s%s>' % (base_repr, data_repr)


class BaseObjectWrapper(BaseObject):
    def __init__(self, revit_object, enforce_type=None, enforce_types=None):
        """
        Child classes can use self._wrapped_object to refer to
        the wrapped Revit APIObject or Element. In Revit API, Element does
        not subclass from APIObject. But in RPW, BaseObjectWrapper is the
        parent class to all other wrappers including Revit Element wrappers.

        Arguments:
            revit_object(APIObject): Revit APIObject to store
        """

        super(BaseObjectWrapper, self).__init__()

        if enforce_type and not isinstance(revit_object, enforce_type):
            raise RpwTypeError(enforce_type, type(revit_object))
        if enforce_types and not isinstance(revit_object, enforce_types):
            raise RpwTypeError(enforce_type, type(revit_object))

        super(BaseObjectWrapper, self).__setattr__('_wrapped_object',
                                                   revit_object)

    def __str__(self):
        return repr(self)

    # noinspection PyMethodOverriding
    def __repr__(self, data=None):
        # pass the wrapped element name and data to the original repr
        if hasattr(self._wrapped_object, 'ToString'):
            wrapping_element = self._wrapped_object.ToString()
            wrapping_element = \
                wrapping_element.replace(HOST_API_NAMESPACE + '.', '')
        else:
            wrapping_element = type(self._wrapped_object).__name__

        return super(BaseObjectWrapper, self)\
            .__repr__(data=data, wrapping=unicode(wrapping_element))

    def __getattr__(self, attr):
        """
        Getter for methods and properties of this python class or
        the wrapped Revit APIObject. This method is only called if the
        attribute name does not already exist in the class dictionary.

        Raises:
            RpwException: if wrapped element does not exist.
            AttributeError: if attribute does not exist.
        """
        try:
            return getattr(self.__dict__['_wrapped_object'], attr)
        except KeyError:
            raise RpwException('{} is missing _wrapped_object.'
                               .format(self.__class__.__name__))

    def __setattr__(self, attr, value):
        """
        Setter for properties of this python class or the wrapped
        Revit APIObject. Setter allows setting of wrapped object properties,
        for example:
        ```WrappedWall.Pinned = True``

        Raises:
            AttributeError: On attribue set errors.
        """
        if hasattr(self._wrapped_object, attr):
            self._wrapped_object.__setattr__(attr, value)
        else:
            super(BaseObjectWrapper, self).__setattr__(attr, value)

    def unwrap(self):
        return self._wrapped_object


class BaseEnumWrapper(BaseObject):
    def __init__(self, api_enum):
        super(BaseEnumWrapper, self).__init__()
        self._api_enum = api_enum

    def get(self, parameter_name):
        try:
            enum = getattr(self._api_enum, parameter_name)
        except AttributeError:
            raise RpwAttributeError(DB.BuiltInParameter, parameter_name)
        return enum

    def get_id(self, parameter_name):
        enum = self.get(parameter_name)
        return DB.ElementId(enum)
