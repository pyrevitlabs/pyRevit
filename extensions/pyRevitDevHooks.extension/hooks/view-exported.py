# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "view_id": str(__eventargs__.ViewId),
        "status": str(__eventargs__.Status),
    },
    log_doc_access=True
)