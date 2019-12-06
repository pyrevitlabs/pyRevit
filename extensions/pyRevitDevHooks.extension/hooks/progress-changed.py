# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "caption": str(__eventargs__.Caption),
        "lower": str(__eventargs__.LowerRange),
        "upper": str(__eventargs__.UpperRange),
        "position": str(__eventargs__.Position),
        "stage": str(__eventargs__.Stage),
    },
    log_doc_access=True
)