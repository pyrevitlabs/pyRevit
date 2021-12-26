import os.path as op

from pyrevit import HOST_APP, PyRevitException
from pyrevit.compat import safe_strtype
from pyrevit import coreutils
from pyrevit import DB
from Autodesk.Revit.DB import Element   #pylint: disable=E0401


#pylint: disable=W0703,C0302,C0103
__all__ = ('BaseWrapper', 'ElementWrapper',
           'ExternalRef', 'ProjectParameter', 'ProjectInfo',
           'XYZPoint')


class BaseWrapper(object):
    def __init__(self, obj=None):
        self._wrapped = obj

    def __repr__(self, data=None):
        pdata = {}
        if hasattr(self._wrapped, 'Id'):
            pdata['id'] = self._wrapped.Id.IntegerValue

        if data:
            pdata.update(data)

        datastr = ' '.join(['{0}:{1}'.format(k, v)
                            for k, v in pdata.iteritems()]) #pylint: disable=E1101
        return '<pyrevit.revit.db.{class_name} % {wrapping}{datastr}>' \
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
        symbol = getattr(self._wrapped, 'Symbol', None)
        if symbol:
            return Element.Name.GetValue(symbol)

    @property
    def family_name(self):
        symbol = getattr(self._wrapped, 'Symbol', None)
        if symbol:
            return Element.Name.GetValue(symbol.Family)

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
        mparam = self._wrapped.Parameter[DB.BuiltInParameter.ALL_MODEL_MARK]
        return mparam.AsString() if mparam else ''

    @property
    def location(self):
        locp = getattr(self._wrapped.Location, 'Point', None)
        if locp:
            return (locp.X, locp.Y, locp.Z)
        return (None, None, None)

    @property
    def x(self):
        return self.location[0]

    @property
    def y(self):
        return self.location[1]

    @property
    def z(self):
        return self.location[2]

    def get_param(self, param_name):
        return self._wrapped.LookupParameter(param_name)

    def safe_get_param(self, param_name, default=None):
        try:
            return self._wrapped.LookupParameter(param_name)
        except Exception:
            return default


class ExternalRef(ElementWrapper):
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


class ProjectParameter(BaseWrapper):
    def __init__(self, param_def, param_binding=None, param_ext_def=False):
        super(ProjectParameter, self).__init__()
        self.param_def = param_def
        self.param_binding = param_binding
        self.param_binding_type = self._determine_binding_type()

        self.shared = False
        self.param_ext_def = None
        self.param_guid = ''
        if param_ext_def:
            self.shared = True
            self.param_ext_def = param_ext_def
            self.param_guid = self.param_ext_def.GUID.ToString()

        self.name = self.param_def.Name

        # Revit <2017 does not have the Id parameter
        self.param_id = getattr(self.param_def, 'Id', None)

        # Revit >2021 does not have the UnitType property
        if HOST_APP.is_newer_than(2021, or_equal=True):
            self.unit_type = self.param_def.GetSpecTypeId()
        else:
            self.unit_type = self.param_def.UnitType

        # Revit >2022 does not have the ParameterType property
        if HOST_APP.is_newer_than(2022, or_equal=True):
            self.param_type = self.param_def.GetDataType()
        else:
            self.param_type = self.param_def.ParameterType

        self.param_group = self.param_def.ParameterGroup

    def __eq__(self, other):
        if isinstance(self.param_def, DB.ExternalDefinition):
            return self.param_def.GUID == other.GUID or self.name == other.Name
        else:
            guid = coreutils.extract_guid(str(other))
            if guid:
                return self.param_def.GUID.ToString() == guid
            else:
                return self.name == str(other)

    def _determine_binding_type(self):
        if isinstance(self.param_binding, DB.InstanceBinding):
            return 'Instance'
        elif isinstance(self.param_binding, DB.TypeBinding):
            return 'Type'


class ProjectInfo(BaseWrapper):
    def __init__(self, doc):
        super(ProjectInfo, self).__init__()
        self._doc = doc

    @property
    def name(self):
        if not self._doc.IsFamilyDocument:
            return self._doc.ProjectInformation.Name
        else:
            return ''

    @property
    def number(self):
        if not self._doc.IsFamilyDocument:
            return self._doc.ProjectInformation.Number
        else:
            return ''

    @property
    def address(self):
        if not self._doc.IsFamilyDocument:
            return self._doc.ProjectInformation.Address
        else:
            return ''

    @property
    def author(self):
        if not self._doc.IsFamilyDocument:
            return self._doc.ProjectInformation.Author
        else:
            return ''

    @property
    def building_name(self):
        if not self._doc.IsFamilyDocument:
            return self._doc.ProjectInformation.BuildingName
        else:
            return ''

    @property
    def client_name(self):
        if not self._doc.IsFamilyDocument:
            return self._doc.ProjectInformation.ClientName
        else:
            return ''

    @property
    def issue_date(self):
        if not self._doc.IsFamilyDocument:
            return self._doc.ProjectInformation.IssueDate
        else:
            return ''

    @property
    def org_name(self):
        if not self._doc.IsFamilyDocument:
            return self._doc.ProjectInformation.OrganizationName
        else:
            return ''

    @property
    def org_desc(self):
        if not self._doc.IsFamilyDocument:
            return self._doc.ProjectInformation.OrganizationDescription
        else:
            return ''

    @property
    def status(self):
        if not self._doc.IsFamilyDocument:
            return self._doc.ProjectInformation.Status
        else:
            return ''

    @property
    def location(self):
        return op.dirname(self._doc.PathName)

    @property
    def path(self):
        return self._doc.PathName

    @property
    def filename(self):
        return op.splitext(op.basename(self.path))[0]


class XYZPoint(BaseWrapper):
    @property
    def x(self):
        return round(self._wrapped.X)

    @property
    def y(self):
        return round(self._wrapped.Y)

    @property
    def z(self):
        return round(self._wrapped.Z)

    def __repr__(self): #pylint: disable=W0222
        return super(XYZPoint, self).__repr__({'X': self.x,
                                               'Y': self.y,
                                               'Z': self.z})

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def __eq__(self, other):
        if isinstance(other, DB.XYZ):
            return self._wrapped.X == other.X \
                    and self._wrapped.Y == other.Y \
                    and self._wrapped.Z == other.Z
        elif isinstance(other, XYZPoint):
            return self.x == other.x \
                    and self.y == other.y \
                    and self.z == other.z
        return False
