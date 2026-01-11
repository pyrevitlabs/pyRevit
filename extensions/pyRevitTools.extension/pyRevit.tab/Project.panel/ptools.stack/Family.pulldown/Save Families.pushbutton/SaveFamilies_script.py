# -*- coding: utf-8 -*-
"""Saves chosen families from the project"""
# pylint: disable=import-error,invalid-name,broad-except
import os
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
            overwrite_option = forms.CommandSwitchWindow.show(
                ["Skip Existing Families", "Overwrite Existing Families"],
                message="Choose what to do with existing families:",
            )
            if not overwrite_option:
                script.exit()

            subfolder_option = forms.CommandSwitchWindow.show(
                ["Save to a single folder", "Create subfolders by category"],
                message="Choose how to organize saved families:",
            )
            if not subfolder_option:
                script.exit()

            overwrite_exst = overwrite_option == "Overwrite Existing Families"
            create_subfolders = subfolder_option == "Create subfolders by category"

            save_opts = DB.SaveAsOptions()
            save_opts.OverwriteExistingFile = overwrite_exst
            total_work = len(selected_families)
            for idx, family in enumerate(
                    [family_dict[x] for x in selected_families]
                ):
                target_dir = dest_folder
                if create_subfolders:
                    category_name = family.FamilyCategory.Name or "Unknown"
                    target_dir = op.join(dest_folder, category_name)
                    if not op.exists(target_dir):
                        try:
                            os.makedirs(target_dir)
                        except OSError as ex:
                            target_dir = dest_folder
                            logger.error("Failed to create directory %s | %s", target_dir, ex)
                            continue
                family_filepath = op.join(target_dir, family.Name + ".rfa")
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
