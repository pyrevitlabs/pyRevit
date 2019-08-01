"""Prepare and compile python script types."""
from pyrevit import coreutils
from pyrevit.coreutils import logger
from pyrevit.loader import basetypes
from pyrevit.userconfig import user_config
import pyrevit.extensions.extpackages as extpkgs


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


def _is_rocketmode_compat(ext_name):
    # pyRevitCore is rocket-mode compatible
    # this line is needed since pyRevitCore does not have an extension
    # definition in extensions/extensions.json
    if ext_name == 'pyRevitCore':
        return True

    try:
        ext_pkg = extpkgs.get_ext_package_by_name(ext_name)
        if ext_pkg:
            return ext_pkg.rocket_mode_compatible
        else:
            mlogger.debug('Extension package is not defined: %s', ext_name)
    except Exception as ext_check_err:
        mlogger.error('Error checking rocket-mode compatibility '
                      'for extension: %s | %s', ext_name, ext_check_err)

    # assume not-compatible if not set
    return False


def create_executor_type(extension, module_builder, cmd_component):
    """

    Args:
        module_builder:
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):

    Returns:

    """
    mlogger.debug('Creating executor type for: %s', cmd_component)

    # by default, core uses a clean engine for each command execution
    use_clean_engine = True
    # use_clean_engine will be set to false only when:
    # core is in rocket-mode
    #   AND extension is rocket-mode compatible
    #       AND the command is not asking for a clean engine
    if user_config.core.get_option('rocketmode', False) \
            and _is_rocketmode_compat(extension.name) \
            and not cmd_component.requires_clean_engine:
        use_clean_engine = False

    mlogger.debug('%s uses clean engine: %s',
                  cmd_component.name, use_clean_engine)

    mlogger.debug('%s requires Fullframe engine: %s',
                  cmd_component.name, cmd_component.requires_fullframe_engine)

    coreutils.create_type(
        module_builder,
        basetypes.CMD_EXECUTOR_TYPE,
        cmd_component.unique_name,
        coreutils.create_ext_command_attrs(),
        cmd_component.get_full_script_address(),
        cmd_component.get_full_config_script_address(),
        coreutils.join_strings(cmd_component.get_search_paths()),
        cmd_component.get_help_url(),
        cmd_component.name,
        cmd_component.bundle_name,
        extension.name,
        cmd_component.unique_name,
        int(use_clean_engine),
        int(cmd_component.requires_fullframe_engine)
        )

    mlogger.debug('Successfully created executor type for: %s', cmd_component)
    cmd_component.class_name = cmd_component.unique_name
