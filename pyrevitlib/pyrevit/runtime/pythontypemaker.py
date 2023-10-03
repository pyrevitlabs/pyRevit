"""Prepare and compile python script types."""
from pyrevit.coreutils import logger
from pyrevit.userconfig import user_config
import pyrevit.extensions.extpackages as extpkgs

from pyrevit import runtime
from pyrevit.runtime import bundletypemaker


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


def _does_need_clean_engine(extension, cmd_component):
    # by default, core uses a clean engine for each command execution
    use_clean_engine = True
    # use_clean_engine will be set to false only when:
    # core is in rocket-mode
    #   AND extension is rocket-mode compatible
    #       AND the command is not asking for a clean engine
    if user_config.rocket_mode \
            and _is_rocketmode_compat(extension.name) \
            and not cmd_component.requires_clean_engine:
        use_clean_engine = False

    return use_clean_engine


def create_executor_type(extension, module_builder, cmd_component):
    """Create the dotnet type for the executor.

    Args:
        extension (pyrevit.extensions.components.Extension): pyRevit extension
        module_builder (ModuleBuilder): module builder
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):
            command
    """
    cmd_component.requires_clean_engine = \
        _does_need_clean_engine(extension, cmd_component)

    engine_configs = runtime.create_ipyengine_configs(
        clean=cmd_component.requires_clean_engine,
        full_frame=cmd_component.requires_fullframe_engine,
        persistent=cmd_component.requires_persistent_engine,
    )

    bundletypemaker.create_executor_type(
        extension,
        module_builder,
        cmd_component,
        eng_cfgs=engine_configs
        )
