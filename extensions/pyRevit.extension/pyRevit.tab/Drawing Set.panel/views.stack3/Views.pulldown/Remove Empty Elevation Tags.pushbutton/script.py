"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ = 'Genrally if all elevations creates by an elevation tag are deleted from the model, the empty ' \
          'elevation tag still remains in its location. This script will delete all empty elevation ' \
          'tags from the model.'

from Autodesk.Revit.DB import View, FilteredElementCollector, Transaction, ElevationMarker, Element

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


def removeallemptyelevationmarkers():
    t = Transaction(doc, 'Remove All Elevation Markers')
    t.Start()
    print('---------------------------- REMOVING ELEVATION MARKERS --------------------------------\n')
    elevmarkers = FilteredElementCollector(doc).OfClass(ElevationMarker).WhereElementIsNotElementType().ToElements()
    for em in elevmarkers:
        if em.CurrentViewCount == 0:
            emtype = doc.GetElement(em.GetTypeId())
            print('ID: {0}\tELEVATION TYPE: {1}'.format(em.Id, Element.Name.GetValue(emtype)))
            try:
                doc.Delete(em.Id)
            except Exception as e:
                print('Elevation Marker', em.Id, e)
                continue
    t.Commit()


removeallemptyelevationmarkers()
