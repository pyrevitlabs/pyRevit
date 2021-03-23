# pylint: skip-file
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script

import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "doc": str(revit.doc),
        "added": str(args.GetAddedElementIds().Count),
        "deleted": str(args.GetDeletedElementIds().Count),
        "modified": str(args.GetModifiedElementIds().Count),
        "txn_names": str(list(args.GetTransactionNames())),
        "operation": str(args.Operation),
    },
    log_doc_access=True
)