#! python3
# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "current_view": str(__eventargs__.CurrentActiveView),
        "prev_view": str(__eventargs__.PreviousActiveView),
        "status": str(__eventargs__.Status),
    },
    log_doc_access=True
)