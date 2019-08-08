# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc_type": str(__eventargs__.DocumentType),
        "doc_template": str(__eventargs__.Template),
    },
    log_doc_access=True
)