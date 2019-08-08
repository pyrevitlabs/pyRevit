# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "current_view": str(__eventargs__.CurrentActiveView),
        "new_view": str(__eventargs__.NewActiveView),
    },
    log_doc_access=True
)