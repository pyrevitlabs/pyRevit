# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "operation": str(__eventargs__.Operation),
    },
    log_doc_access=True
)