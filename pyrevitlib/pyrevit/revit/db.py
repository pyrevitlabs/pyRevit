from pyrevit import PyRevitException
from pyrevit import DB
from Autodesk.Revit.DB import Element


__all__ = ('BaseWrapper', 'ElementWrapper', )


class BaseWrapper(object):
    def __init__(self, obj):
        self._wrapped = obj

    def __repr__(self, data=None):
        pdata = dict()
        if hasattr(self._wrapped, 'Id'):
            pdata['id'] = self._wrapped.Id.IntegerValue

        if data:
            pdata.update(data)

        datastr = ' '.join(['{0}:{1}'.format(k, v)
                            for k, v in pdata.iteritems()])
        return '<pyrevit.revit.{class_name} % {wrapping}{datastr}>' \
               .format(class_name=self.__class__.__name__,
                       wrapping=self._wrapped.ToString(),
                       datastr=(' ' + datastr) if datastr else '')

    def unwrap(self):
        return self._wrapped


class ElementWrapper(BaseWrapper):
    def __init__(self, element):
        super(ElementWrapper, self).__init__(element)
        if not isinstance(self._wrapped, DB.Element):
            raise PyRevitException('Can not wrap object that are not '
                                   'derived from Element.')

    @property
    def assoc_doc(self):
        return self._wrapped.Document

    @property
    def name(self):
        # have to use the imported Element otherwise
        # AttributeError occurs
        return Element.Name.__get__(self._wrapped)

    @property
    def symbol_name(self):
        return Element.Name.GetValue(self._wrapped.Symbol.Family)

    @property
    def id(self):
        return self._wrapped.Id

    @property
    def unique_id(self):
        return self._wrapped.UniqueId

    @property
    def workset_id(self):
        return self._wrapped.WorksetId

    @property
    def mark(self):
        mparam = self._wrapped.LookupParameter('Mark')
        return mparam.AsString() if mparam else ''

    @property
    def location(self):
        return (self.x, self.y, self.z)

    @property
    def x(self):
        return self._wrapped.Location.Point.X

    @property
    def y(self):
        return self._wrapped.Location.Point.Y

    @property
    def z(self):
        return self._wrapped.Location.Point.Z

    def get_param(self, param_name):
        return self._wrapped.LookupParameter(param_name)
