"""Assembly file cleanup for pyRevit sessions.

Extension assemblies are now built by the C# loader. This module only retains
the cleanup of stale assembly files left in the appdata folder between sessions.
"""
import os.path as op

from pyrevit import coreutils
from pyrevit.coreutils import assmutils
from pyrevit.coreutils import appdata
from pyrevit.coreutils import logger


#pylint: disable=W0703,C0103
mlogger = logger.get_logger(__name__)


def cleanup_assembly_files():
    if coreutils.get_revit_instance_count() == 1:
        for asm_file_path in appdata.list_data_files(file_ext='dll'):
            if not assmutils.find_loaded_asm(asm_file_path, by_location=True):
                appdata.garbage_data_file(asm_file_path)
                asm_log_file = asm_file_path.replace('.dll', '.log')
                if op.exists(asm_log_file):
                    appdata.garbage_data_file(asm_log_file)
