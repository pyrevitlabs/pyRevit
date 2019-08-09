# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.GetDocument()),
        "added": str(__eventargs__.GetAddedElementIds().Count),
        "deleted": str(__eventargs__.GetDeletedElementIds().Count),
        "modified": str(__eventargs__.GetModifiedElementIds().Count),
        "txn_names": str(list(__eventargs__.GetTransactionNames())),
        "operation": str(__eventargs__.Operation),
    },
    log_doc_access=True
)