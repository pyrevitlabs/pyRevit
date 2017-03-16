"""Generates a report from all revisions in current project."""

from scriptutils import this_script
from revitutils import doc, uidoc

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, WorksharingUtils, WorksharingTooltipInfo, \
							  ElementId, ViewSheet
from Autodesk.Revit.UI import TaskDialog

# collect data:
revClouds = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_RevisionClouds).WhereElementIsNotElementType()
sheetsnotsorted = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)
all_revisions = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Revisions).WhereElementIsNotElementType()


console = this_script.output
report_title = 'Revision Report'
report_date = '2017-03-18'
report_project = 'This project'


# setup element styling ------------------------------------------------------------------------------------------------
console.add_style('table { border-collapse: collapse; width:100% }' \
                  'table, th, td { border-bottom: 1px solid #aaa; padding: 5px;}' \
                  'th { background-color: #545454; color: white; }' \
                  'tr:nth-child(odd) {background-color: #f2f2f2}')


# Print Title and Report Info ------------------------------------------------------------------------------------------
console.print_md('## {}'.format(report_title))
print('Project Name: {project}\nDate: {date}'.format(project=report_project, date=report_date))
console.insert_divider()

# Print information about all existing revisions -----------------------------------------------------------------------
console.print_md('### List of Revisions')
# prepare markdown code for the revision table
rev_table_header = "| Number        | Date           | Description  |\n" \
                   "|:-------------:|:--------------:|:-------------|\n"
rev_table_template = "|{number}|{date}|{desc}|\n"
rev_table = rev_table_header
for rev in all_revisions:
    rev_table += rev_table_template.format(number=rev.RevisionNumber,
                                           date=rev.RevisionDate,
                                           desc=rev.Description)

# print revision table
console.print_md(rev_table)

# console.save_contents(r'H:\report.html')
