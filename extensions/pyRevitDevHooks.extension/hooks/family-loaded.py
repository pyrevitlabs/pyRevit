# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "doc": str(__eventargs__.Document),
        "family_name": str(__eventargs__.FamilyName),
        "family_path": str(__eventargs__.FamilyPath),
        "family_id": str(__eventargs__.NewFamilyId),
        "original_family_id": str(__eventargs__.OriginalFamilyId),
        "status": str(__eventargs__.Status),
    },
    log_doc_access=True
)