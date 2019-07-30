"""Prepare and compile direct invoke script types."""
from pyrevit import coreutils
from pyrevit.coreutils import logger

from pyrevit.loader.basetypes import CMD_EXECUTOR_TYPE


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


def create_executor_type(extension, module_builder, cmd_component): #pylint: disable=W0613
    mlogger.debug('Creating executor type for: %s', cmd_component)

    target_assm_command_class = ''
    target_assm = cmd_component.get_target_assembly(required=True)
    target_class = cmd_component.command_class
    if target_assm and not target_class:
        # RevitPythonShell.dll
        target_assm_command_class = target_assm
    elif target_assm and target_class:
        # RevitPythonShell.dll::IronPythonConsoleCommand
        target_assm_command_class = '{}::{}'.format(target_assm, target_class)

    coreutils.create_type(
        module_builder,
        CMD_EXECUTOR_TYPE,
        cmd_component.unique_name,
        coreutils.create_ext_command_attrs(),
        cmd_component.get_full_script_address(),
        target_assm_command_class,
        coreutils.join_strings(cmd_component.get_search_paths()),
        cmd_component.get_help_url(),
        cmd_component.name,
        cmd_component.bundle_name,
        extension.name,
        cmd_component.unique_name,
        0,
        0
        )

    mlogger.debug('Successfully created executor type for: %s', cmd_component)
    cmd_component.class_name = cmd_component.unique_name
