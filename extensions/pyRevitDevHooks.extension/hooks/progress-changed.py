# pylint: skip-file
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script
import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "caption": str(args.Caption),
        "lower": str(args.LowerRange),
        "upper": str(args.UpperRange),
        "position": str(args.Position),
        "stage": str(args.Stage),
    },
    log_doc_access=True
)