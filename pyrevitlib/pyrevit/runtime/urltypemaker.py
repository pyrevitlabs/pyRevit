"""Prepare and compile url script types."""
from pyrevit.coreutils import logger

from pyrevit.runtime import bundletypemaker


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


def create_executor_type(extension, module_builder, cmd_component):
    cmd_component.arguments = [cmd_component.get_target_url()]
    bundletypemaker.create_executor_type(
        extension,
        module_builder,
        cmd_component
        )
