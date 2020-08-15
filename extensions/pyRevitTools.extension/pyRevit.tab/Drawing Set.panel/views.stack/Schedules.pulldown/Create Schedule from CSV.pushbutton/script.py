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


def has_field_conflicts(keysched_def, fields):
    """Check if given schedule definition contains any of the fields"""
    for idx in range(keysched_def.GetFieldCount()):
        sched_field = keysched_def.GetField(idx)
        if sched_field.GetName() in fields:
            return sched_field.GetName()


def resolve_messy_conflicts(category, sched_name, fields, doc=None):
    """Decide what to do if there is an existing sched with identical name"""
    doc = doc or revit.doc
    all_schedules = \
        revit.query.get_all_views(doc=doc, view_types=[DB.ViewType.Schedule])
    # check for existing key schedules that use the fields already
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

    # check for matching view names
    all_schedules = \
        revit.query.get_all_views(doc=doc, view_types=[DB.ViewType.Schedule])
    existing_view = \
        revit.query.get_view_by_name(sched_name,
                                     view_types=[DB.ViewType.Schedule])
    if existing_view:
        if isinstance(existing_view, DB.ViewSchedule) \
                and existing_view.Definition.IsKeySchedule \
                and existing_view.Definition.CategoryId == category.Id:
            if forms.alert(
                    "There is a \"{}\" key schedule with name \"{}\". "
                    "Do you want to delete this first?".format(
                        category.Name,
                        sched_name),
                    yes=True, no=True):
                if safe_delete_keysched(doc, existing_view):
                    return sched_name
        else:
            if forms.alert(
                    "There is a view with the same name \"{}\" but it is "
                    "not a key schedule! Do you want to choose a new name "
                    "for this key schedule?"
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
        resolve_messy_conflicts(category, sched_name, fields[1:], doc=doc)
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
        # create records first
        create_schedule_record(new_key_sched, count=len(records))
        # now grab the records and update their param values
        # iterate over elements and records
        # FIXME: collect new elements only
        for keysched_el, record_data in zip(
                revit.query.get_all_elements_in_view(new_key_sched),
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
    return new_key_sched


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
            # start transaction
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
                        doc=revit.doc)
