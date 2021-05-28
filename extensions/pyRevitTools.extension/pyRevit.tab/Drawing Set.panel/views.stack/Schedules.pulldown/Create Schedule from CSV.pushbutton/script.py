"""Import existing CSV file as a key schedule.

- First CSV row must be field names
- First CSV field must be "Key Name"

CSV Example:
Key Name,Parameter1 Name,Parameter2 Name
A,Value11,Value12
B,Value21,Value22
C,Value32,Value32
"""
#pylint: disable=C0103,E0401,W0703

import csv
import codecs
import os.path as op
from collections import defaultdict

from pyrevit import PyRevitException
from pyrevit import forms
from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import script


logger = script.get_logger()


def safe_delete_keysched(doc, keysched):
    """Safely delete given key schedule"""
    try:
        doc.Delete(keysched.Id)
        return True
    except Exception as ex:
        forms.alert(
            "Failed deleting existing key schedule",
            expanded=str(ex))
    return False


def create_schedule_record(schedule, count=1):
    """Create rows in given schedule."""
    table_data = schedule.GetTableData()
    section_data = table_data.GetSectionData(DB.SectionType.Body)
    for _ in range(count):
        section_data.InsertRow(section_data.LastRowNumber + 1)


def create_schedule_records(schedule, fields, records):
    """Create records in given schedule"""
    # create records first
    create_schedule_record(schedule, count=len(records))
    # now grab the records and update their param values
    # iterate over elements and records
    for keysched_el, record_data in zip(
            revit.query.get_all_elements_in_view(schedule),
            records):
        logger.debug('Processing record: %s', record_data)
        for idx, field_name in enumerate(fields):
            if record_data[idx]:
                p = keysched_el.LookupParameter(field_name)
                if p and not p.SetValueString(record_data[idx]):
                    if p.StorageType == DB.StorageType.Integer:
                        p.Set(int(record_data[idx]))
                    elif p.StorageType == DB.StorageType.Double:
                        p.Set(float(record_data[idx]))
                    elif p.StorageType == DB.StorageType.String:
                        p.Set(record_data[idx])
                    elif p.StorageType == DB.StorageType.ElementId:
                        p.Set(DB.ElementId(int(record_data[idx])))


def has_matching_fields(keysched_def, fields):
    """Check if given schedule definition contains any of the fields"""
    exist_ksch_fields = set()
    for idx in range(keysched_def.GetFieldCount()):
        sched_field = keysched_def.GetField(idx)
        exist_ksch_fields.add(sched_field.GetName())
    other_fields = exist_ksch_fields.difference(set(fields))
    return len(other_fields) == 0


def has_field_conflicts(keysched_def, fields):
    """Check if given schedule definition contains any of the fields"""
    for idx in range(keysched_def.GetFieldCount()):
        sched_field = keysched_def.GetField(idx)
        if sched_field.GetName() in fields:
            return sched_field.GetName()


def resolve_naming_conflicts(category, sched_name, fields, doc=None):
    """Decide what to do if there is an existing sched with identical name

    This function needs to check these conditions, in this order:
        1- exisiting key schedule for given category, with any of the fields
        2- existing any schedule with matching name

    Exisiting key schedule for given category, with identical fields, has
    already been checked for and the update function would be called
    """
    doc = doc or revit.doc

    all_schedules = \
        revit.query.get_all_views(doc=doc, view_types=[DB.ViewType.Schedule])
    # check for existing key schedules (check 1)
    matching_keysched = next(
        (
            x for x in all_schedules
            if x.Definition.IsKeySchedule
            and x.Definition.CategoryId == category.Id
        ),
        None
    )
    if matching_keysched:
        cfield = has_field_conflicts(matching_keysched.Definition, fields)
        if cfield:
            if forms.alert(
                    "Field \"{}\" is already used by another "
                    "key schedule \"{}\". Multiple key schedules can not "
                    "set values for same parameter. Do you want to delete "
                    "the existing key schedule first?".format(
                        cfield,
                        matching_keysched.Name
                        ),
                    yes=True, no=True):
                # the the process continue to check matching names below
                if not safe_delete_keysched(doc, matching_keysched):
                    return None
            else:
                return None

    # by now, if there was a key schdule matching name, it is deleted
    # check for matching view names, of other types
    all_schedules = \
        revit.query.get_all_views(doc=doc, view_types=[DB.ViewType.Schedule])
    existing_sched = \
        revit.query.get_view_by_name(sched_name,
                                     view_types=[DB.ViewType.Schedule])
    if existing_sched:
        if forms.alert(
                "There is an existing schedule with the same name \"{}\"."
                "Do you want to choose a new name for this key schedule?"
                .format(sched_name),
                yes=True, no=True):
            return forms.ask_for_unique_string(
                reserved_values=[x.Name for x in all_schedules],
                default='{} {}'.format(sched_name, coreutils.current_date())
            )
        return None
    return sched_name


