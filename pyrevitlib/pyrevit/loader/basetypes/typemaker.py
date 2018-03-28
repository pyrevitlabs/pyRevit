from pyrevit.coreutils import create_type
from pyrevit.coreutils.logger import get_logger

import pyrevit.extensions as exts

from pyrevit.loader.basetypes import CMD_AVAIL_TYPE, CMD_AVAIL_TYPE_NAME
from pyrevit.loader.basetypes.pythontypemaker import create_python_types
from pyrevit.loader.basetypes.csharptypemaker import create_csharp_types
from pyrevit.loader.basetypes.dynamobimtypemaker import create_dyno_types


logger = get_logger(__name__)


# public base class maker function ---------------------------------------------
def make_cmd_types(extension, cmd_component, module_builder=None):
    """

    Args:
        extension:
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):
        module_builder:

    Returns:

    """
    # make command interface type for the given command
    try:
        if cmd_component.script_language == exts.PYTHON_LANG:
            logger.debug('Command is python: {}'.format(cmd_component))
            try:
                create_python_types(extension, cmd_component, module_builder)
            except Exception as cmd_exec_err:
                logger.error('Error creating python types for: {} | {}'
                             .format(cmd_component, cmd_exec_err))

        elif cmd_component.script_language == exts.CSHARP_LANG:
            logger.debug('Command is C#: {}'.format(cmd_component))
            try:
                create_csharp_types(extension, cmd_component, module_builder)
            except Exception as cmd_compile_err:
                logger.error('Error compiling C# types for: {} | {}'
                             .format(cmd_component, cmd_compile_err))
        elif cmd_component.script_language == exts.DYNAMO_LANG:
            logger.debug('Command is DynamoBIM: {}'.format(cmd_component))
            try:
                create_dyno_types(extension, cmd_component, module_builder)
            except Exception as cmd_compile_err:
                logger.error('Error compiling DynamoBIM types for: {} | {}'
                             .format(cmd_component, cmd_compile_err))
    except Exception as createtype_err:
        logger.error('Error creating appropriate executor for: {} | {}'
                     .format(cmd_component, createtype_err))


def make_shared_types(module_builder=None):
    create_type(module_builder, CMD_AVAIL_TYPE, CMD_AVAIL_TYPE_NAME, [])
