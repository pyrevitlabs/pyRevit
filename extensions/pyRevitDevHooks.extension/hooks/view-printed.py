# pylint: skip-file
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script
import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "doc": str(revit.doc),
        "index": str(args.Index),
        "total_views": str(args.TotalViews),
        "view": str(args.View),
        "status": str(args.Status),
    },
    log_doc_access=True
)