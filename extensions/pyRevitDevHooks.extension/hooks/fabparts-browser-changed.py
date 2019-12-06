# pylint: skip-file
import hooks_logger as hl
hl.log_hook(__file__,
    {
        "cancellable?": str(__eventargs__.Cancellable),
        "solutions_num": str(__eventargs__.NumberOfSolutions),
        "operation": str(__eventargs__.Operation),
        "service_id": str(__eventargs__.ServiceId),
        "all_parts_count": str(__eventargs__.GetAllSolutionsPartsTypeCounts()),
        "parts_count": str(__eventargs__.GetCurrentSolutionPartTypeIds()),
        "parts_ids": str(__eventargs__.GetFabricationPartTypeIds()),
        "filtered_parts_count": str(__eventargs__.GetFilteredSolutionsPartsTypeCounts()),
        "required_parts_ids": str(__eventargs__.GetRequiredFabricationPartTypeIds()),
    },
    log_doc_access=True
)