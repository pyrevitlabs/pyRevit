# pylint: skip-file
import os.path as op
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script

import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "command_id": str(args.CommandId.Name),
        "doc_title": str(revit.doc.Title),
    }
)

output = script.get_output()
output.print_image(
    op.join(op.dirname(__file__), op.basename(__file__).replace('.py', '.gif'))
)