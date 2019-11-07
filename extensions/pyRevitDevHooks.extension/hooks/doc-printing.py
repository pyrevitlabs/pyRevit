# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "views": str(__eventargs__.GetViewElementIds()),
        "settings": str(__eventargs__.GetSettings()),
    },
    log_doc_access=True
)