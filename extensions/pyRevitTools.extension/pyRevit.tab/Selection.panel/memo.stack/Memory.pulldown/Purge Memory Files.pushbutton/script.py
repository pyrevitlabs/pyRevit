# -*- coding: utf-8 -*-
"""Delete every pyRevit memory data file of this Revit version."""

import os
import os.path as op

from pyrevit import forms, script
from pyrevit.coreutils import appdata

import selectionmemory

logger = script.get_logger()
output = script.get_output()


def remove_files(paths):
    removed = []
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            logger.exception("{} could not be removed.".format(path))
        else:
            removed.append(op.basename(path))
    return removed


def main():
    memory_files = appdata.list_data_files(
        ".{}".format(selectionmemory.DATA_FILE_EXTENSION)
    )
    if not memory_files:
        forms.alert(selectionmemory.text("purge_nothing"), exitscript=True)
    removed = remove_files(memory_files)
    output.print_md(selectionmemory.text("purge_done").format(len(removed)))
    for file_name in removed:
        output.print_md("- `{}`".format(file_name))


if __name__ == "__main__":
    main()
