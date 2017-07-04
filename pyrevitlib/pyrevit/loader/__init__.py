import os.path as op
from pyrevit import EXEC_PARAMS


if not EXEC_PARAMS.doc_mode:
    LOADER_DIR = op.dirname(__file__)
else:
    LOADER_DIR = None


ASSEMBLY_FILE_TYPE = 'dll'
LOADER_ADDON_NAMESPACE = 'PyRevitLoader'


HASH_CUTOFF_LENGTH = 16
