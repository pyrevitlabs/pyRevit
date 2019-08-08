# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc_id": str(__eventargs__.DocumentId),
        "status": str(__eventargs__.Status),
    }
)