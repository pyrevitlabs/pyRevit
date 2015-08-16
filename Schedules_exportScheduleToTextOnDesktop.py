from Autodesk.Revit.DB import ViewSchedule, ViewScheduleExportOptions, ExportColumnHeaders, ExportTextQualifier
import os
import os.path as op

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

desktop = op.expandvars('%userprofile%\\desktop')

vseop = ViewScheduleExportOptions()
# vseop.ColumnHeaders = ExportColumnHeaders.None
# vseop.TextQualifier = ExportTextQualifier.None
# vseop.FieldDelimiter = ','
# vseop.Title = False

for el in uidoc.Selection.Elements:
	fname = "".join(x for x in el.ViewName if x not in ['*']) + '.txt'
	el.Export( desktop, fname , vseop )
	print('EXPORTED: {0}\n      TO: {1}\n'.format( el.ViewName, fname))