def create_key_schedule(category, key_name, sched_name,
                        fields=None, records=None, doc=None):
    """Create a key schedule for given category and fill with given data."""
    # verify input
    doc = doc or revit.doc
    fields = fields or []
    records = records or []

    # set name and key parameter name
    # fields[1:] because first field in keyname
    new_name = \
        resolve_naming_conflicts(category, sched_name, fields[1:], doc=doc)
    # if not name skip making schedule
    if not new_name:
        return

    # create the key schedule view
    new_key_sched = \
        DB.ViewSchedule.CreateKeySchedule(doc, category.Id)
    new_key_sched.Name = new_name
    new_key_sched.KeyScheduleParameterName = key_name
    # set the schedulable fields
    fsched_fields = {x.GetName(doc): x
                     for x in new_key_sched.Definition.GetSchedulableFields()}
    cancel_txn = False
    for field in fields:
        if field in fsched_fields:
            try:
                new_key_sched.Definition.AddField(fsched_fields[field])
            except Exception:
                logger.debug('Failed adding field: %s', field)
        else:
            cancel_txn = True
            logger.error(
                "Field \"%s\" is not schedulable for category \"%s\". "
                "Check applicable categories for this project parameter",
                field, category.Name
                )
    # if any errors lets cancel to remove the created key schedule
    if cancel_txn:
        raise PyRevitException("Cancelling changes due to errors")

    # fill with data
    if records:
        create_schedule_records(new_key_sched, fields, records)
    return new_key_sched


def find_matching_keyschedule(category, fields, doc=None):
    """Find any existing key schedules that have matching fields"""
    doc = doc or revit.doc
    all_schedules = \
        revit.query.get_all_views(doc=doc, view_types=[DB.ViewType.Schedule])
    # check for existing key schedules (check 1)
    matching_keysched = next(
        (
            x for x in all_schedules
            if x.Definition.IsKeySchedule
            and x.Definition.CategoryId == category.Id
        ),
        None
    )
    if matching_keysched:
        if has_matching_fields(matching_keysched.Definition, fields):
            return matching_keysched


def update_key_schedule(keyschedule, category, fields, records, doc=None):
    """Update existing key schedule with provided values"""
    doc = doc or revit.doc
    if forms.alert(
            "key schedule \"{}\" has identical fields. Multiple key "
            "schedules can not set values for same parameter.\n"
            "Do you want to update the data in existing schedule?"
            .format(keyschedule.Name),
            yes=True, no=True):
        # updating cells is possible but more complex logic was necessary
        # to find existing, new, and deleted records
        # the approach below is simpler but takes more exec time
        # collect key schedule param values on all elements
        value_dict = defaultdict(list)
        param_name = keyschedule.KeyScheduleParameterName
        for exst_el in revit.query.get_elements_by_categories(
                [revit.query.get_builtincategory(category.Name)],
                doc=doc):
            param = exst_el.LookupParameter(param_name)
            if param:
                value_dict[param.AsValueString()].append(exst_el.Id)

        # remove existing fields
        table_data = keyschedule.GetTableData()
        section_data = table_data.GetSectionData(DB.SectionType.Body)
        for idx in range(section_data.NumberOfRows-1, 0, -1):
            if section_data.CanRemoveRow(idx):
                section_data.RemoveRow(idx)
        # create new fields
        create_schedule_records(keyschedule, fields, records)

        # update all elements with the same key schedule value
        schedule_els = revit.query.get_all_elements_in_view(keyschedule)
        first_rec = fields[0]
        sched_items = {x.LookupParameter(first_rec).AsString(): x.Id
                       for x in schedule_els}
        new_possible_values = [x[0] for x in records]
        for param_value, element_ids in value_dict.items():
            if param_value in new_possible_values:
                for eid in element_ids:
                    exst_el = doc.GetElement(eid)
                    if exst_el:
                        param = exst_el.LookupParameter(param_name)
                        if param:
                            param.Set(sched_items[param_value])


