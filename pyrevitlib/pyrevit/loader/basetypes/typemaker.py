"""Prepare and compile script types."""
from pyrevit.coreutils import create_type, create_ext_command_attrs, \
                              join_strings
from pyrevit.coreutils.logger import get_logger

import pyrevit.extensions as exts

from pyrevit.loader.basetypes import CMD_EXECUTOR_TYPE
from pyrevit.loader.basetypes import CMD_AVAIL_TYPE, CMD_AVAIL_TYPE_NAME
from pyrevit.loader.basetypes.pythontypemaker import create_python_types
from pyrevit.loader.basetypes.invoketypemaker import create_invoke_types


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


# generic type maker functions ------------------------------------------------
def _make_types(extension, module_builder, cmd_component): #pylint: disable=W0613
    mlogger.debug('Creating executor type for: %s', cmd_component)

    create_type(module_builder,
                CMD_EXECUTOR_TYPE,
                cmd_component.unique_name or '',
                create_ext_command_attrs(),
                cmd_component.get_full_script_address() or '',
                cmd_component.get_full_config_script_address() or '',
                join_strings(cmd_component.get_search_paths() or []),
                cmd_component.get_help_url() or '',
                cmd_component.name or '',
                cmd_component.bundle_name or '',
                extension.name or '',
                cmd_component.unique_name or '',
                0,
                0)

    mlogger.debug('Successfully created executor type for: %s', cmd_component)
    cmd_component.class_name = cmd_component.unique_name


def create_types(extension, cmd_component, module_builder=None):
    if module_builder:
        _make_types(extension, module_builder, cmd_component)
    else:
        cmd_component.class_name = cmd_component.unique_name


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
        # cpython, ironpython
        if cmd_component.script_language == exts.PYTHON_LANG:
            mlogger.debug('Command is python: %s', cmd_component)
            try:
                create_python_types(extension, cmd_component, module_builder)
            except Exception as cmd_exec_err:
                mlogger.error('Error creating python types for: %s | %s',
                              cmd_component, cmd_exec_err)

        # c#
        elif cmd_component.script_language == exts.CSHARP_LANG:
            mlogger.debug('Command is C#: %s', cmd_component)
            try:
                create_types(extension, cmd_component, module_builder)
            except Exception as cmd_compile_err:
                mlogger.error('Error compiling C# types for: %s | %s',
                              cmd_component, cmd_compile_err)

        # visual basic
        elif cmd_component.script_language == exts.VB_LANG:
            mlogger.debug('Command is Visua Basic: %s', cmd_component)
            try:
                create_types(extension, cmd_component, module_builder)
            except Exception as cmd_compile_err:
                mlogger.error('Error compiling Visua Basic types for: %s | %s',
                              cmd_component, cmd_compile_err)

        # ruby
        elif cmd_component.script_language == exts.RUBY_LANG:
            mlogger.debug('Command is Ruby: %s', cmd_component)
            try:
                create_types(extension, cmd_component, module_builder)
            except Exception as cmd_compile_err:
                mlogger.error('Error compiling Ruby types for: %s | %s',
                              cmd_component, cmd_compile_err)

        # dynamo
        elif cmd_component.script_language == exts.DYNAMO_LANG:
            mlogger.debug('Command is DynamoBIM: %s', cmd_component)
            try:
                create_types(extension, cmd_component, module_builder)
            except Exception as cmd_compile_err:
                mlogger.error('Error compiling DynamoBIM types for: %s | %s',
                              cmd_component, cmd_compile_err)

        # grasshopper
        elif cmd_component.script_language == exts.GRASSHOPPER_LANG:
            mlogger.debug('Command is Grasshopper script: %s', cmd_component)
            try:
                create_types(extension, cmd_component, module_builder)
            except Exception as cmd_compile_err:
                mlogger.error('Error compiling Grasshopper types for: %s | %s',
                              cmd_component, cmd_compile_err)

        # invoke button
        elif cmd_component.type_id == exts.INVOKE_BUTTON_POSTFIX:
            mlogger.debug('Command is Invoke button: %s', cmd_component)
            try:
                create_invoke_types(extension, cmd_component, module_builder)
            except Exception as cmd_compile_err:
                mlogger.error('Error compiling Invoke types for: %s | %s',
                              cmd_component, cmd_compile_err)

    except Exception as createtype_err:
        mlogger.error('Error creating appropriate executor for: %s | %s',
                      cmd_component, createtype_err)


def make_shared_types(module_builder=None):
    create_type(module_builder, CMD_AVAIL_TYPE, CMD_AVAIL_TYPE_NAME, [])
