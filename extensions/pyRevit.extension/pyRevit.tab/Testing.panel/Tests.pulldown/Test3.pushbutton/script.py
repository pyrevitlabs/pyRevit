import sys
print sys.version

from pyrevit.coreutils.logger import get_logger

logger = get_logger(__commandname__)

print '\n'.join(sys.path)

from pyrevit import EXEC_PARAMS

print EXEC_PARAMS.executor_version
