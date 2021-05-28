# -*- coding: utf-8 -*-
"""Generates a report from all revisions in current project."""
"""tooltip."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import script


# collect sheet
sheetsnotsorted = DB.FilteredElementCollector(revit.doc)\
                    .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                    .WhereElementIsNotElementType()\
                    .ToElements()

all_sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)


# collect all clouds
all_clouds = DB.FilteredElementCollector(revit.doc)\
               .OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
               .WhereElementIsNotElementType()

# collect all revisions
all_revisions = DB.FilteredElementCollector(revit.doc)\
                  .OfCategory(DB.BuiltInCategory.OST_Revisions)\
                  .WhereElementIsNotElementType()


console = script.get_output()
console.set_height(800)
console.lock_size()

report_title = 'Revision Report'
report_date = coreutils.current_date()
report_project = revit.query.get_project_info().name


# setup element styling
console.add_style(
    'table { border-collapse: collapse; width:100% }'
    'table, th, td { border-bottom: 1px solid #aaa; padding: 5px;}'
    'th { background-color: #545454; color: white; }'
    'tr:nth-child(odd) {background-color: #f2f2f2}'
    )


# Print Title and Report Info
console.print_md('# {}'.format(report_title))
print('Project Name: {project}\nDate: {date}'
      .format(project=report_project, date=report_date))
console.insert_divider()

# Print information about all existing revisions
console.print_md('### List of Revisions')
# prepare markdown code for the revision table
rev_table_header = "| Number        | Date           | Description  |\n" \
                   "|:-------------:|:--------------:|:-------------|\n"
rev_table_template = "|{number}|{date}|{desc}|\n"
rev_table = rev_table_header
for rev in all_revisions:
    revnum = revit.query.get_rev_number(rev)
    rev_table += rev_table_template.format(number=revnum,
                                           date=rev.RevisionDate,
                                           desc=rev.Description)

# print revision table
console.print_md(rev_table)


class RevisedSheet:
    def __init__(self, rvt_sheet):
        self._rvt_sheet = rvt_sheet

        self._clouds = []
        self._find_all_clouds()
        self._find_all_revisions()

    def _find_all_clouds(self):
        ownerview_ids = [self._rvt_sheet.Id]
        # add all the sheeted views to list
        ownerview_ids.extend(
            [
                revit.doc.GetElement(x).ViewId
                for x in self._rvt_sheet.GetAllViewports()
            ])
        for rev_cloud in all_clouds:
            if rev_cloud.OwnerViewId in ownerview_ids:
                self._clouds.append(rev_cloud)

    def _find_all_revisions(self):
        self._revisions = set([cloud.RevisionId for cloud in self._clouds])
        self._revisions.update(
            set(self._rvt_sheet.GetAdditionalRevisionIds())
        )
        self._rev_numbers = set(
            [
                revit.query.get_rev_number(revit.doc.GetElement(rev_id))
                for rev_id in self._revisions
            ])

    @property
    def sheet_number(self):
        return self._rvt_sheet.SheetNumber

    @property
    def sheet_name(self):
        return self._rvt_sheet.Name

    @property
    def cloud_count(self):
        return len(self._clouds)

    @property
    def rev_count(self):
        return len(self._revisions)

    def get_clouds(self):
        return self._clouds

    def get_comments(self):
        all_comments = set()
        for cloud in self._clouds:
            cparam = \
                cloud.Parameter[DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS]
            comment = cparam.AsString()
            if not coreutils.is_blank(comment):
                all_comments.add(comment)
        return all_comments

    def get_revision_numbers(self):
        return self._rev_numbers


# create a list of revised sheets
revised_sheets = []
for sheet in all_sheets:
    if sheet.CanBePrinted:
        revised_sheets.append(RevisedSheet(sheet))

# draw a revision chart
chart = console.make_bar_chart()
chart.options.scales = {'type': 'linear',
                        'yAxes': [
                            {
                                # 'stacked': True,
                                'ticks': {'min': 0, 'stepSize': 1}
                            }
                            ],
                        'xAxes': [
                            {
                                'ticks': {'minRotation': 90}
                            }
                            ]}

chart.data.labels = [rs.sheet_number
                     for rs in revised_sheets
                     if rs.rev_count > 0]
chart.set_height(100)

cloudcount_dataset = chart.data.new_dataset('Revision Count')
cloudcount_dataset.set_color('red')
cloudcount_dataset.data = [rs.rev_count
                           for rs in revised_sheets
                           if rs.rev_count > 0]

cloudcount_dataset = chart.data.new_dataset('Revision Cloud Count')
cloudcount_dataset.set_color('black')
cloudcount_dataset.data = [rs.cloud_count
                           for rs in revised_sheets
                           if rs.cloud_count > 0]

chart.draw()

# print info on sheets
for rev_sheet in revised_sheets:
    if rev_sheet.rev_count > 0:
        console.print_md(
            '** Sheet {}: {}**\n\n'
            'Revision Count: {}\n\n'
            'Revision Cloud Count: {}\n\n'
            'Revision Numbers: {}'
            .format(rev_sheet.sheet_number,
                    rev_sheet.sheet_name,
                    rev_sheet.rev_count,
                    rev_sheet.cloud_count,
                    coreutils.join_strings(rev_sheet.get_revision_numbers(),
                                           separator=',')))
        comments = rev_sheet.get_comments()
        if comments:
            print('\t\tRevision comments:\n{}'
                  .format('\n'.join(['\t\t{}'.format(cmt)
                                     for cmt in comments])))

        console.insert_divider()
