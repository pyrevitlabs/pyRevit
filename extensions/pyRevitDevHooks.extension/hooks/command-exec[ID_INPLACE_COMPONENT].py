# pylint: skip-file
import os.path as op
from pyrevit import script

import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "command_id": str(__eventargs__.CommandId.Name),
        "doc_title": str(__eventargs__.ActiveDocument.Title),
    }
)

output = script.get_output()
output.print_image(
    op.join(op.dirname(__file__), op.basename(__file__).replace('.py', '.gif'))
)