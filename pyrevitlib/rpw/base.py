"""
Base Object Wrapper Class

Most other wrappers inherit from this base class,
which has 4 primary responsibilities:

* Instantiates Class and stores wrapped element.
* Provides a ``unwrap()`` method to return the wrapped object.
* Provides access to all original methods and attributes of the
  wrapped object through a pass through ``__getattr__``
* Implements a ``__repr__()`` for consistent object representation

Because access to original methods and properties is maintained, you can keep
the elements wrapped throughout your code. You would only need to unwrap when
when passing the element into function where the original Type is expected.

>>> wrapped = BaseObjectWrapper(SomeObject)
>>> wrapped
<RPW_BaseOBjectWrapper:>
>>> wrapped.unwrap()
SomeObject
>>> wrapped.Pinned
False
>>> wrapped.AnyRevitPropertyOrMethod

Warning:
    This class is primarily for internal use. If you plan on creating your
    own wrappers using this base class make sure you read through the
    documentation first. Misusing this class can cause easilly cause
    Max Recursion Crashes.

"""

import rpw
from rpw.utils.logger import logger


class BaseObject(object):

        def __init__(self, *args, **kwargs):
            pass

        def ToString(self, *args, **kwargs):
            # Show correct repr on Dynamo
            return self.__repr__(*args, **kwargs)

        # def __dir__(self):
        # TODO: Implement Dir on BaseOBject and BaseObjectWrapper for proper AC
            # return list(self.__dict__)

        # TODO: Clean up repr. remove wraps, add brackets to data
        def __repr__(self, data=''):
            if data:
                data = ' '.join(['{0}:{1}'.format(k, v) for k, v in data.iteritems()])
            return '<rpw:{class_name} | {data}>'.format(
                                        class_name=self.__class__.__name__,
                                        data=data)


class BaseObjectWrapper(BaseObject):
    """
    Arguments:
        element(APIObject): Revit Element to store
    """

    def __init__(self, revit_object, enforce_type=True):
        """
        Child classes can use self._revit_object to refer back to Revit Element

        Warning:
            Any Wrapper that inherits and overrides __init__ class MUST
            ensure ``_revit_object`` is created by calling super().__init__
            before setting any self attributes. Not doing so will
            cause recursion errors and Revit will crash.
            BaseObjectWrapper should define a class variable _revit_object_class
            to define the object class being wrapped.

        """
        _revit_object_class = self.__class__._revit_object_class

        if enforce_type and not isinstance(revit_object, _revit_object_class):
            raise rpw.exceptions.RpwTypeError(_revit_object_class, type(revit_object))

        object.__setattr__(self, '_revit_object', revit_object)

    def __getattr__(self, attr):
        """
        Getter for original methods and properties or the element.
        This method is only called if the attribute name does not
        already exists.
        """
        try:
            return getattr(self.__dict__['_revit_object'], attr)
        # except AttributeError:
            # This lower/snake case to be converted.
            # This automatically gives acess to all names in lower case format
            # x.name (if was not already defined, will get x.Name)
            # Note: will not Work for setters, unless defined by wrapper
            # attr_pascal_case = rpw.utils.coerce.to_pascal_case(attr)
            # return getattr(self.__dict__['_revit_object'], attr_pascal_case)
        except KeyError:
            raise rpw.exceptions.RpwException('BaseObjectWrapper is missing _revit_object')

    def __setattr__(self, attr, value):
        """
        Setter allows setting of wrapped object properties, for example
        ```WrappedWall.Pinned = True``
        """
        if hasattr(self._revit_object, attr):
            self._revit_object.__setattr__(attr, value)
        else:
            object.__setattr__(self, attr, value)

    def unwrap(self):
        """ Returns the Original Wrapped Element """
        return self._revit_object

    def __repr__(self, data={}, to_string=None):
        """ ToString can be overriden for objects in which the method is
        not consistent - ie. XYZ.ToString returns pt tuple not Class Name """
        class_name = self.__class__.__name__

        revit_object_name = to_string or self._revit_object.ToString()
        revit_class_name = revit_object_name.split('.')[-1]
        if class_name != revit_class_name:
            class_name = '{} % {}'.format(class_name, revit_class_name)

        data = ''.join([' [{0}:{1}]'.format(k, v) for k, v in data.iteritems()])
        return '<rpw:{class_name}{data}>'.format(class_name=class_name,
                                                    data=data
                                                    )
