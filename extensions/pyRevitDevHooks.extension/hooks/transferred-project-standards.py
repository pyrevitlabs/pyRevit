# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "source_doc": str(__eventargs__.SourceDocument),
        "target_doc": str(__eventargs__.TargetDocument),
        "ext_items": str(__eventargs__.GetSelectedExternalItems()),
    },
    log_doc_access=True
)