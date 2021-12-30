# pylint: skip-file
# revit 2022 fires this event for the new PDF export feature
# https://discourse.pyrevitlabs.io/t/revit-2022-pdf-export-event/416/3
# Revit 2022 added PDF to the list of export formats
# https://apidocs.co/apps/revit/2022/f43a36a6-ebce-29e2-693b-9b9867da026b.htm#
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script
import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "doc": str(revit.doc),
        "format": str(args.Format),
        "path": str(args.Path),
        "status": str(args.Status),
    },
    log_doc_access=True
)
