"""Prepare and compile script types."""
from pyrevit import coreutils
from pyrevit.coreutils import logger

import pyrevit.extensions as exts

from pyrevit import runtime
from pyrevit.runtime import bundletypemaker
from pyrevit.runtime import pythontypemaker
from pyrevit.runtime import dynamotypemaker
from pyrevit.runtime import invoketypemaker
from pyrevit.runtime import urltypemaker


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


def create_avail_type(extension, cmd_component, module_builder=None):
    if cmd_component.type_id == exts.LINK_BUTTON_POSTFIX:
        mlogger.debug(
            'Skipped creating availability type for: %s', cmd_component
            )
        return

    # create command availability class for this command
    mlogger.debug('Creating availability type for: %s', cmd_component)
    # set the name of the created type
    cmd_component.avail_class_name = \
            cmd_component.class_name + runtime.CMD_AVAIL_NAME_POSTFIX

    if module_builder:
        context_str = cmd_component.context.lower()

        if context_str == exts.CTX_SELETION:
            bundletypemaker.create_selection_avail_type(
                module_builder=module_builder,
                cmd_component=cmd_component
                )

        elif context_str == exts.CTX_ZERODOC:
            bundletypemaker.create_zerodoc_avail_type(
                module_builder=module_builder,
                cmd_component=cmd_component
                )

        else:
            bundletypemaker.create_extended_avail_type(
                module_builder=module_builder,
                cmd_component=cmd_component
                )

        mlogger.debug(
            'Successfully created availability type for: %s', cmd_component)


def create_exec_types(extension, cmd_component, module_builder=None):
    mlogger.debug('Command language is: %s', cmd_component.script_language)
    # set the name of the created type
    cmd_component.class_name = cmd_component.unique_name

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
        # if content
        elif cmd_component.type_id == exts.CONTENT_BUTTON_POSTFIX:
            # link buttons don't need types
            bundletypemaker.create_executor_type(
                extension,
                module_builder,
                cmd_component
                )
        # if url
        elif cmd_component.type_id == exts.URL_BUTTON_POSTFIX:
            urltypemaker.create_executor_type(
                extension,
                module_builder,
                cmd_component
                )
        ## now language based button types
        # if python
        elif cmd_component.script_language == exts.PYTHON_LANG:
            pythontypemaker.create_executor_type(
                extension,
                module_builder,
                cmd_component
                )
        # if dynamo
        elif cmd_component.script_language == exts.DYNAMO_LANG:
            dynamotypemaker.create_executor_type(
                extension,
                module_builder,
                cmd_component
                )
        # if anything else
        else:
            bundletypemaker.create_executor_type(
                extension,
                module_builder,
                cmd_component
                )


# public base class maker function ---------------------------------------------
def make_bundle_types(extension, cmd_component, module_builder=None):
    """Create the types for the bundle.

    Args:
        extension (pyrevit.extensions.components.Extension): pyRevit extension
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):
            command
        module_builder (ModuleBuilder): module builder.
    """
    # make command interface type for the given command
    try:
        create_exec_types(extension, cmd_component, module_builder)
    except Exception as createtype_err:
        mlogger.error('Error creating appropriate exec types for: %s | %s',
                      cmd_component, createtype_err)
    # create availability types if necessary
    if cmd_component.context:
        try:
            create_avail_type(extension, cmd_component, module_builder)
        except Exception as createtype_err:
            mlogger.error('Error creating appropriate avail types for: %s | %s',
                          cmd_component, createtype_err)
