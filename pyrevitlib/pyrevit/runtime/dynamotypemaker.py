"""Prepare and compile python script types."""
import json
from pyrevit.coreutils import logger

import pyrevit.extensions as exts
from pyrevit.runtime import bundletypemaker


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


def create_executor_type(extension, module_builder, cmd_component):
    """Create the dotnet type for the executor.

    Args:
        extension (pyrevit.extensions.components.Extension): pyRevit extension
        module_builder (ModuleBuilder): module builder
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):
            command
    """
    engine_configs = json.dumps({
        exts.MDATA_ENGINE_CLEAN:
            cmd_component.requires_clean_engine,

        exts.MDATA_ENGINE_DYNAMO_AUTOMATE:
            cmd_component.requires_mainthread_engine,

        exts.MDATA_ENGINE_DYNAMO_PATH:
            cmd_component.dynamo_path,

        # exts.MDATA_ENGINE_DYNAMO_PATH_EXEC:
        #     cmd_component.dynamo_path_exec,

        exts.MDATA_ENGINE_DYNAMO_PATH_CHECK_EXIST:
            cmd_component.dynamo_path_check_existing,

        exts.MDATA_ENGINE_DYNAMO_FORCE_MANUAL_RUN:
            cmd_component.dynamo_force_manual_run,

        exts.MDATA_ENGINE_DYNAMO_MODEL_NODES_INFO:
            cmd_component.dynamo_model_nodes_info,
    })

    bundletypemaker.create_executor_type(
        extension,
        module_builder,
        cmd_component,
        eng_cfgs=engine_configs
        )
