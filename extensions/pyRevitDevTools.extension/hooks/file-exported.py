# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "format": str(__eventargs__.Format),
        "path": str(__eventargs__.Path),
        "status": str(__eventargs__.Status),
    },
    log_doc_access=True
)