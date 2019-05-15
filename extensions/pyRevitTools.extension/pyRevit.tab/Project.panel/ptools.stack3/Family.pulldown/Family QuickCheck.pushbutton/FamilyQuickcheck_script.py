# -*- coding: utf-8 -*-
"""Non-exhaustive check to detect corrupt Revit families.

Copyright (c) 2017 Frederic Beaupere
github.com/frederic-beaupere
"""
#pylint: disable=invalid-name,import-error,superfluous-parens,broad-except

from pyrevit import revit, DB
from pyrevit import script


__author__ = 'Frederic Beaupere\n{{author}}'


logger = script.get_logger()
output = script.get_output()

all_families = DB.FilteredElementCollector(revit.doc)\
                 .OfClass(DB.Family)\
                 .ToElements()

editable_families = [x for x in all_families if x.IsEditable]
total_count = len(editable_families)
checked_families = 0

output.reset_progress()

for fam in editable_families:
    fam_name = revit.query.get_name(fam)
    logger.debug("attempt to open family: %s", fam_name)
    try:
        fam_doc = revit.doc.EditFamily(fam)
        fam_doc.Close(False)
        print(":white_heavy_check_mark: %s" % fam_name)
    except Exception as ex:
        logger.error(":cross_mark: %s | error: %s", fam.Name, str(ex))

    checked_families += 1
    output.update_progress(checked_families, total_count)

print("\nChecked: {} families.".format(checked_families))
