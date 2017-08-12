""" Assembly Wrappers """

from rpw import revit, DB
from rpw.db.element import Element

from rpw.utils.coerce import to_elements
from rpw.utils.mixins import ByNameCollectMixin


# TODO: Tests
# TODO: Docs

class AssemblyInstance(Element):
    """
    `DB.AssemblyInstance` Wrapper

    Attribute:
        _revit_object (DB.AssemblyInstance): Wrapped ``DB.AssemblyInstance``
    """

    _revit_object_class = DB.AssemblyInstance
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}

    @property
    def elements(self):
        member_ids = self._revit_object.GetMemberIds()
        elements = to_elements(member_ids, doc=self._revit_object.Document)
        return [Element(e) for e in elements]

    def __repr__(self):
        return Element.__repr__(self, data={'name': self.Name})


class AssemblyType(Element):
    """
    `DB.AssemblyType` Wrapper
    Inherits from :any:`Element`

    Attribute:
        _revit_object (DB.AssemblyType): Wrapped ``DB.AssemblyType``
    """

    _revit_object_class = DB.AssemblyType
    _collector_params = {'of_class': _revit_object_class, 'is_type': True}

    @property
    def siblings(self):
        """ Returns all assembly types """
        return [Element.from_id(t) for t in self._revit_object.GetSimilarTypes()]

    @property
    def instances(self):
        """ Returns all Instances of the assembly type """
        raise NotImplemented
        # bip = BipEnum.get_id('AREA_SCHEME_ID')
        # param_filter = rpw.db.Collector.ParameterFilter(bip, equals=self._revit_object.Id)
        # collector = rpw.db.Collector(parameter_filter=param_filter,
        #                              **Area._collector_params)
        # return collector.wrapped_elements

    @property
    def name(self):
        return self._revit_object.FamilyName

    def __repr__(self):
        return super(AssemblyType, self).__repr__(data={'name': self.name})
