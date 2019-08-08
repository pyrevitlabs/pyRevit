# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc_location": str(__eventargs__.Location),
        "status": str(__eventargs__.Status),
    }
)