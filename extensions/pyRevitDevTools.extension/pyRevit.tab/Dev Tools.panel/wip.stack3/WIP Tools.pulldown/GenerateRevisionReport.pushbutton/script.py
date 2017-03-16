"""Generates a report of all changes for a specific revision."""

import os.path as op

from scriptutils import this_script
from revitutils import doc, uidoc

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, WorksharingUtils, WorksharingTooltipInfo, ElementId, ViewSheet
from Autodesk.Revit.UI import TaskDialog

# collect data:
revClouds = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_RevisionClouds).WhereElementIsNotElementType()
sheetsnotsorted = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)
allRevs = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Revisions).WhereElementIsNotElementType()

# fixme: cleanup and re-write OOP
# todo: add findDetailNumberAndReferencingSheet() for any clouds that are placed on views
# todo: add findUnderlayViewport() for any cloud that is on a sheet over a viewport.
# todo: ask for revision number to generate report for:
pass

# digging into data:
descSet = set()
noneDescClouds = []
revDict = dict()

for revc in revClouds:
	descString = revc.LookupParameter('Comments').AsString()
	if descString is not None:
		descSet.add(revc.LookupParameter('Comments').AsString())
	else:
		noneDescClouds.append(revc.Id.IntegerValue)

for desc in descSet:
	for revc in revClouds:
		revcDesc = revc.LookupParameter('Comments').AsString()
		if revcDesc is not None and revcDesc == desc:
			if revcDesc not in revDict.keys():
				revDict[revcDesc] = (set(), set(), set())
			rev = doc.GetElement( revc.RevisionId )
			for r in allRevs:
				if revc.RevisionId.IntegerValue == r.Id.IntegerValue:
					revDict[revcDesc][2].add(revc.RevisionId.IntegerValue)
			# for s in sheets:
				# revIds = [x.IntegerValue for x in s.GetAllRevisionIds()]
				# if revc.RevisionId.IntegerValue in revIds:
					# revDict[revcDesc][0].append((s.Id.IntegerValue, s.LookupParameter('Sheet Number').AsString()))
			parent = doc.GetElement(revc.OwnerViewId)
			if isinstance(parent, ViewSheet):
				revDict[revcDesc][0].add((parent.Id.IntegerValue, parent.LookupParameter('Sheet Number').AsString()))
			else: # todo: What if the parent is not a sheet?
				pass
			if doc.IsWorkshared:
				wti = WorksharingUtils.GetWorksharingTooltipInfo(doc, revc.Id)
				revDict[revcDesc][1].add(str(wti.Creator))
				revDict[revcDesc][1].add(str(wti.LastChangedBy))

# printing results and exporting to file:
destDir = op.expandvars('%userprofile%\\desktop')
reportfname = op.join(destDir, 'Revision Report.txt')
revisionline = ''

# with open(reportfname, 'w+') as reportfile:
print('PRINTING REVISIONS GROUPED BY COMMENT:')
print('DESCRIPTION\tREVISION\tDRAWING/SHEET\tREVISED BY\n')
for k,v in revDict.items():
	revisionline = ''
	print('\n' + '-'*100)
	print('REVISION COMMENT:\n{0}'.format(k))
	print('\n\tREVISIONS WITH THIS COMMENTS:')
	revisionline += ('\"' + k + '\"\t')
	for rid in v[2]:
		rev = doc.GetElement(ElementId(rid))
		print('\t\t{0}\tREV#: {1}DATE: {2}TYPE:{3}DESC: {4}'.format( rev.SequenceNumber, str(rev.RevisionNumber).ljust(5), str(rev.RevisionDate).ljust(10), str(rev.NumberType.ToString()).ljust(15), rev.Description))
		revisionline += (rev.RevisionNumber + ', ')
	revisionline = revisionline[:len(revisionline)-2] + '\t'
	print('\n\tREVISED SHEETS:')
	for s in v[0]:
		print('\t\t'+s[1])
		revisionline += (s[1] + ', ')
	revisionline = revisionline[:len(revisionline)-2] + '\t'
	print('\n\tREVISED BY:')
	for b in v[1]:
		print('\t\t'+b)
		revisionline += (b + ', ')
	revisionline = revisionline[:len(revisionline)-2] + '\n'
	print(revisionline)

print('\n\n' + '-'*100 + '\n' + '-'*100)
print('REVISION CLOUDS WITH NO COMMENT:\n')
for rid in noneDescClouds:
	revc = doc.GetElement(ElementId(rid))
	parent = doc.GetElement(revc.OwnerViewId)
	if doc.IsWorkshared:
		wti = WorksharingUtils.GetWorksharingTooltipInfo(doc, revc.Id)
	print('REV#: {0}\t\tID: {3}\t\tON SHEET: {1} {2}'.format( doc.GetElement( revc.RevisionId ).RevisionNumber, parent.SheetNumber, parent.Name, revc.Id ))
	print('\tCREATED BY:\t{0}\n\tLAST EDITED BY:\t{1}\n'.format(wti.Creator, wti.LastChangedBy))


# todo: look into exporting excel file maybe? http://www.ironpython.info/index.php?title=Interacting_with_Excel
# import clr
# clr.AddReferenceByName('Microsoft.Office.Interop.Excel')
# from Microsoft.Office.Interop import Excel
