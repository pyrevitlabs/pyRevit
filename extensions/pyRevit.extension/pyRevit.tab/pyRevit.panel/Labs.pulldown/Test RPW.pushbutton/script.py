import sys
print sys.version

from pyrevit.coreutils.logger import get_logger
import rpw

logger = get_logger(__commandname__)

print '\n'.join(sys.path)

from pyrevit import EXEC_PARAMS

print EXEC_PARAMS.executor_version

# noinspection PyUnresolvedReferences
from System import AppDomain

for loaded_assembly in AppDomain.CurrentDomain.GetAssemblies():
    print loaded_assembly.Location
