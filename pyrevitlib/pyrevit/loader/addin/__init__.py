import os.path as op
from pyrevit import EXEC_PARAMS
from pyrevit.coreutils import make_canonical_name
from pyrevit.loader import LOADER_DIR, ASSEMBLY_FILE_TYPE


if not EXEC_PARAMS.doc_mode:
    ADDIN_DIR = op.join(LOADER_DIR, 'addin')
    ADDIN_RESOURCE_DIR = op.join(ADDIN_DIR,
                                 'Source', 'pyRevitLoader', 'Resources')
else:
    ADDIN_DIR = ADDIN_RESOURCE_DIR = None


def get_addin_dll_file(addin_filename):
    addin_file = op.join(ADDIN_DIR, make_canonical_name(addin_filename, ASSEMBLY_FILE_TYPE))
    if op.exists(addin_file):
        return addin_file

    return None
