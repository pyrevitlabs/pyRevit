import os.path as op

from pyrevit import HOST_APP, PyRevitException
from pyrevit.compat import safe_strtype
from pyrevit import DB
from Autodesk.Revit.DB import Element


__all__ = ('BaseWrapper', 'ElementWrapper', 'ExternalRef', 'ModelSharedParam',
           'CurrentProjectInfo', )


class BaseWrapper(object):
    def __init__(self, obj=None):
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
                       wrapping=safe_strtype(self._wrapped),
                       datastr=(' ' + datastr) if datastr else '')

    def unwrap(self):
        return self._wrapped

    @staticmethod
    def compare_attr(src, dest, attr_name, case_sensitive=False):
        if case_sensitive:
            return safe_strtype(getattr(src, attr_name, '')).lower() == \
                   safe_strtype(getattr(dest, attr_name, '')).lower()
        else:
            return safe_strtype(getattr(src, attr_name)) == \
                   safe_strtype(getattr(dest, attr_name))

    @staticmethod
    def compare_attrs(src, dest, attr_names, case_sensitive=False):
        return [BaseWrapper.compare_attr(src,
                                         dest,
                                         x,
                                         case_sensitive=case_sensitive)
                for x in attr_names]


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


class ExternalRef(BaseWrapper):
    def __init__(self, link, extref):
        super(ExternalRef, self).__init__(link)
        self._extref = extref

    @property
    def name(self):
        return DB.Element.Name.__get__(self._wrapped)

    @property
    def link(self):
        return self._wrapped

    @property
    def linktype(self):
        return self._extref.ExternalFileReferenceType

    @property
    def path(self):
        p = self._extref.GetPath()
        return DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(p)

    def reload(self):
        return self._wrapped.Reload()


class ModelSharedParam(BaseWrapper):
    def __init__(self, param_def, param_binding=None):
        super(ModelSharedParam, self).__init__()
        self.param_def = param_def
        self.param_binding = param_binding

    @property
    def name(self):
        return self.param_def.Name

    def __eq__(self, other):
        if isinstance(self.param_def, DB.ExternalDefinition):
            return self.param_def.GUID == other or self.name == other
        else:
            return self.name == other


class CurrentProjectInfo(BaseWrapper):
    def __init__(self):
        super(CurrentProjectInfo, self).__init__()

    @property
    def name(self):
        if not HOST_APP.doc.IsFamilyDocument:
            return HOST_APP.doc.ProjectInformation.Name
        else:
            return ''

    @property
    def location(self):
        return HOST_APP.doc.PathName

    @property
    def filename(self):
        return op.splitext(op.basename(self.location))[0]
