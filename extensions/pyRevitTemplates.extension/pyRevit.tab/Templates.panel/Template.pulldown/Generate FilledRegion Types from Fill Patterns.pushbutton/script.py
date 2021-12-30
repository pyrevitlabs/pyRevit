"""Generate FilledRegion Swatches"""
#pylint: disable=E0401,C0103
# -*- coding: utf-8 -*-
from pyrevit import revit, DB


fillpats = revit.query.get_types_by_class(DB.FillPatternElement)
with revit.Transaction('Generate FilledRegion Types'):
    for fillpat in fillpats:
        try:
            filledregion_type = \
                revit.create.create_filledregion(fillpat.Name, fillpat)
            filledregion_type.ForegroundPatternColor = DB.Color(128, 128, 128)
            filledregion_type.LineWeight = 1
            filledregion_type.IsMasking = True
        except: 
            pass
