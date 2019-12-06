# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "page_count": str(__eventargs__.PagesCount),
    },
    log_doc_access=True
)