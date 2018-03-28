from pyrevit.coreutils import create_type, create_ext_command_attrs
from pyrevit.coreutils.logger import get_logger

from pyrevit.loader.basetypes import DYNOCMD_EXECUTOR_TYPE

import pyrevit.extensions as exts
import pyrevit.plugins.extpackages as extpkgs


logger = get_logger(__name__)


def _determine_ui_display(cmd_component):
    return False


def _make_dyno_types(extension, module_builder, cmd_component):
    logger.debug('Creating executor type for: {}'.format(cmd_component))

    create_type(module_builder, DYNOCMD_EXECUTOR_TYPE,
                cmd_component.unique_name,
                create_ext_command_attrs(),
                cmd_component.get_full_script_address(),
                int(_determine_ui_display(cmd_component)))

    logger.debug('Successfully created executor type for: {}'
                 .format(cmd_component))
    cmd_component.class_name = cmd_component.unique_name


def create_dyno_types(extension, cmd_component, module_builder=None):
    if module_builder:
        _make_dyno_types(extension, module_builder, cmd_component)
    else:
        cmd_component.class_name = cmd_component.unique_name
