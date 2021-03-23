# -*- coding: utf-8 -*-
"""Convert ACIS Solid to FreeForm Element.

creates FreeForm elements from your selected imported acis SAT
solid geometry, so you can turn it into Void/Solid apply materials
easily and get access to its shape handles.

Copyright (c) 2019 Frederic Beaupere
github.com/hdm-dt-fb
"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit.framework import Stopwatch
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script

logger = script.get_logger()


def verify_selection(selected_elems, doc):
    if doc.IsFamilyDocument:
        if all([isinstance(x, (DB.DirectShape, DB.ImportInstance)) for x in selected_elems]):
            return True
        else:
            forms.alert("More than one element is selected or selected "
                        "element is not an ACIS Solid.", exitscript=True)
    else:
        forms.alert("Please select one imported ACIS SAT DirectShape "
                    "while in Family Editor.", exitscript=True)
    return False


stopwatch = Stopwatch()
selection = revit.get_selection()

if verify_selection(selection, revit.doc):
    stopwatch.Start()
    for sat_import in selection:
        geom_opts = DB.Options()
        geom_opts.IncludeNonVisibleObjects = True
        logger.debug('Converting: %s', sat_import)
        solids = []
        for geo in revit.query.get_geometry(sat_import):
            if isinstance(geo, DB.Solid):
                if geo.Volume > 0.0:
                    solids.append(geo)
        # create freeform from solids
        with revit.Transaction("Convert ACIS to FreeFrom"):
            for solid in solids:
                DB.FreeFormElement.Create(revit.doc, solid)

logger.debug('Conversion completed in: %s', stopwatch.Elapsed)
