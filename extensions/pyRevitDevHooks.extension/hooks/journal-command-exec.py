# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "command-id": __eventargs__.CommandId,
    },
    log_doc_access=False
)