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

__doc__ = 'pick the source object that has the element graphics override you like to match to, and then pick the destination objects one by one and this tool will match the graphics.'

from pyrevit.userconfig import user_config

from Autodesk.Revit.DB import Transaction, OverrideGraphicSettings
from Autodesk.Revit.UI.Selection import ObjectType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
curview = doc.ActiveView

verbose = True

sel = []

# fixme: modify to remember source style
try:
    sourceElement = doc.GetElement(uidoc.Selection.PickObject(ObjectType.Element, 'Pick source object.'))
    fromStyle = curview.GetElementOverrides(sourceElement.Id)

    sourceStyle = OverrideGraphicSettings()

    if user_config.matchpropoptions.halftone:
        sourceStyle.SetHalftone(fromStyle.Halftone)

    if user_config.matchpropoptions.transparency:
        sourceStyle.SetSurfaceTransparency(fromStyle.Transparency)

    if user_config.matchpropoptions.proj_line_color:
        sourceStyle.SetProjectionLineColor(fromStyle.ProjectionLineColor)

    if user_config.matchpropoptions.proj_line_pattern:
        sourceStyle.SetProjectionLinePatternId(fromStyle.ProjectionLinePatternId)

    if user_config.matchpropoptions.proj_line_weight:
        sourceStyle.SetProjectionLineWeight(fromStyle.ProjectionLineWeight)

    if user_config.matchpropoptions.proj_fill_color:
        sourceStyle.SetProjectionFillColor(fromStyle.ProjectionFillColor)

    if user_config.matchpropoptions.proj_fill_pattern:
        sourceStyle.SetProjectionFillPatternId(fromStyle.ProjectionFillPatternId)

    if user_config.matchpropoptions.proj_fill_pattern_visibility:
        sourceStyle.SetProjectionFillPatternVisible(fromStyle.IsProjectionFillPatternVisible)

    if user_config.matchpropoptions.cut_line_color:
        sourceStyle.SetCutLineColor(fromStyle.CutLineColor)

    if user_config.matchpropoptions.cut_line_pattern:
        sourceStyle.SetCutLinePatternId(fromStyle.CutLinePatternId)

    if user_config.matchpropoptions.cut_line_weight:
        sourceStyle.SetCutLineWeight(fromStyle.CutLineWeight)

    if user_config.matchpropoptions.cut_fill_color:
        sourceStyle.SetCutFillColor(fromStyle.CutFillColor)

    if user_config.matchpropoptions.cut_fill_pattern:
        sourceStyle.SetCutFillPatternId(fromStyle.CutFillPatternId)

    if user_config.matchpropoptions.cut_fill_pattern_visibility:
        sourceStyle.SetCutFillPatternVisible(fromStyle.IsCutFillPatternVisible)

    while True:
        try:
            destElement = doc.GetElement(
                uidoc.Selection.PickObject(ObjectType.Element, 'Pick objects to change their graphic overrides.'))
            curview = doc.ActiveView

            with Transaction(doc, 'Match Graphics Overrides') as t:
                t.Start()
                curview.SetElementOverrides(destElement.Id, sourceStyle)
                t.Commit()
        except:
            break

except:
    pass
