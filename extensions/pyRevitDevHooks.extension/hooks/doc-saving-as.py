# pylint: skip-file
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script
import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(
    __file__,
    {
        "cancellable?": str(args.Cancellable),
        "doc": str(revit.doc),
        "master_file": str(args.IsSavingAsCentralFile if HOST_APP.is_newer_than(2021) else args.IsSavingAsMasterFile),
        "doc_path": str(args.PathName),
    },
    log_doc_access=True
)