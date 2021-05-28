"""Saves chosen families from the project"""
# pylint: disable=import-error,invalid-name,broad-except
import os.path as op
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


family_dict = {}
for family in revit.query.get_families(revit.doc, only_editable=True):
    if family.FamilyCategory:
        family_dict[
            "%s: %s" % (family.FamilyCategory.Name, family.Name)
        ] = family

if family_dict:
    selected_families = forms.SelectFromList.show(
        sorted(family_dict.keys()),
        title="Select Families to Save",
        multiselect=True,
    )

    if selected_families:
        dest_folder = forms.pick_folder()
        if dest_folder:
            selected_option = forms.CommandSwitchWindow.show(
                ["Skip Existing Families", "Overwrite Existing Families"],
                message="Choose what to do with existing families:",
            )
            overwrite_exst = selected_option == "Overwrite Existing Families"
            save_opts = DB.SaveAsOptions()
            save_opts.OverwriteExistingFile = overwrite_exst
            total_work = len(selected_families)
            for idx, family in enumerate(
                    [family_dict[x] for x in selected_families]
                ):
                family_filepath = op.join(dest_folder, family.Name + ".rfa")
                if not overwrite_exst and op.exists(family_filepath):
                    logger.info(
                        "Skipping existing family %s ...", family_filepath
                    )
                else:
                    logger.info(
                        "%s %s ...",
                        "Updating" if op.exists(family_filepath) else "Saving",
                        family_filepath,
                    )
                    try:
                        family_doc = revit.doc.EditFamily(family)
                        family_doc.SaveAs(family_filepath, save_opts)
                        family_doc.Close(False)
                    except Exception as ex:
                        logger.error(
                            "Error saving family %s | %s", family_filepath, ex
                        )
                output.update_progress(idx + 1, total_work)
else:
    forms.alert("Can not find any families that can be saved in this model.")
