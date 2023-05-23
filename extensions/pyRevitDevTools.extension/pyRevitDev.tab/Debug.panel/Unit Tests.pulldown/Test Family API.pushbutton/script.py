"""
Exercise the Revit family creation API:
1. Creates a new Generic Annotation family and load it into the current document.
2. Re-open the family, add some types, and re-load it.
3. Check that the types were loaded, and the parameter values are correct.
4. Purge the test family from the current document.

Enable pyRevit log messages to see the test confirmation messages.
Test errors are raised Python exceptions.
"""
import os
import tempfile

from pyrevit import revit, DB, script, HOST_APP
from pyrevit.revit.db.create import FamilyLoaderOptionsHandler
from pyrevit.revit.db.transaction import Transaction


__context__ = "doc-project"

TEMP_FAMILY_NAME = "pyRevitTestFamily"
TEST_PARAMETER_NAME = "Test Parameter"
TYPES_TO_ADD = {"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0}
LOG = script.get_logger()


def _purge_family():
    """Remove the temporary family from the document."""
    to_delete = None
    collector = DB.FilteredElementCollector(revit.doc).OfClass(DB.Family)
    for family_element in collector.GetElementIterator():
        if family_element.Name == TEMP_FAMILY_NAME:
            to_delete = family_element.Id
            break
    if to_delete is not None:
        message = "Purge {0} family".format(TEMP_FAMILY_NAME)
        with Transaction(message, doc=revit.doc):
            revit.doc.Delete(to_delete)
            LOG.info(message)


def _family_type_count(family_id):
    """
    Return the number of types in a loaded family.
    """
    if isinstance(family_id, int):
        family_id = DB.ElementId(family_id)
    elif not isinstance(family_id, DB.ElementId):
        raise TypeError()
    family = revit.doc.GetElement(family_id)
    return len(list(family.GetFamilySymbolIds()))


def _add_types(family_doc):
    """
    Create new types in the test family, and assign values to the type
    parameter.
    """
    if not isinstance(family_doc, DB.Document):
        raise TypeError()
    if not family_doc.IsFamilyDocument:
        raise ValueError()
    manager = family_doc.FamilyManager
    parameter = manager.get_Parameter(TEST_PARAMETER_NAME)
    with Transaction("Add Family Types", doc=family_doc):
        for k, v in TYPES_TO_ADD.items():
            manager.NewType(k)
            manager.Set(parameter, v)


def _check_type_parameter_values(family_id):
    """
    Check the family types and parameter values in the loaded test family.
    """
    if isinstance(family_id, int):
        family_id = DB.ElementId(family_id)
    elif not isinstance(family_id, DB.ElementId):
        raise TypeError()
    family_element = revit.doc.GetElement(family_id)
    for type_id in family_element.GetFamilySymbolIds():
        type_element = revit.doc.GetElement(type_id)
        type_name = type_element.get_Parameter(
            DB.BuiltInParameter.ALL_MODEL_TYPE_NAME
        ).AsString()
        if type_name == TEMP_FAMILY_NAME:
            continue
        if type_name not in TYPES_TO_ADD:
            raise KeyError("Unexpected Type Name: " + type_name)
        parameter = type_element.LookupParameter(TEST_PARAMETER_NAME)
        if parameter is None:
            raise TypeError("Missing Type Parameter: " + TEST_PARAMETER_NAME)
        if abs(parameter.AsDouble() - TYPES_TO_ADD[type_name]) > 0.0000001:
            raise ValueError("Unexpected value in type parameter.")


def test_family_api():
    """Exercise the Revit family creation API."""
    _purge_family()
    family_template_path = HOST_APP.app.FamilyTemplatePath
    assert os.path.isdir(family_template_path)
    LOG.info("Family Template Path: {0}".format(family_template_path))
    family_template = os.path.normpath(
        os.path.join(
            family_template_path,
            r"English-Imperial\Annotations\Generic Annotation.rft",
        )
    )
    if not os.path.isfile(family_template):
        # Older Versions of Revit include the languge in the family template path.
        family_template = os.path.normpath(
            os.path.join(
                family_template_path,
                r"Annotations\Generic Annotation.rft",
            )
        )
    if not os.path.isfile(family_template):
        # We're not running on an English copy of Revit.
        # Return the first template file we find.
        for base, dirs, files in os.walk(family_template_path):
            for f in files:
                if os.path.splitext(f)[1].lower() == ".rft":
                    family_template = os.path.normpath(os.path.join(base, f))
                    break
            if os.path.isfile(family_template):
                break
        else:
            raise EnvironmentError(
                "Failed to find an RFT file in the Family Template Path."
            )
    LOG.info("Using Family Template: {0}".format(os.path.basename(family_template)))
    family_doc = HOST_APP.app.NewFamilyDocument(family_template)
    LOG.info(
        "Created new family with {0} template.".format(
            os.path.splitext(os.path.basename(family_template))[0]
        )
    )
    manager = family_doc.FamilyManager
    with Transaction("Add Project Parameter", doc=family_doc):
        if HOST_APP.is_newer_than(2021):
            manager.AddParameter(
                parameterName=TEST_PARAMETER_NAME,
                groupTypeId=DB.GroupTypeId.General,
                specTypeId=DB.SpecTypeId.Number,
                isInstance=False,
            )
        else:
            manager.AddParameter(
                parameterName=TEST_PARAMETER_NAME,
                parameterGroup=DB.BuiltInParameterGroup.PG_GENERAL,
                parameterType=DB.ParameterType.Number,
                isInstance=False,
            )
    LOG.info("Added test type parameter to new family.")
    temporary_dir = tempfile.mkdtemp()
    family_path = os.path.normpath(
        os.path.join(temporary_dir, TEMP_FAMILY_NAME + ".rfa")
    )
    save_options = DB.SaveAsOptions()
    save_options.OverwriteExistingFile = True
    family_doc.SaveAs(family_path, save_options)
    assert os.path.isfile(family_path)
    family_element = family_doc.LoadFamily(revit.doc, FamilyLoaderOptionsHandler())
    LOG.info("Loaded test family into current document.")
    family_doc.Close()
    assert _family_type_count(family_element.Id.IntegerValue) == 1
    LOG.info("Checked that only the base type is in the test family.")
    family_doc = revit.doc.EditFamily(family_element)
    _add_types(family_doc)
    type_count = len(TYPES_TO_ADD.keys()) + 1
    LOG.info(
        "Re-opened the test family for editing and added {0} type{1}.".format(
            type_count,
            "" if type_count == 1 else "s",
        )
    )
    family_element = family_doc.LoadFamily(revit.doc, FamilyLoaderOptionsHandler())
    family_doc.Close()
    LOG.info("Reloaded test family into current file.")
    assert _family_type_count(family_element.Id.IntegerValue) == type_count
    LOG.info(
        "Checked that {0} type{1} are in the test family, as expected.".format(
            type_count,
            "" if type_count == 1 else "s",
        )
    )
    _check_type_parameter_values(family_element.Id.IntegerValue)
    LOG.info("Checked that the parameter values are correct in the test family.")
    _purge_family()
    LOG.info("Test completed.")


if __name__ == "__main__":
    test_family_api()
