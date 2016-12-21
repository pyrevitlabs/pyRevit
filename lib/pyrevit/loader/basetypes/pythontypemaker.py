from pyrevit.coreutils import create_type, create_ext_command_attrs, join_strings
from pyrevit.coreutils.logger import get_logger

from pyrevit.loader.basetypes import CMD_EXECUTOR_TYPE, CMD_AVAIL_TYPE_SELECTION, CMD_AVAIL_TYPE_CATEGORY


logger = get_logger(__name__)


def _create_python_avail_type(module_builder, cmd_component):
    """

    Args:
        module_builder:
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):

    Returns:

    """
    if cmd_component.cmd_context == 'Selection':
        create_type(module_builder, CMD_AVAIL_TYPE_SELECTION,
                    cmd_component.unique_avail_name, [], cmd_component.cmd_context)
    else:
        create_type(module_builder, CMD_AVAIL_TYPE_CATEGORY,
                    cmd_component.unique_avail_name, [], cmd_component.cmd_context)

    return cmd_component.unique_avail_name


def create_python_types(module_builder, cmd_component):
    """

    Args:
        module_builder:
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):

    Returns:

    """
    logger.debug('Creating executor type for: {}'.format(cmd_component))

    create_type(module_builder, CMD_EXECUTOR_TYPE, cmd_component.unique_name,
                create_ext_command_attrs(),
                cmd_component.get_full_script_address(),
                cmd_component.get_full_config_script_address(),
                join_strings(cmd_component.get_search_paths()),
                cmd_component.name)

    logger.debug('Successfully created executor type for: {}'.format(cmd_component))
    cmd_component.class_name = cmd_component.unique_name

    # create command availability class for this command
    if cmd_component.cmd_context:
        try:
            logger.debug('Creating availability type for: {}'.format(cmd_component))
            cmd_component.avail_class_name = _create_python_avail_type(module_builder, cmd_component)
            logger.debug('Successfully created availability type for: {}'.format(cmd_component))
        except Exception as cmd_avail_err:
            cmd_component.avail_class_name = None
            logger.error('Error creating availability type: {} | {}'.format(cmd_component, cmd_avail_err))
