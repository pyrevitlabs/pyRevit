# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "doc_location": str(__eventargs__.Location),
        "options": str(__eventargs__.Options),
    },
    log_doc_access=True
)