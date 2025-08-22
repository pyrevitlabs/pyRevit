# -*- coding: utf-8 -*-
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import script, forms


# collect sheet
sheetsnotsorted = (
    DB.FilteredElementCollector(revit.doc)
    .OfCategory(DB.BuiltInCategory.OST_Sheets)
    .WhereElementIsNotElementType()
    .ToElements()
)

all_sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

# collect all clouds
all_clouds = (
    DB.FilteredElementCollector(revit.doc)
    .OfCategory(DB.BuiltInCategory.OST_RevisionClouds)
    .WhereElementIsNotElementType()
    .ToElements()
)

# collect all revisions
all_revisions = forms.select_revisions(
    title="Select Revisions To Include In The Report"
)
if not all_revisions:
    script.exit()

console = script.get_output()
console.set_height(800)
console.lock_size()

report_title = "Revision Report"
report_date = coreutils.current_date()
report_project = revit.query.get_project_info().name


# setup element styling
console.add_style(
    "table { border-collapse: collapse; width:100% }"
    "table, th, td { border-bottom: 1px solid #aaa; padding: 5px;}"
    "th { background-color: #545454; color: white; }"
    "tr:nth-child(odd) {background-color: #f2f2f2}"
)


# Print Title and Report Info
console.print_md("# {}".format(report_title))
print(
    "Project Name: {project}\nDate: {date}".format(
        project=report_project, date=report_date
    )
)
console.insert_divider()

# Print information about all existing revisions
console.print_md("### List of Revisions")
# prepare markdown code for the revision table
rev_table_header = (
    "| Number        | Date           | Description  |\n"
    "|:-------------:|:--------------:|:-------------|\n"
)
rev_table_template = "|{number}|{date}|{desc}|\n"
rev_table = rev_table_header

# gather revision number, date, and description in tuple list
rev_data = [
    (revit.query.get_rev_number(rev), rev.RevisionDate, rev.Description)
    for rev in all_revisions
]

# sort tuple list by revision number
rev_data.sort(key=lambda rev: rev[0])

# add revision data to the revision table string
for rev in rev_data:
    rev_table += rev_table_template.format(number=rev[0], date=rev[1], desc=rev[2])

# print revision table
console.print_md(rev_table)


class RevisedSheet:
    def __init__(self, rvt_sheet):
        self._rvt_sheet = rvt_sheet

        self._sheet_revisions = self._find_all_revisions_in_sheet()
        self._sheet_clouds = self._find_all_clouds_in_sheet()
        self._rev_numbers = self._find_revision_numbers()

    def _find_all_clouds_in_sheet(self):
        sheet_clouds = []
        ownerview_ids = [self._rvt_sheet.Id]
        # add all the sheeted views to list
        ownerview_ids.extend(
            [revit.doc.GetElement(x).ViewId for x in self._rvt_sheet.GetAllViewports()]
        )

        primary_owenerview_ids = [
            revit.doc.GetElement(view_id).GetPrimaryViewId()
            for view_id in ownerview_ids
            if revit.doc.GetElement(view_id).GetPrimaryViewId()
            != DB.ElementId.InvalidElementId
        ]

        for rev_cloud in all_clouds:
            is_rev_cloud_visible_in_sheet = self._is_revision_cloud_visible_in_sheet(
                rev_cloud
            )
            is_rev_cloud_in_sheet_revisions = (
                rev_cloud.RevisionId in self._sheet_revisions
            )

            if (
                is_rev_cloud_in_sheet_revisions
                and is_rev_cloud_visible_in_sheet
                and (
                    rev_cloud.OwnerViewId in ownerview_ids
                    or rev_cloud.OwnerViewId in primary_owenerview_ids
                )
            ):
                sheet_clouds.append(rev_cloud)
        return sheet_clouds

    def _is_revision_cloud_visible_in_sheet(self, rev_cloud):
        """Check if a revision cloud is visible in the sheet."""
        is_visible = False
        for view_id in self._rvt_sheet.GetAllViewports():
            viewport = revit.doc.GetElement(view_id)
            view = revit.doc.GetElement(viewport.ViewId)
            if not rev_cloud.IsHidden(view):
                is_visible = True
                break
        return is_visible

    def _find_all_revisions_in_sheet(self):
        revisions = set(self._rvt_sheet.GetAllRevisionIds())
        revisions.update(set(self._rvt_sheet.GetAdditionalRevisionIds()))
        return revisions

    def _find_revision_numbers(self):
        rev_numbers = set(
            [
                revit.query.get_rev_number(revit.doc.GetElement(rev_id))
                for rev_id in self._sheet_revisions
            ]
        )
        return rev_numbers

    @property
    def sheet_number(self):
        return self._rvt_sheet.SheetNumber

    @property
    def sheet_name(self):
        return self._rvt_sheet.Name

    @property
    def cloud_count(self):
        return len(self._sheet_clouds)

    @property
    def rev_count(self):
        return len(self._sheet_revisions)

    @property
    def additional_revisions_count(self):
        return len(set(self._rvt_sheet.GetAdditionalRevisionIds()))

    def get_clouds(self):
        return self._sheet_clouds

    def get_comments(self):
        all_comments = set()
        for cloud in self._sheet_clouds:
            cparam = cloud.Parameter[DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS]
            comment = cparam.AsString()
            if not coreutils.is_blank(comment):
                all_comments.add(comment)
        return all_comments

    def get_all_revision_marks(self):
        all_marks = set()
        for cloud in self._sheet_clouds:
            cparam = cloud.Parameter[DB.BuiltInParameter.ALL_MODEL_MARK]
            mark = cparam.AsString()
            if not coreutils.is_blank(mark):
                all_marks.add(mark)
        return all_marks

    def get_revision_numbers(self):
        return self._rev_numbers


