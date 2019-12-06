# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "status": str(__eventargs__.Status),
        "passed_on": str(__eventargs__.GetPrintedViewElementIds()),
        "failed_on": str(__eventargs__.GetFailedViewElementIds()),
    },
    log_doc_access=True
)