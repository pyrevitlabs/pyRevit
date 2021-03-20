# pylint: skip-file
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, script
import hooks_logger as hl

args = EXEC_PARAMS.event_args

hl.log_hook(__file__,
    {
        "cancellable?": str(args.Cancellable),
        "solutions_num": str(args.NumberOfSolutions),
        "operation": str(args.Operation),
        "service_id": str(args.ServiceId),
        "all_parts_count": str(args.GetAllSolutionsPartsTypeCounts()),
        "parts_count": str(args.GetCurrentSolutionPartTypeIds()),
        "parts_ids": str(args.GetFabricationPartTypeIds()),
        "filtered_parts_count": str(args.GetFilteredSolutionsPartsTypeCounts()),
        "required_parts_ids": str(args.GetRequiredFabricationPartTypeIds()),
    },
    log_doc_access=True
)