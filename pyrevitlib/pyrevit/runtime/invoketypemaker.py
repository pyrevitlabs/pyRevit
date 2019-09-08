"""Prepare and compile direct invoke script types."""
from pyrevit import coreutils
from pyrevit.coreutils import logger

from pyrevit.runtime import bundletypemaker


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


def create_executor_type(extension, module_builder, cmd_component):
    # create argument to pass on to the executor for invoke commands
    target_assm_command_class = ''
    target_assm = cmd_component.get_target_assembly(required=True)
    target_class = cmd_component.command_class
    if target_assm and not target_class:
        # RevitPythonShell.dll
        target_assm_command_class = target_assm
    elif target_assm and target_class:
        # RevitPythonShell.dll::IronPythonConsoleCommand
        target_assm_command_class = '{}::{}'.format(target_assm, target_class)

    cmd_component.arguments = [target_assm_command_class]
    bundletypemaker.create_executor_type(
        extension,
        module_builder,
        cmd_component
        )
