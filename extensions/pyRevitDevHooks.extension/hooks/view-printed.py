# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "index": str(__eventargs__.Index),
        "total_views": str(__eventargs__.TotalViews),
        "view": str(__eventargs__.View),
        "status": str(__eventargs__.Status),
    },
    log_doc_access=True
)