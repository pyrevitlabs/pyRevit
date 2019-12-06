# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.CurrentDocument),
        "formula": str(__eventargs__.Formula),
        "param_id": str(__eventargs__.ParameterId),
    },
    log_doc_access=True
)