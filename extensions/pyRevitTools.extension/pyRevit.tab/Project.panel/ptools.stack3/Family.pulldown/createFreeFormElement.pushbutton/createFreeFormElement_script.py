# -*- coding: utf-8 -*-
"""create Free Form Element.

creates FreeForm elements from your selected imported acis SAT
solid geometry, so you can turn it into Void/Solid apply materials
easily and get access to its shape handles.

Copyright (c) 2017 Frederic Beaupere
github.com/hdm-dt-fb

--------------------------------------------------------
PyRevit Notice:
Copyright (c) 2014-2017 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit
"""

import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import Options, FreeFormElement
from System.Diagnostics import Stopwatch
from rpw import db, doc, uidoc


def correct_selection(selected_elems):
    if doc.IsFamilyDocument:
        if len(selected_elems) == 1:
            if selected_elems[0].GetType().ToString() == 'Autodesk.Revit.DB.DirectShape':
                print("Single ACIS SAT DirectShape selected.")
                return True
    print("Please select one imported acis SAT DirectShape in FamilyEditor")
    return False


stopwatch = Stopwatch()
stopwatch.Start()
selection = [doc.GetElement(elId) for elId in uidoc.Selection.GetElementIds()]

if correct_selection(selection):
    sat_import = selection[0]
    geo_elem = sat_import.get_Geometry(Options())
    solids = []

    for geo in geo_elem:
        if geo.ToString() == 'Autodesk.Revit.DB.Solid':
            if geo.Volume > 0.0:
                solids.append(geo)

    with db.Transaction("generate_freeform_geo"):
        for solid in solids:
            FreeFormElement.Create(doc, solid)

print("pyRevit createFreeFormElement run in: ")
stopwatch.Stop()
timespan = stopwatch.Elapsed
print(timespan)
