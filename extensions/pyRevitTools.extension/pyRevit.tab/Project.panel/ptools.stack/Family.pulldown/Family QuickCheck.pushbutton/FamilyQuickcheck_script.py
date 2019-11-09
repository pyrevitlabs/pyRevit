# -*- coding: utf-8 -*-
"""Non-exhaustive check to detect corrupt Revit families.

Copyright (c) 2017 Frederic Beaupere
github.com/frederic-beaupere

PR731 https://github.com/eirannejad/pyRevit/pull/731
"""
#pylint: disable=invalid-name,import-error,superfluous-parens,broad-except
from pyrevit import revit
from pyrevit import forms
from pyrevit import script


__author__ = 'Frederic Beaupere\n{{author}}'


logger = script.get_logger()
output = script.get_output()


checked_families = 0
count_exceptions = 0
count_swallowed = 0
count_families_with_warnings = 0


all_families = revit.query.get_families(revit.doc, only_editable=True)
editable_families = []

if __shiftclick__: #pylint: disable=E0602
    family_dict = {}
    for family in all_families:
        if family.FamilyCategory:
            family_dict[
                "%s: %s" % (family.FamilyCategory.Name, family.Name)
                ] = family

    selected_families = \
        forms.SelectFromList.show(
            sorted(family_dict.keys()),
            title="Select Families to Check",
            multiselect=True)
    if selected_families:
        editable_families = [family_dict[x] for x in selected_families]
else:
    editable_families = [x for x in all_families if x.IsEditable]

total_count = len(editable_families)

output.reset_progress()


with revit.ErrorSwallower(log_errors=True) as swallower:
    for fam in editable_families:
        # get the family name
        fam_name = revit.query.get_name(fam)
        logger.debug("attempt to open family: %s", fam_name)

        try:
            # attempt to open family
            fam_doc = revit.doc.EditFamily(fam)
            # report swallowed warnings
            swallowed_errors = swallower.get_swallowed_errors()
            if swallowed_errors:
                error_descs = "\n".join(
                    [x.GetDescriptionText() for x in swallowed_errors]
                    )
                logger.warning(":warning: %s\n%s", fam.Name, error_descs)
                count_swallowed += len(swallowed_errors)
                count_families_with_warnings += 1
            else:
                print(":white_heavy_check_mark: %s" % fam_name)
            # close family
            fam_doc.Close(False)
            swallower.reset()
        except Exception as ex:
            # report exceptions occured when doing any of above
            logger.error(":cross_mark: %s | error: %s", fam.Name, ex)
            count_exceptions += 1

        # increment, update gui, and proceed
        checked_families += 1
        output.update_progress(checked_families, total_count)
        output.set_title("Family QuickCheck (X{} !{})"
                         .format(count_exceptions, count_swallowed))
        if output.is_closed_by_user:
            script.exit()


# report results
print("\nChecked: {} families.".format(checked_families))

if count_exceptions:
    logger.warning("%s families seem to be corrupted", count_exceptions)

if count_families_with_warnings and count_swallowed:
    logger.warning(
        "%s families have total of %s warnings",
        count_families_with_warnings,
        count_swallowed
        )

if not (count_exceptions and count_swallowed):
    logger.success("Finished. No errors found.")
