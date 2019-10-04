# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "accessor": str(__eventargs__.GetFailuresAccessor()),
        "get_results": str(__eventargs__.GetProcessingResult()),
        # "set_results": str(__eventargs__.SetProcessingResult()),
    },
    log_doc_access=True
)