# create a list of revised sheets
revised_sheets = []
for sheet in all_sheets:
    if sheet.CanBePrinted:
        revised_sheets.append(RevisedSheet(sheet))

# draw a revision chart
chart = console.make_bar_chart()
chart.options.scales = {
    "type": "linear",
    "yAxes": [
        {
            # 'stacked': True,
            "ticks": {"min": 0, "stepSize": 1}
        }
    ],
    "xAxes": [{"ticks": {"minRotation": 90}}],
}

chart.data.labels = [rs.sheet_number for rs in revised_sheets if rs.rev_count > 0]
chart.set_height(100)

cloudcount_dataset = chart.data.new_dataset("Revision Count")
cloudcount_dataset.set_color("red")
cloudcount_dataset.data = [rs.rev_count for rs in revised_sheets if rs.rev_count > 0]

cloudcount_dataset = chart.data.new_dataset("Revision Cloud Count")
cloudcount_dataset.set_color("black")
cloudcount_dataset.data = [
    rs.cloud_count for rs in revised_sheets if rs.cloud_count > 0
]

chart.draw()

# print info on sheets
for rev_sheet in revised_sheets:
    if rev_sheet.rev_count > 0:
        console.print_md(
            "** Sheet {}: {}**\n\n"
            "Revision Count: {}\n\n"
            "Revision Cloud Count: {}\n\n"
            "Revision Numbers: {}".format(
                rev_sheet.sheet_number,
                rev_sheet.sheet_name,
                rev_sheet.rev_count,
                rev_sheet.cloud_count,
                coreutils.join_strings(rev_sheet.get_revision_numbers(), separator=","),
            )
        )

        if rev_sheet.additional_revisions_count > 0:
            console.print_md(
                "Additional Revisions Count: {} (revisions not associated with a cloud on this sheet)".format(
                    rev_sheet.additional_revisions_count
                )
            )

        comments = rev_sheet.get_comments()
        if comments:
            print(
                "\t\tRevision comments:\n{}".format(
                    "\n".join(["\t\t{}".format(cmt) for cmt in comments])
                )
            )

        marks = rev_sheet.get_all_revision_marks()
        if marks:
            print(
                "\n\t\tRevision Marks:\n{}".format(
                    "\n".join(["\t\t{}".format(mrk) for mrk in marks])
                )
            )
        console.insert_divider()
