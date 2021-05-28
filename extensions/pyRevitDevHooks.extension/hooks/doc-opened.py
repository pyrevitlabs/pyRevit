# pylint: skip-file
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script

args = EXEC_PARAMS.event_args

import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "doc": str(revit.doc),
        "status": str(args.Status),
        "script_doc": script.get_document_data_file('this', '.dat')
    },
    log_doc_access=True
)