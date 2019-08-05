# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "path": str(__eventargs__.LinkedResourcePathName),
        "type": str(__eventargs__.ResourceType),
    },
    log_doc_access=True
)