"""Saves chosen families from the project"""
#pylint: disable=import-error,invalid-name,broad-except
import os.path as op
from pyrevit import revit
from pyrevit import forms
from pyrevit import script
from pyrevit.revit import FailureSwallowerContext


logger = script.get_logger()
output = script.get_output()

family_dict = {}
saved_families = 0
count_errors = 0
count_warnings = 0


for family in revit.query.get_families(revit.doc, only_editable=True):
    if family.FamilyCategory:
        family_dict[
            "%s: %s" % (family.FamilyCategory.Name, family.Name)
            ] = family
if not family_dict:
    script.exit()

selected_families = \
    forms.SelectFromList.show(
        sorted(family_dict.keys()),
        title="Select Families to Save",
        multiselect=True)
if not selected_families:
    forms.alert("Can not find any families that can be saved in this model.",
                exitscript=True)

dest_folder = forms.pick_folder()
if not dest_folder:
    script.exit()

total_work = len(selected_families)

with forms.ProgressBar(title="Saving families..."
                             " ({value} of {max_value})",
                       cancellable=True) as pb:
    with FailureSwallowerContext() as swallower:
        try:
            for idx, family in enumerate(
                    [family_dict[x] for x in selected_families]):
                if pb.cancelled:
                    break
                family_filepath = op.join(dest_folder,
                                          family.Name + ".rfa")
                logger.info("Saving %s ..." % family_filepath)
                try:
                    family_doc = revit.doc.EditFamily(family)
                    family_doc.SaveAs(family_filepath)
                    family_doc.Close(False)
                    saved_families += 1
                except Exception as ex:
                    logger.error("Error saving family %s | %s",
                                 family_filepath, ex)
                    count_errors += 1
                # check if warnings were swallowed
                swallowed_warnings = swallower.get_swallowed()
                if swallowed_warnings:
                    logger.warning("Warnings in family %s | %s",
                                   family.Name,
                                   ", ".join(set(swallowed_warnings)))
                    count_warnings += 1
                pb.update_progress(idx + 1, total_work)
        except Exception as ex:
            logger.error(ex)
# show results
if saved_families == len(selected_families):
    forms.alert("Saved: {} families.".format(saved_families))
else:
    forms.alert("Saved: {} of {} families."
                .format(saved_families, len(selected_families)))
if not count_errors and count_warnings and saved_families:
    output.log_success("Finished")
elif count_errors:
    output.log_warning("{} families cannot be saved"
                       .format(count_errors))
if count_warnings:
    logger.warning("{} families have warnings"
                   .format(count_warnings))
