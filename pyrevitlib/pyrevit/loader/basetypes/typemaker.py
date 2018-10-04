"""Prepare and compile script types."""
from pyrevit.coreutils import create_type
from pyrevit.coreutils.logger import get_logger

import pyrevit.extensions as exts

from pyrevit.loader.basetypes import CMD_AVAIL_TYPE, CMD_AVAIL_TYPE_NAME
from pyrevit.loader.basetypes.pythontypemaker import create_python_types
from pyrevit.loader.basetypes.csharptypemaker import create_csharp_types
from pyrevit.loader.basetypes.dynamobimtypemaker import create_dyno_types


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


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
            mlogger.debug('Command is python: %s', cmd_component)
            try:
                create_python_types(extension, cmd_component, module_builder)
            except Exception as cmd_exec_err:
                mlogger.error('Error creating python types for: %s | %s',
                              cmd_component, cmd_exec_err)

        elif cmd_component.script_language == exts.CSHARP_LANG:
            mlogger.debug('Command is C#: %s', cmd_component)
            try:
                create_csharp_types(extension, cmd_component, module_builder)
            except Exception as cmd_compile_err:
                mlogger.error('Error compiling C# types for: %s | %s',
                              cmd_component, cmd_compile_err)
        elif cmd_component.script_language == exts.DYNAMO_LANG:
            mlogger.debug('Command is DynamoBIM: %s', cmd_component)
            try:
                create_dyno_types(extension, cmd_component, module_builder)
            except Exception as cmd_compile_err:
                mlogger.error('Error compiling DynamoBIM types for: %s | %s',
                              cmd_component, cmd_compile_err)
    except Exception as createtype_err:
        mlogger.error('Error creating appropriate executor for: %s | %s',
                      cmd_component, createtype_err)


def make_shared_types(module_builder=None):
    create_type(module_builder, CMD_AVAIL_TYPE, CMD_AVAIL_TYPE_NAME, [])
