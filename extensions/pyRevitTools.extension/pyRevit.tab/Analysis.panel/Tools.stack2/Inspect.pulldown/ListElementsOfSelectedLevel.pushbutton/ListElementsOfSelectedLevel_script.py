# -*- coding: utf-8 -*-
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

__title__ = 'List Elements of Selected Level(s)'
__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = 'Lists all Elements of the selected level(s).'

import clr
from collections import defaultdict

from scriptutils import this_script
from revitutils import doc, uidoc

clr.AddReference('RevitAPI')
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector as Fec
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog


this_script.output.print_md("####LIST ALL ELEMENTS ON SELECTED LEVEL(S):")
this_script.output.print_md('By: [{}]({})'.format(__author__, __contact__))


all_elements = Fec(doc).WhereElementIsNotElementType().ToElements()
selection = [doc.GetElement(elId) for elId in uidoc.Selection.GetElementIds()]

levels = []
for el in selection:
    if el.Category.Name == 'Levels':
        levels.append(el)

if not levels:
    TaskDialog.Show('pyRevit', 'At least one Level element must be selected.')
else:
    all_count = all_elements.Count
    print('\n' + str(all_count) + ' Elements found in project.')

    for element in levels:
        element_categories = defaultdict(list)
        level = element
        counter = 0

        print('\n' + '╞═════════■ {}:'.format(level.Name))

        for elem in all_elements:
            if elem.LevelId == level.Id:
                counter += 1
                element_categories[elem.Category.Name].append(elem)

        for category in element_categories:
            print('├──────────□ {}: {}'.format(category,
                                              str(len(element_categories[category]))))

            for elem_cat in element_categories[category]:
                print('├ id: ' + elem_cat.Id.ToString())

        print('├────────── {} Categories found in {}:'.format(str(len(element_categories)),
                                                         level.Name))

        for cat in element_categories:
            print('│ {}: {}'.format(str(cat),
                                    str(len(element_categories[cat]))))

        print('└────────── {}: {} Elements found.'.format(level.Name,
                                                     str(counter)))
