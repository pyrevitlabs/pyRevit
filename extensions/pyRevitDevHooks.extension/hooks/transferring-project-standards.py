# pylint: skip-file
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script
import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "doc": str(revit.doc),
        "source_doc": str(args.SourceDocument),
        "target_doc": str(args.TargetDocument),
        "ext_items": str(args.GetExternalItems()),
        # "set_ext_items": str(args.SetExternalItems()),
    },
    log_doc_access=True
)