from pyrevit.coreutils import create_type
from pyrevit.coreutils.logger import get_logger

from pyrevit.extensions import PYTHON_LANG, CSHARP_LANG

from pyrevit.loader.basetypes import CMD_AVAIL_TYPE, CMD_AVAIL_TYPE_NAME
from pyrevit.loader.basetypes.pythontypemaker import create_python_types
from pyrevit.loader.basetypes.csharptypemaker import create_csharp_types


logger = get_logger(__name__)


# public base class maker function -------------------------------------------------------------------------------------
def make_cmd_types(module_builder, cmd_component):
    """

    Args:
        module_builder:
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):

    Returns:

    """
    # make command interface type for the given command
    try:
        if cmd_component.script_language == PYTHON_LANG:
            logger.debug('Command is python: {}'.format(cmd_component))
            try:
                create_python_types(module_builder, cmd_component)
            except Exception as cmd_exec_err:
                logger.error('Error creating python types for: {} | {}'.format(cmd_component, cmd_exec_err))

        elif cmd_component.script_language == CSHARP_LANG:
            logger.debug('Command is C#: {}'.format(cmd_component))
            try:
                create_csharp_types(module_builder, cmd_component)
            except Exception as cmd_compile_err:
                logger.error('Error compiling C# types for: {} | {}'.format(cmd_component, cmd_compile_err))
    except:
        logger.error('Can not determine script language for: {}'.format(cmd_component))


def make_shared_types(module_builder):
    create_type(module_builder, CMD_AVAIL_TYPE, CMD_AVAIL_TYPE_NAME, [])
