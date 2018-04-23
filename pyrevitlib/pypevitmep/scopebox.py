# coding: utf8

import rpw
from rpw import DB
from rpw.db import Element


class ScopeBox(Element):
    """ VolumeOfInterest wrapper commonly called ScopeBox
        Inherits from rpw.db.Element
        >>> from rpw.db import ScopeBox

        Example to return a dictionary of fluids in use with system as key
        >>> FluidType.in_use_dict() # return format: {system.name:{'name':fluid.name, 'temperature':temperature}
        {'Hydronic Return': {'name': 'Water', 'temperature': 283.15000000000003}, ...}

        FluidType wrapper is collectible:
        >>> FluidType.collect()
        <rpw:Collector % FilteredElementCollector [count:19]>
        """
    _revit_object_category = DB.BuiltInCategory.OST_VolumeOfInterest
    _collector_params = {'of_category': _revit_object_category, 'is_type': False}

    def __repr__(self, data=None):
        """ Adds data to Base __repr__ to add Parameter List Name """
        if not data:
            data = {}
        data['name'] = self.name
        return super(ScopeBox, self).__repr__(data=data)

    @property
    def bounding_box(self):
        return self.get_BoundingBox(rpw.doc.ActiveView)

    @bounding_box.setter
    def bounding_box(self, value):
        return self.set_BoundingBox(rpw.doc.ActiveView)

    def min(self):
        return self.bo




