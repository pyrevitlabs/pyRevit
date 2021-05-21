# pylint: skip-file
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script
import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "doc": str(revit.doc),
        "new_type_id": str(args.NewElementTypeId),
        "new_type_name": str(args.NewName),
        "original_type_id": str(args.OriginalElementTypeId),
        "status": str(args.Status),
    },
    log_doc_access=True
)