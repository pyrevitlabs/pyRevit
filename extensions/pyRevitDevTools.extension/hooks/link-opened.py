# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "path": str(__eventargs__.LinkedResourcePathName),
        "type": str(__eventargs__.ResourceType),
        "status": str(__eventargs__.Status),
    },
    log_doc_access=True
)