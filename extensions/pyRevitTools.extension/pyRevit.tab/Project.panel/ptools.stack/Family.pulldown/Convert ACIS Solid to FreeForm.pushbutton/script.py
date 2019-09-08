# -*- coding: utf-8 -*-
"""Convert ACIS Solid to FreeForm Element.

creates FreeForm elements from your selected imported acis SAT
solid geometry, so you can turn it into Void/Solid apply materials
easily and get access to its shape handles.

Copyright (c) 2019 Frederic Beaupere
github.com/hdm-dt-fb
"""

from pyrevit.framework import Stopwatch
from pyrevit import forms
from pyrevit import revit, DB


def verify_selection(selected_elems, doc):
    if doc.IsFamilyDocument:
        if len(selected_elems) == 1 \
                and selected_elems[0].GetType() is DB.DirectShape:
            return True
        else:
            forms.alert('More than one element is selected or selected '
                        'element is not an ACIS Solid.', exitscript=True)
    else:
        forms.alert('Please select one imported ACIS SAT DirectShape '
                    'while in Family Editor.', exitscript=True)
    return False


stopwatch = Stopwatch()
selection = revit.get_selection()

if verify_selection(selection, revit.doc):
    stopwatch.Start()
    sat_import = selection.first
    geo_elem = sat_import.get_Geometry(DB.Options())
    solids = []
    for geo in geo_elem:
        if isinstance(geo, DB.Solid):
            if geo.Volume > 0.0:
                solids.append(geo)
    # create freeform from solids
    with revit.Transaction("Convert ACIS to FreeFrom"):
        for solid in solids:
            DB.FreeFormElement.Create(revit.doc, solid)

print("Conversion completed in: {}".format(stopwatch.Elapsed))
