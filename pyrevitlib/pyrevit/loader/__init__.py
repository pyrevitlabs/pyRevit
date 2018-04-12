import os.path as op
from pyrevit import EXEC_PARAMS


ASSEMBLY_FILE_TYPE = 'dll'
LOADER_ADDON_NAMESPACE = 'PyRevitLoader'


HASH_CUTOFF_LENGTH = 16

RELOAD_SCRIPT_PATH = op.join(op.dirname(__file__), 'sessionreload')
