"""Calculated plenum space between selected ceiling and floor or roof above."""

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

from System import Math


logger = script.get_logger()
output = script.get_output()



list = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_Levels).WhereElementIsNotElementType()

levels = {}
bottomOfRoof = 0
bottomOfFloor = 0
bottomOfRatedLid = 0
totalCeilValue = 0

# sort elements by level+offset
for el in revit.get_selection():
	if isinstance(el, DB.FootPrintRoof):
		offset = el.Parameter[DB.BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM].AsDouble()
		levelElev = revit.doc.GetElement(el.LevelId).Elevation
		elev = levelElev + offset
		levels[elev] = el.Id.IntegerValue
	elif isinstance(el, DB.Floor) or isinstance(el, DB.Ceiling):
		if isinstance(el, DB.Ceiling):
			param_type = DB.BuiltInParameter.CEILING_HEIGHTABOVELEVEL_PARAM
		elif isinstance(el, DB.Floor):
			param_type = DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM
		offset = el.Parameter[param_type].AsDouble()
		levelElev = revit.doc.GetElement(el.LevelId).Elevation
		elev = levelElev + offset
		levels[elev] = el.Id.IntegerValue

# get element thinknesses and update the elevs
for elev in sorted(levels.keys()):
	elid = levels[elev]
	el = revit.doc.GetElement(DB.ElementId(elid))
	if isinstance(el, DB.FootPrintRoof):
		# roofType = revit.doc.GetElement(el.GetTypeId())
		# cs = roofType.GetCompoundStructure()
		# roofThickness = cs.GetWidth()
		bottomOfRoof = elev
	if isinstance(el, DB.Floor):
		floorType = revit.doc.GetElement(el.GetTypeId())
		cs = floorType.GetCompoundStructure()
		floorThickness = cs.GetWidth()
		bottomOfFloor = elev - floorThickness
	elif isinstance(el, DB.Ceiling) and totalCeilValue == 0:
		ceilType = revit.doc.GetElement(el.GetTypeId())
		cs = ceilType.GetCompoundStructure()
		ceilThickness = cs.GetWidth()
		totalCeilValue = elev + ceilThickness
	elif isinstance(el, DB.Ceiling):
		bottomOfRatedLid = elev

unts = revit.doc.GetUnits()
fo = FormatOptions()
fo.UseDefault = False
fo.DisplayUnits = DB.DisplayUnitType.DUT_FRACTIONAL_INCHES 
fo.Accuracy = 0.5
unts.SetFormatOptions(DB.UnitType.UT_Length, fo)

if bottomOfRoof > 0:
	result = DB.UnitFormatUtils.Format(unts, DB.UnitType.UT_Length, bottomOfRoof - totalCeilValue, False, False)
	forms.alert('pyRevit', 'DB.Ceiling/Roof plenum space depth is:\n{0}'.format(result))
elif bottomOfFloor > 0:
	result = DB.UnitFormatUtils.Format(unts, DB.UnitType.UT_Length, bottomOfFloor - totalCeilValue, False, False)
	forms.alert('pyRevit', 'DB.Floor/Roof plenum space depth is:\n{0}'.format(result))
elif bottomOfRatedLid > 0:
	result = DB.UnitFormatUtils.Format(unts, DB.UnitType.UT_Length, abs(bottomOfRatedLid - totalCeilValue), False, False)
	forms.alert('pyRevit', 'DB.Floor/Roof plenum space depth is:\n{0}'.format(result))
# DB.UnitUtils.ConvertFromInternalUnits(cs.GetWidth(), DB.DisplayUnitType.DUT_DECIMAL_INCHES)