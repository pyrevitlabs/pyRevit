'''
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
'''

__doc__ = 'Calculated plenum space between selected ceiling and floor or roof above.'

__window__.Close()
from Autodesk.Revit.DB import UnitUtils, UnitFormatUtils, UnitType, DisplayUnitType, FilteredElementCollector, BuiltInCategory, FormatOptions, RoundingMethod, UnitSymbolType
from Autodesk.Revit.DB import FootPrintRoof, Ceiling, Floor, ElementId
from Autodesk.Revit.UI import TaskDialog
from System import Math

doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

list = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Levels).WhereElementIsNotElementType()

levels = dict()
bottomOfRoof = 0
bottomOfFloor = 0
bottomOfRatedLid = 0
totalCeilValue = 0

# sort elements by level+offset
for el in selection:
	if isinstance(el, FootPrintRoof):
		offset = el.LookupParameter('Base Offset From Level').AsDouble()
		levelElev = doc.GetElement(el.LevelId).Elevation
		elev = levelElev + offset
		levels[elev] = el.Id.IntegerValue
	elif isinstance(el, Floor) or isinstance(el, Ceiling):
		offset = el.LookupParameter('Height Offset From Level').AsDouble()
		levelElev = doc.GetElement(el.LevelId).Elevation
		elev = levelElev + offset
		levels[elev] = el.Id.IntegerValue

# get element thinknesses and update the elevs
for elev in sorted(levels.keys()):
	elid = levels[elev]
	el = doc.GetElement(ElementId(elid))
	if isinstance(el, FootPrintRoof):
		# roofType = doc.GetElement(el.GetTypeId())
		# cs = roofType.GetCompoundStructure()
		# roofThickness = cs.GetWidth()
		bottomOfRoof = elev
	if isinstance(el, Floor):
		floorType = doc.GetElement(el.GetTypeId())
		cs = floorType.GetCompoundStructure()
		floorThickness = cs.GetWidth()
		bottomOfFloor = elev - floorThickness
	elif isinstance(el, Ceiling) and totalCeilValue == 0:
		ceilType = doc.GetElement(el.GetTypeId())
		cs = ceilType.GetCompoundStructure()
		ceilThickness = cs.GetWidth()
		totalCeilValue = elev + ceilThickness
	elif isinstance(el, Ceiling):
		bottomOfRatedLid = elev

unts = doc.GetUnits()
fo = FormatOptions()
fo.UseDefault = False
fo.DisplayUnits = DisplayUnitType.DUT_FRACTIONAL_INCHES 
fo.Accuracy = 0.5
unts.SetFormatOptions(UnitType.UT_Length, fo)

if bottomOfRoof > 0:
	result = UnitFormatUtils.Format(unts, UnitType.UT_Length, bottomOfRoof - totalCeilValue, False, False)
	TaskDialog.Show('pyRevit', 'Ceiling/Roof plenum space depth is:\n{0}'.format(result))
elif bottomOfFloor > 0:
	result = UnitFormatUtils.Format(unts, UnitType.UT_Length, bottomOfFloor - totalCeilValue, False, False)
	TaskDialog.Show('pyRevit', 'Floor/Roof plenum space depth is:\n{0}'.format(result))
elif bottomOfRatedLid > 0:
	result = UnitFormatUtils.Format(unts, UnitType.UT_Length, abs(bottomOfRatedLid - totalCeilValue), False, False)
	TaskDialog.Show('pyRevit', 'Floor/Roof plenum space depth is:\n{0}'.format(result))
# UnitUtils.ConvertFromInternalUnits(cs.GetWidth(), DisplayUnitType.DUT_DECIMAL_INCHES)