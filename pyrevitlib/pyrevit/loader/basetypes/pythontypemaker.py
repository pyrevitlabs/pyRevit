from pyrevit.coreutils import create_type, create_ext_command_attrs, \
                              join_strings
from pyrevit.coreutils.logger import get_logger

from pyrevit.loader.basetypes import CMD_EXECUTOR_TYPE
from pyrevit.loader.basetypes import CMD_AVAIL_TYPE, CMD_AVAIL_TYPE_SELECTION,\
    CMD_AVAIL_TYPE_CATEGORY

from pyrevit.userconfig import user_config

import pyrevit.plugins.extpackages as extpkgs


logger = get_logger(__name__)


def _is_rocketmode_compat(ext_name):
    # pyRevitCore is rocket-mode compatible
    # this line is needed since pyRevitCore does not have an extension
    # definition in extensions/extensions.json
    if ext_name == 'pyRevitCore':
        return True

    try:
        ext_pkg = extpkgs.get_ext_package_by_name(ext_name)
        if ext_pkg:
            return ext_pkg.rocket_mode
        else:
            logger.debug('Extension package is not defined: {}'
                         .format(ext_name))
    except Exception as ext_check_err:
        logger.error('Error checking rocket-mode compatibility '
                     'for extension: {} | {}'.format(ext_name, ext_check_err))

    # assume not-compatible if not set
    return False


def _make_python_avail_type(module_builder, cmd_component):
    """

    Args:
        module_builder:
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):

    Returns:

    """

    context_str = cmd_component.cmd_context.lower()

    if context_str == 'selection':
        create_type(module_builder, CMD_AVAIL_TYPE_SELECTION,
                    cmd_component.unique_avail_name, [],
                    cmd_component.cmd_context)

    elif context_str == 'zerodoc':
        create_type(module_builder, CMD_AVAIL_TYPE,
                    cmd_component.unique_avail_name, [])

    else:
        create_type(module_builder, CMD_AVAIL_TYPE_CATEGORY,
                    cmd_component.unique_avail_name, [],
                    cmd_component.cmd_context)

    return cmd_component.unique_avail_name


def _make_python_types(extension, module_builder, cmd_component):
    """

    Args:
        module_builder:
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):

    Returns:

    """
    logger.debug('Creating executor type for: {}'.format(cmd_component))

    # by default, core uses a clean engine for each command execution
    use_clean_engine = True
    # use_clean_engine will be set to false only when:
    # core is in rocket-mode
    #   AND extension is rocket-mode compatible
    #       AND the command is not asking for a clean engine
    if user_config.core.rocketmode \
        and _is_rocketmode_compat(extension.name) \
            and not cmd_component.requires_clean_engine:
                use_clean_engine = False

    logger.debug('{} uses clean engine: {}'.format(cmd_component.name,
                                                   use_clean_engine))

    logger.debug('{} requires Fullframe engine: {}'
                 .format(cmd_component.name,
                         cmd_component.requires_fullframe_engine))

    create_type(module_builder, CMD_EXECUTOR_TYPE, cmd_component.unique_name,
                create_ext_command_attrs(),
                cmd_component.get_full_script_address(),
                cmd_component.get_full_config_script_address(),
                join_strings(cmd_component.get_search_paths()),
                cmd_component.name,
                cmd_component.bundle_name,
                extension.name,
                cmd_component.unique_name,
                int(use_clean_engine),
                int(cmd_component.requires_fullframe_engine))

    logger.debug('Successfully created executor type for: {}'
                 .format(cmd_component))
    cmd_component.class_name = cmd_component.unique_name

    # create command availability class for this command
    if cmd_component.cmd_context:
        try:
            logger.debug('Creating availability type for: {}'
                         .format(cmd_component))
            cmd_component.avail_class_name = \
                _make_python_avail_type(module_builder, cmd_component)
            logger.debug('Successfully created availability type for: {}'
                         .format(cmd_component))
        except Exception as cmd_avail_err:
            cmd_component.avail_class_name = None
            logger.error('Error creating availability type: {} | {}'
                         .format(cmd_component, cmd_avail_err))


def create_python_types(extension, cmd_component, module_builder=None):
    if module_builder:
        _make_python_types(extension, module_builder, cmd_component)
    else:
        cmd_component.class_name = cmd_component.unique_name
        if cmd_component.cmd_context:
            cmd_component.avail_class_name = cmd_component.unique_avail_name
