# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "new_type_id": str(__eventargs__.NewElementTypeId),
        "new_type_name": str(__eventargs__.NewName),
        "original_type_id": str(__eventargs__.OriginalElementTypeId),
        "status": str(__eventargs__.Status),
    },
    log_doc_access=True
)