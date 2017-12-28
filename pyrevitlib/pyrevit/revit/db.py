from pyrevit import PyRevitException
from pyrevit import DB
from Autodesk.Revit.DB import Element


__all__ = ('ElementWrapper', )


class ElementWrapper(object):
    def __init__(self, element):
        if isinstance(element, DB.Element):
            self._wrapped_element = element
        else:
            raise PyRevitException('Can not wrap object that are not '
                                   'derived from Element.')

    def __repr__(self):
        return '<pyrevit.revit.{} % {} id:{}>' \
                    .format(self.__class__.__name__,
                            self._wrapped_element.ToString(),
                            self._wrapped_element.Id)

    def unwrap(self):
        return self._wrapped_element

    @property
    def assoc_doc(self):
        return self._wrapped_element.Document

    @property
    def name(self):
        # have to use the imported Element otherwise
        # AttributeError occurs
        return Element.Name.GetValue(self._wrapped_element)

    @property
    def id(self):
        return self._wrapped_element.Id

    @property
    def unique_id(self):
        return self._wrapped_element.UniqueId

    @property
    def workset_id(self):
        return self._wrapped_element.WorksetId

    @property
    def mark(self):
        mparam = self._wrapped_element.LookupParameter('Mark')
        return mparam.AsString() if mparam else ''

    @property
    def location(self):
        return (self.x, self.y, self.z)

    @property
    def x(self):
        return self._wrapped_element.Location.Point.X

    @property
    def y(self):
        return self._wrapped_element.Location.Point.Y

    @property
    def z(self):
        return self._wrapped_element.Location.Point.Z

    def get_param(self, param_name):
        return self._wrapped_element.LookupParameter(param_name)
