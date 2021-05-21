# pylint: skip-file
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script
import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "accessor": str(args.GetFailuresAccessor()),
        "get_results": str(args.GetProcessingResult()),
        # "set_results": str(args.SetProcessingResult()),
    },
    log_doc_access=True
)