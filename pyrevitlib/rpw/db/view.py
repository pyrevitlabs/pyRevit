"""
View Wrappers

"""  #

import rpw
from rpw import revit, DB
from rpw.db.element import Element
from rpw.db.collector import Collector
from rpw.base import BaseObjectWrapper
from rpw.utils.logger import logger
from rpw.utils.dotnet import Enum
from rpw.db.builtins import BipEnum


class View(Element):
    """
    This is the master View Class. All other View classes inherit
    from DB.View

    This is also used for some Types: Legend, ProjectBrowser, SystemBrowser
    """

    _revit_object_category = DB.BuiltInCategory.OST_Views
    _revit_object_class = DB.View
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}

    @property
    def name(self):
        # TODO: Make Mixin ?
        return self._revit_object.Name

    @name.setter
    def name(self, value):
        self._revit_object.Name == value

    @property
    def view_type(self):
        return ViewType(self._revit_object.ViewType)

    @property
    def view_family_type(self):
        # NOTE: This can return Empty, as Some Views like SystemBrowser have no Type
        view_type_id = self._revit_object.GetTypeId()
        view_type = self.doc.GetElement(view_type_id)
        if view_type:
            return ViewFamilyType(self.doc.GetElement(view_type_id))

    @property
    def view_family(self):
        # Some Views don't have a ViewFamilyType
        return getattr(self.view_family_type, 'view_family', None)

    @property
    def siblings(self):
        return self.view_type.views

    def __repr__(self):
        return super(View, self).__repr__(data={'view_name': self.name,
                                                'view_family_type': getattr(self.view_family_type, 'name', None),
                                                'view_type': self.view_type.name,
                                                'view_family': getattr(self.view_family, 'name', None)
                                                })


# ViewPlanType
class ViewPlan(View):
    _revit_object_class = DB.ViewPlan
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}

    @property
    def level(self):
        return self._revit_object.GenLevel


class ViewSheet(View):
    """ View where ``ViewType`` is ViewType.DrawingSheet """
    _revit_object_class = DB.ViewSheet
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}


class ViewSchedule(View):
    """ View where ``ViewType`` is ViewType.DrawingSheet """
    _revit_object_class = DB.ViewSchedule
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}


class ViewSection(View):
    """ View where ``ViewType`` is ViewType.DrawingSheet """
    _revit_object_class = DB.ViewSection
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}


class ViewSchedule(View):
    _revit_object_class = DB.ViewSchedule
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}

class View3D(View):
    _revit_object_class = DB.View3D
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}


class ViewFamilyType(Element):
    """ View Family Type Wrapper """
    _revit_object_class = DB.ViewFamilyType
    _collector_params = {'of_class': _revit_object_class, 'is_type': True}

    @property
    def name(self):
        # Could use the line below but would required re-importing element, as per
        # return DB.Element.Name.GetValue(self._revit_object)
        return self.parameters.builtins['SYMBOL_FAMILY_NAME_PARAM'].value

    @property
    def view_family(self):
        """ Returns ViewFamily Enumerator """
        # Autodesk.Revit.DB.ViewFamily.FloorPlan
        return ViewFamily(self._revit_object.ViewFamily)

    @property
    def views(self):
        # Collect All Views, Compare view_family of each view with self
        views = Collector(of_class='View').wrapped_elements
        return [view for view in views if getattr(view.view_family_type, '_revit_object', None) == self.unwrap()]



    def __repr__(self):
        return super(ViewFamilyType, self).__repr__(data={'name': self.name,
                                                          'view_family': self.view_family.name,
                                                          })

class ViewFamily(BaseObjectWrapper):
    """ ViewFamily Enumerator Wrapper.
    An enumerated type that corresponds to the type of a Revit view.

    This is returned on view.ViewFamily
    AreaPlan, CeilingPlan, CostReport
    Detail, Drafting, Elevation
    FloorPlan, GraphicalColumnSchedule, ImageView, Legend
    LoadsReport, PanelSchedule, PressureLossReport
    Schedule, Section, Sheet, StructuralPlan
    ThreeDimensional, Walkthrough
    """
    _revit_object_class = DB.ViewFamily

    @property
    def name(self):
        return self._revit_object.ToString()

    @property
    def views(self):
        # Collect All Views, Compare view_family of each view with self
        views = Collector(of_class='View').wrapped_elements
        return [view for view in views if getattr(view.view_family, '_revit_object', None) == self.unwrap()]


    def __repr__(self):
        return super(ViewFamily, self).__repr__(data={'family': self.name})



class ViewType(BaseObjectWrapper):
    """ ViewType Wrapper.
    An enumerated type listing available view types.

    Can be on of the following types:
        AreaPlan ,CeilingPlan, ColumnSchedule, CostReport,
        Detail, DraftingView, DrawingSheet, Elevation, EngineeringPlan,
        FloorPlan, Internal, Legend,
        LoadsReport, PanelSchedule, PresureLossReport,
        ProjectBrowser, Rendering, Report,
        Schedule, Section, SystemBrowser,
        ThreeD, Undefined, Walkthrough
    """
    _revit_object_class = DB.ViewType

    @property
    def name(self):
        return self._revit_object.ToString()

    @property
    def views(self):
        views = Collector(of_class='View').wrapped_elements
        return [view for view in views if view.view_type.unwrap() == self.unwrap()]


    def __repr__(self):
        return super(ViewType, self).__repr__(data={'view_type': self.name})



class ViewPlanType(BaseObjectWrapper):
    """
    Enumerator
        FloorPlan, CeilingPlan
    No Wrapper Need. Only a Enum that is used as arg for ViewPlan
    """
