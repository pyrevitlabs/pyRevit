"""
List Elements of selected Level(s)
Lists all Elements of the selected level(s).

Copyright (c) 2017 Frederic Beaupere
github.com/frederic-beaupere

--------------------------------------------------------
PyRevit Notice:
Copyright (c) 2014-2017 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit

"""

__title__ = 'List Elements of selected Level(s)'
__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = """Lists all Elements of the selected level(s)."""

import clr
clr.AddReference("RevitAPI")
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector as Fec
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog
from revitutils import doc
from revitutils import uidoc
from collections import defaultdict

all_elements = Fec(doc).WhereElementIsNotElementType().ToElements()
all_count = all_elements.Count
selection = [doc.GetElement(elId) for elId in uidoc.Selection.GetElementIds()]

def filter_levels(elements):
    levels = []
    for element in elements:
        if element.Category.Name == "Levels":
            levels.append(element)
    return levels

if filter_levels(selection):
    for element in filter_levels(selection):
        element_categories = defaultdict(list)
        level = element
        counter = 0
        
        print("\n" + 5 * "_" + level.Name + ":")
        
        for elem in all_elements:
            if elem.LevelId == level.Id:
                counter += 1
                element_categories[elem.Category.Name].append(elem)
        
        for category in element_categories:
            print("|" + 9 * "_" + category + ": " + str(len(element_categories[category])))
            for elem_cat in element_categories[category]:
                print("| id: " + elem_cat.Id.ToString())

        print("|" + 5 * "_" + str(len(element_categories)) + " Categories found in " + level.Name + ":")
        
        for cat in element_categories:
            print("| " + str(cat) + ": " + str(len(element_categories[cat])))

        print("|" + 5 * "_" + level.Name + ": " + str(counter) + " Elements found.")
        
else:
    __window__.Close()
    TaskDialog.Show('pyRevit', 'No level found in selection.')
    
print("\n" + str(all_count) + " Elements found in project.")
