# pylint: skip-file
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script
import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "frame_shown": str(args.DockableFrameShown),
        "pane_id": str(args.PaneId),
    },
    log_doc_access=True
)