def ensure_parameters(category, parameter_defs, doc=None):
    """Ensure parameters exist for given categoryself.

    Args:
        parameter_defs (list[tuple]): list of (name, type) tuples
    """
    # FIXME: ensure the defined params have cat in them
    doc = doc or revit.doc
    # builtincat = revit.query.get_builtincategory(category.Id)
    params_ensured = True
    with revit.Transaction("Ensure CSV Fields"):
        for param_def in parameter_defs:
            if not revit.query.model_has_parameter(param_def[0]):
                logger.critical(
                    "Missing project parameter.\n"
                    "Name: \"%s\"\n"
                    "Type: %s\n"
                    "Category %s",
                    param_def[0], param_def[1], category.Name)
                params_ensured = False
                # FIXME: API does not allow creating project parameters
                # revit.create.create_project_parameter(
                #     param_name=param_def[0],
                #     param_type=param_def[1],
                #     category_list=[builtincat],
                #     builtin_param_group=DB.BuiltInParameterGroup.PG_DATA,
                #     doc=revit.doc
                #     )
    if not params_ensured:
        logger.critical(
            "Revit API does not allow creation of "
            "Project Parameters. Please create the missing parameters "
            "manually before importing the data from CSV file."
            )
    return params_ensured


def read_csv_typed_data(csv_file):
    """Read Revit property data from the given CSV file."""
    # open file
    with codecs.open(csv_file, 'rb', encoding='utf-8') as csvfile:
        # read lines
        csv_lines = list(csv.reader(csvfile, delimiter=',', quotechar='\"'))
        # grab the first line, extract field names
        # if field definition include the type, grab the associated
        # DB.ParameterType as well
        # https://www.apidocs.co/apps/revit/2019/f38d847e-207f-b59a-3bd6-ebea80d5be63.htm
        # https://support.spatialkey.com/providing-data-types-in-csv-headers/
        field_defs = []
        for field_def in csv_lines[0]:
            parts = field_def.split('|')
            parts_count = len(parts)
            if parts_count == 1:
                if parts[0]:
                    field_defs.append((parts[0], DB.ParameterType.Text))
            elif parts_count == 2:
                field_defs.append((parts[0],
                                   coreutils.get_enum_value(DB.ParameterType,
                                                            parts[1])))
    # return field definitions, and data
    return (field_defs, csv_lines[1:])


if __name__ == '__main__':
    # ask user for source CSV file
    source_file = forms.pick_file(file_ext='csv')
    if source_file:
        fname = op.splitext(op.basename(source_file))[0]
        # as user for target key schedule category
        key_sched_cat = forms.SelectFromList.show(
            revit.query.get_key_schedule_categories(),
            name_attr='Name',
            multiselect=False,
            title="Select Key-Schedule Category",
            )
        if key_sched_cat:
            # read the csv data
            param_defs, param_data = read_csv_typed_data(source_file)
            # grab the param names
            param_names = [x[0] for x in param_defs]
            # decide to create, or update existing
            existing_keyschedule = \
                find_matching_keyschedule(category=key_sched_cat,
                                          fields=param_names)
            if existing_keyschedule:
                with revit.Transaction('Update Schedule from CSV',
                                       log_errors=False):
                    # update the data in current schedule
                    update_key_schedule(
                        keyschedule=existing_keyschedule,
                        category=key_sched_cat,
                        fields=param_names,
                        records=param_data,
                        doc=revit.doc
                    )
            else:
                with revit.Transaction('Create Schedule from CSV',
                                       log_errors=False):
                    # make sure field parameters exist
                    # creates project params if not
                    # skip the first on since it is "Key Name" and only applies
                    # to elements inside a key schedule
                    if ensure_parameters(key_sched_cat, param_defs[1:]):
                        # create the schedule and fill with data now
                        create_key_schedule(
                            category=key_sched_cat,
                            key_name=fname,
                            sched_name=fname,
                            fields=param_names,
                            records=param_data,
                            doc=revit.doc
                        )
