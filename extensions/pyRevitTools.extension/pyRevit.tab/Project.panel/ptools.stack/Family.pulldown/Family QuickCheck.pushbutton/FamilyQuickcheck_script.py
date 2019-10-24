# -*- coding: utf-8 -*-
"""Non-exhaustive check to detect corrupt Revit families.

Copyright (c) 2017 Frederic Beaupere
github.com/frederic-beaupere
"""
#pylint: disable=invalid-name,import-error,superfluous-parens,broad-except

from pyrevit import revit, script, DB, forms
from pyrevit.revit import FailureSwallowerContext


__author__ = 'Frederic Beaupere\n{{author}}'

logger = script.get_logger()
output = script.get_output()

checked_families = 0
count_errors = 0
count_warnings = 0
cancelled = False

def update_output_title():
    output.set_title("Family QuickCheck (Err:{} Warn:{})"
                     .format(count_errors, count_warnings))


all_families = DB.FilteredElementCollector(revit.doc)\
                 .OfClass(DB.Family)\
                 .ToElements()

editable_families = [x for x in all_families if x.IsEditable]
total_count = len(editable_families)

output.reset_progress()

with FailureSwallowerContext(force=True) as swallower:
    try:
        for fam in editable_families:
            # cancel if output window was closed
            if output.window.ClosedByUser:
                break
            fam_name = revit.query.get_name(fam)
            logger.debug("attempt to open family: %s", fam_name)
            try:
                fam_doc = revit.doc.EditFamily(fam)
                fam_doc.Close(False)
                swallowed_warnings = swallower.get_swallowed()
                if swallowed_warnings:
                    logger.warning(":warning: %s | warning: %s", fam.Name,
                                   ", ".join(set(swallowed_warnings)))
                    count_warnings += 1
                    update_output_title()
                else:
                    print(":white_heavy_check_mark: %s" % fam_name)
            except Exception as ex:
                logger.error(":cross_mark: %s | error: %s", fam.Name, ex)
                count_errors += 1
                update_output_title()
            checked_families += 1
            output.update_progress(checked_families, total_count)
    except Exception as ex:
        logger.error(ex)

print("\nChecked: {} families.".format(checked_families))
if not count_errors and count_warnings:
    output.log_success("Finished. No errors found.")
elif count_errors:
    output.log_warning("{} families seem to be corrupted".format(count_errors))
if count_warnings:
    logger.warning("{} families have warnings".format(count_warnings))
