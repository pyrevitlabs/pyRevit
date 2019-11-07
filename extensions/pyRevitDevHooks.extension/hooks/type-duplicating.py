# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "type_id": str(__eventargs__.ElementTypeId),
    },
    log_doc_access=True
)