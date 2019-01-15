"""Import selected csv file as a schedule."""


import os
import os.path as op
import csv

from pyrevit import forms
from pyrevit import coreutils
from pyrevit import revit, DB


def create_record(schedule, fields):
    table_data = schedule.GetTableData()
    section_data = table_data.GetSectionData(DB.SectionType.Body)
    section_data.InsertRow(section_data.FirstRowNumber + 1)
    # section_data.SetCellText(section_data.FirstRowNumber + 1,
    #                          section_data.FirstColumnNumber,
    #                          fields[0])


def create_records(viewsched, key_records, doc=None):
    doc = doc or revit.doc
    for krec in key_records:
        create_record(viewsched, ("BRRR", ))

    cl = DB.FilteredElementCollector(doc, viewsched.Id).WhereElementIsNotElementType().ToElements()
    for el, rec in zip(list(cl), key_records):
        p = el.LookupParameter("Key Name")
        p.Set(rec[0])
        p = el.LookupParameter("# Abbreviations")
        p.Set(rec[1])


# def create_key_schedule(key_name, sched_name, key_records=None, doc=None):
#     doc = doc or revit.doc
#     key_records = key_records or []
#     point_load = revit.query.get_category('Internal Point Loads')
#     if point_load:
#         with revit.Transaction('Create Schedule from CSV'):
#             new_key_sched = \
#                 DB.ViewSchedule.CreateKeySchedule(doc, point_load.Id)
#             new_key_sched.Name = sched_name
#             new_key_sched.KeyScheduleParameterName = key_name


source_file = forms.pick_file(file_ext='csv')
if source_file:
    with open(source_file, 'rb') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',', quotechar='\"')
        data = [(x[0], x[1]) for x in spamreader]
    # create_key_schedule("Abbrevs", "" "Abbreviations", key_records=data)
    with revit.Transaction('Create Schedule from CSV'):
        create_records(revit.activeview, data)