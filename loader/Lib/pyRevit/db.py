"""
todo add wrapper functions to interact with Revit database in a more user friendly manner.
example:
    import pyRevit.db as db
    db.Doors.select('\d6')     selects all doors with mark 06,16,26,36,46,56,66,76,86,96
"""
import re

from .config import HOST_SOFTWARE
from System.Collections.Generic import List

from Autodesk.Revit.DB import FilteredElementCollector, ElementMulticategoryFilter, BuiltInCategory
from Autodesk.Revit.DB import ElementId


doc = HOST_SOFTWARE.ActiveUIDocument.Document
uidoc = HOST_SOFTWARE.ActiveUIDocument


class GenericFamily(object):
    type_id = ''

    def __init__(self):
        cl = FilteredElementCollector(doc)
        self._current_elements = cl.OfCategory(self.type_id).WhereElementIsNotElementType().ToElements()

    def __iter__(self):
        return iter(self._current_elements)

    def __repr__(self):
        pass

    def create(self):
        pass


class Doors(GenericFamily):
    type_id = BuiltInCategory.OST_Doors

    @classmethod
    def select(cls, door_search_regex):
        current_doors = cls()
        door_id_list = []
        finder = re.compile('(?<![\w\d])'+ door_search_regex +'(?![\w\d])')
        for door in current_doors:
            if finder.search(door.LookupParameter('Mark').AsString()):
                door_id_list.append(door.Id)
        uidoc.Selection.SetElementIds(List[ElementId](door_id_list))
