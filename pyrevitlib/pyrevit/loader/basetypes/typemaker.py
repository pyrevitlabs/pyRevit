"""Prepare and compile script types."""
from pyrevit import coreutils
from pyrevit.coreutils import logger

import pyrevit.extensions as exts

from pyrevit.loader.basetypes import CMD_EXECUTOR_TYPE
from pyrevit.loader.basetypes import CMD_AVAIL_TYPE, CMD_AVAIL_TYPE_NAME
from pyrevit.loader.basetypes import CMD_AVAIL_TYPE_SELECTION
from pyrevit.loader.basetypes import CMD_AVAIL_TYPE_EXTENDED
from pyrevit.loader.basetypes import pythontypemaker
from pyrevit.loader.basetypes import invoketypemaker


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


# generic type maker functions ------------------------------------------------
def create_avail_type(module_builder, cmd_component):
    # create command availability class for this command
    if cmd_component.cmd_context:
        try:
            mlogger.debug('Creating availability type for: %s', cmd_component)

            context_str = cmd_component.cmd_context.lower()

            if context_str == exts.CTX_SELETION:
                coreutils.create_type(
                    module_builder,
                    CMD_AVAIL_TYPE_SELECTION,
                    cmd_component.unique_avail_name,
                    [],
                    cmd_component.cmd_context
                    )

            elif context_str in exts.CTX_ZERODOC:
                coreutils.create_type(
                    module_builder,
                    CMD_AVAIL_TYPE,
                    cmd_component.unique_avail_name,
                    [])

            else:
                coreutils.create_type(
                    module_builder,
                    CMD_AVAIL_TYPE_EXTENDED,
                    cmd_component.unique_avail_name,
                    [],
                    cmd_component.cmd_context
                    )

            cmd_component.avail_class_name = \
                cmd_component.unique_avail_name
            mlogger.debug('Successfully created availability type for: %s',
                          cmd_component)
        except Exception as cmd_avail_err:
            cmd_component.avail_class_name = None
            mlogger.error('Error creating availability type: %s | %s',
                          cmd_component, cmd_avail_err)


def create_executor_type(extension, module_builder, cmd_component): #pylint: disable=W0613
    mlogger.debug('Creating executor type for: %s', cmd_component)

    coreutils.create_type(
        module_builder,
        CMD_EXECUTOR_TYPE,
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
        0,
        0)

    mlogger.debug('Successfully created executor type for: %s', cmd_component)


def create_types(extension, cmd_component, module_builder=None):
    mlogger.debug('Command language is: %s', cmd_component.script_language)

    if module_builder:
        ### create the executor types
        ## first highly custom button types
        # if invoke
        if cmd_component.type_id == exts.INVOKE_BUTTON_POSTFIX:
            invoketypemaker.create_executor_type(
                extension,
                module_builder,
                cmd_component
                )
        # if link
        elif cmd_component.type_id == exts.LINK_BUTTON_POSTFIX:
            # link buttons don't need types
            mlogger.debug('Skipped creating executor type for: %s',
                          cmd_component)
        ## now language based button types
        # if python
        elif cmd_component.script_language == exts.PYTHON_LANG:
            pythontypemaker.create_executor_type(
                extension,
                module_builder,
                cmd_component
                )
        # if anything else
        else:
            create_executor_type(
                extension,
                module_builder,
                cmd_component
                )

        # set the name of the created type
        cmd_component.class_name = cmd_component.unique_name

        # create availability types if necessary
        create_avail_type(module_builder, cmd_component)

    else:
        cmd_component.class_name = cmd_component.unique_name
        if cmd_component.cmd_context:
            cmd_component.avail_class_name = cmd_component.unique_avail_name


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
        create_types(extension, cmd_component, module_builder)
    except Exception as createtype_err:
        mlogger.error('Error creating appropriate executor for: %s | %s',
                      cmd_component, createtype_err)


def make_shared_types(module_builder=None):
    # creates the default availability type in module
    coreutils.create_type(
        module_builder,
        CMD_AVAIL_TYPE,
        CMD_AVAIL_TYPE_NAME,
        []
        )
