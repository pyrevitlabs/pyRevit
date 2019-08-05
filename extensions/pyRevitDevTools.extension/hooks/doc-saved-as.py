# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "master_file": str(__eventargs__.IsSavingAsMasterFile),
        "original_path": str(__eventargs__.OriginalPath),
        "status": str(__eventargs__.Status),
    },
    log_doc_access=True
)