"""Prepare and compile python script types."""
import json
from pyrevit.coreutils import logger

import pyrevit.extensions as exts
from pyrevit.runtime import bundletypemaker


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


def create_executor_type(extension, module_builder, cmd_component):
    """

    Args:
        extension:
        module_builder:
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):

    Returns:

    """
    engine_configs = json.dumps({
        exts.MDATA_ENGINE_CLEAN: cmd_component.requires_clean_engine,
    })

    bundletypemaker.create_executor_type(
        extension,
        module_builder,
        cmd_component,
        eng_cfgs=engine_configs
        )
