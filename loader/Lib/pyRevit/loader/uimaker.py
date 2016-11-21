""" Module name = _ui.py
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE


~~~
Description:
pyRevit library has 4 main modules for handling parsing, assembly creation, ui, and caching.
This is the module responsible for creating ui for the commands using the data collected by _parse modules and the
dll assembly created by the _assemblies module.

All these four modules are private and handled by pyRevit.session
These modules do not import each other and mainly use base modules (.config, .logger, .exceptions, .output, .utils)
All these four modules can understand the component tree. (_basecomponents module)
 _parser parses the folders and creates a tree of components provided by _basecomponents
 _assemblies make a dll from the tree.
 _ui creates the ui using the information provided by the tree.
 _cache will save and restore the tree to increase loading performance.

update_revit_ui() is the only ui function that understands the _basecomponents since this is private to a session.
_PyRevitUI class and other auxiliary classes (e.g. _PyRevitRibbonTab) do not understand _basecomponents and need raw
information about the components they need to create or update. update_revit_ui() will read the necessary info from
_basecomponents items and ask _PyRevitUI to create or update the ui.

The rationale is that _basecomponents classes expect a folder for each component and that's why they're internal to
pyRevit.session. update_revit_ui() uses the functionality provided by _PyRevitUI, however, _PyRevitUI is also accessible
to user scripts (This helps scripts to be able to undate their own associated button (or other button) icons, title,
or other misc info.)

And because user script don't create components based on bundled folder (e.g. foldername.pushbutton) the _PyRevitUI
interface doesn't need to understand that. Its main purpose is to capture the current state of ui and create or update
components as requested through its methods.
"""

import imp

from ..logger import get_logger
from ..config import LINK_BUTTON_POSTFIX, PUSH_BUTTON_POSTFIX, TOGGLE_BUTTON_POSTFIX, PULLDOWN_BUTTON_POSTFIX,\
                     STACKTHREE_BUTTON_POSTFIX, STACKTWO_BUTTON_POSTFIX, SPLIT_BUTTON_POSTFIX,\
                     SPLITPUSH_BUTTON_POSTFIX, TAB_POSTFIX, PANEL_POSTFIX, SCRIPT_FILE_FORMAT, SEPARATOR_IDENTIFIER,\
                     SLIDEOUT_IDENTIFIER, CONFIG_SCRIPT_TITLE_POSTFIX, SMART_BUTTON_POSTFIX
from ..config import HostVersion, HOST_SOFTWARE, COMMAND_NAME_PARAM
from ..ui import get_current_ui
from ..exceptions import PyRevitUIError

from System import AppDomain

logger = get_logger(__name__)


def _make_button_tooltip(button):
    tooltip = button.doc_string
    if tooltip:
        tooltip += '\n\nScript Name:\n{0}'.format(button.name + ' ' + SCRIPT_FILE_FORMAT)
        tooltip += '\n\nAuthor:\n{0}'.format(button.author)
    return tooltip


def _make_button_tooltip_ext(button, asm_name):
    return 'Class Name:\n{}\n\nAssembly Name:\n{}'.format(button.unique_name, asm_name)


def _make_ui_title(button):
    if button.has_config_script():
        return button.ui_title + ' {}'.format(CONFIG_SCRIPT_TITLE_POSTFIX)
    else:
        return button.ui_title


def _make_full_class_name(asm_name, class_name):
    if asm_name is None or class_name is None:
        return None
    else:
        return '{}.{}'.format(asm_name, class_name)


def _find_loaded_assembly(asm_name):
    for loaded_asm in AppDomain.CurrentDomain.GetAssemblies():
        if asm_name in loaded_asm.FullName:
            return loaded_asm
    return None


def _produce_ui_separator(parent_ui_item, pushbutton, pkg_asm_info):
    if not pkg_asm_info.reloading:
        logger.debug('Adding separator to: {}'.format(parent_ui_item))
        try:
            parent_ui_item.add_separator()
        except PyRevitUIError as err:
            logger.error('UI error: {}'.format(err.message))

    return None


def _produce_ui_slideout(parent_ui_item, pushbutton, pkg_asm_info):
    if not pkg_asm_info.reloading:
        logger.debug('Adding slide out to: {}'.format(parent_ui_item))
        try:
            parent_ui_item.add_slideout()
        except PyRevitUIError as err:
            logger.error('UI error: {}'.format(err.message))

    return None


def _produce_ui_smartbutton(parent_ui_item, smartbutton, pkg_asm_info):
    logger.debug('Producing smart button: {}'.format(smartbutton))
    try:
        parent_ui_item.create_push_button(smartbutton.name,
                                          pkg_asm_info.location,
                                          smartbutton.unique_name,
                                          smartbutton.icon_file,
                                          _make_button_tooltip(smartbutton),
                                          _make_button_tooltip_ext(smartbutton, pkg_asm_info.name),
                                          smartbutton.unique_avail_name,
                                          update_if_exists=True,
                                          ui_title=_make_ui_title(smartbutton))

        logger.debug('Importing smart button as module: {}'.format(smartbutton))
        # replacing COMMAND_NAME_PARAM value with button name so the init script can log under its own name
        orig_cmd_name = __builtins__[COMMAND_NAME_PARAM]
        __builtins__[COMMAND_NAME_PARAM] = smartbutton.name
        # importing smart button script as a module
        importedscript = imp.load_source(smartbutton.unique_name, smartbutton.script_file)
        # resetting COMMAND_NAME_PARAM to original
        __builtins__[COMMAND_NAME_PARAM] = orig_cmd_name
        logger.debug('Import successful: {}'.format(importedscript))
        logger.debug('Running self initializer: {}'.format(smartbutton))
        try:
            # running the smart button initializer function
            importedscript.__selfinit__(smartbutton,
                                        parent_ui_item.button(smartbutton.name),
                                        HOST_SOFTWARE)
        except Exception as button_err:
            logger.error('Error initializing smart button: {} | {}'.format(smartbutton, button_err))
        return parent_ui_item.button(smartbutton.name)
    except PyRevitUIError as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_linkbutton(parent_ui_item, linkbutton, pkg_asm_info):
    logger.debug('Producing button: {}'.format(linkbutton))
    try:
        linked_asm = _find_loaded_assembly(linkbutton.assembly)
        if not linked_asm or not linkbutton.command_class:
            return None
        parent_ui_item.create_push_button(linkbutton.name,
                                          linked_asm.Location,
                                          _make_full_class_name(linked_asm.GetName().Name, linkbutton.command_class),
                                          linkbutton.icon_file,
                                          _make_button_tooltip(linkbutton),
                                          _make_button_tooltip_ext(linkbutton, pkg_asm_info.name),
                                          linkbutton.unique_avail_name,
                                          update_if_exists=True,
                                          ui_title=_make_ui_title(linkbutton))
        return parent_ui_item.button(linkbutton.name)
    except PyRevitUIError as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_pushbutton(parent_ui_item, pushbutton, pkg_asm_info):
    logger.debug('Producing button: {}'.format(pushbutton))
    try:
        parent_ui_item.create_push_button(pushbutton.name,
                                          pkg_asm_info.location,
                                          pushbutton.unique_name,
                                          pushbutton.icon_file,
                                          _make_button_tooltip(pushbutton),
                                          _make_button_tooltip_ext(pushbutton, pkg_asm_info.name),
                                          pushbutton.unique_avail_name,
                                          update_if_exists=True,
                                          ui_title=_make_ui_title(pushbutton))
        return parent_ui_item.button(pushbutton.name)
    except PyRevitUIError as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_pulldown(parent_ribbon_panel, pulldown, pkg_asm_info):
    logger.debug('Producing pulldown button: {}'.format(pulldown))
    try:
        parent_ribbon_panel.create_pulldown_button(pulldown.name, pulldown.icon_file, update_if_exists=True)
        return parent_ribbon_panel.ribbon_item(pulldown.name)
    except PyRevitUIError as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_split(parent_ribbon_panel, split, pkg_asm_info):
    logger.debug('Producing split button: {}'.format(split))
    try:
        parent_ribbon_panel.create_split_button(split.name, split.icon_file, update_if_exists=True)
        return parent_ribbon_panel.ribbon_item(split.name)
    except PyRevitUIError as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_splitpush(parent_ribbon_panel, splitpush, pkg_asm_info):
    logger.debug('Producing splitpush button: {}'.format(splitpush))
    try:
        parent_ribbon_panel.create_splitpush_button(splitpush.name, splitpush.icon_file, update_if_exists=True)
        return parent_ribbon_panel.ribbon_item(splitpush.name)
    except PyRevitUIError as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_stacks(parent_ui_panel, stack_cmp, pkg_asm_info):
    # if sub_cmp is a stack, ask parent_ui_item to open a stack (parent_ui_item.open_stack).
    # All subsequent items will be placed under this stack.
    # Close the stack (parent_ui_item.close_stack) to finish adding items to the stack.
    try:
        parent_ui_panel.open_stack()
        logger.debug('Opened stack: {}'.format(stack_cmp.name))

        if HostVersion.is_older_than('2017'):
            _component_creation_dict[SPLIT_BUTTON_POSTFIX] = _produce_ui_pulldown
            _component_creation_dict[SPLITPUSH_BUTTON_POSTFIX] = _produce_ui_pulldown

        # capturing and logging any errors on stack item
        # (e.g when parent_ui_panel's stack is full and can not add any more items it will raise an error)
        _recursively_produce_ui_items(parent_ui_panel, stack_cmp, pkg_asm_info)

        if HostVersion.is_older_than('2017'):
            _component_creation_dict[SPLIT_BUTTON_POSTFIX] = _produce_ui_split
            _component_creation_dict[SPLITPUSH_BUTTON_POSTFIX] = _produce_ui_splitpush

        try:
            parent_ui_panel.close_stack()
            logger.debug('Closed stack: {}'.format(stack_cmp.name))
        except PyRevitUIError as err:
            logger.error('Error creating stack | {}'.format(err))

    except Exception as err:
        logger.error('Can not create stack under this parent: {} | {}'.format(parent_ui_panel, err))


def _produce_ui_panels(parent_ui_tab, panel, pkg_asm_info):
    logger.debug('Producing ribbon panel: {}'.format(panel))
    try:
        parent_ui_tab.create_ribbon_panel(panel.name, update_if_exists=True)
        return parent_ui_tab.ribbon_panel(panel.name)
    except PyRevitUIError as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_tab(parent_ui, tab, pkg_asm_info):
    logger.debug('Verifying tab: {}'.format(tab))
    if tab.has_commands():
        logger.debug('Tabs has command: {}'.format(tab))
        logger.debug('Producing ribbon tab: {}'.format(tab))
        try:
            parent_ui.create_ribbon_tab(tab.name, update_if_exists=True)
            return parent_ui.ribbon_tab(tab.name)
        except PyRevitUIError as err:
            logger.error('UI error: {}'.format(err.message))
            return None
    else:
        logger.debug('Tab does not have any commands. Skipping: {}'.format(tab.name))
        return None


_component_creation_dict = {TAB_POSTFIX: _produce_ui_tab,
                            PANEL_POSTFIX: _produce_ui_panels,
                            STACKTWO_BUTTON_POSTFIX: _produce_ui_stacks,
                            STACKTHREE_BUTTON_POSTFIX: _produce_ui_stacks,
                            PULLDOWN_BUTTON_POSTFIX: _produce_ui_pulldown,
                            SPLIT_BUTTON_POSTFIX: _produce_ui_split,
                            SPLITPUSH_BUTTON_POSTFIX: _produce_ui_splitpush,
                            PUSH_BUTTON_POSTFIX: _produce_ui_pushbutton,
                            TOGGLE_BUTTON_POSTFIX: _produce_ui_smartbutton,
                            SMART_BUTTON_POSTFIX: _produce_ui_smartbutton,
                            LINK_BUTTON_POSTFIX: _produce_ui_linkbutton,
                            SEPARATOR_IDENTIFIER: _produce_ui_separator,
                            SLIDEOUT_IDENTIFIER: _produce_ui_slideout,
                            }


def _recursively_produce_ui_items(parent_ui_item, component, pkg_asm_info):
    for sub_cmp in component:
        try:
            logger.debug('Calling create func {} for: {}'.format(_component_creation_dict[sub_cmp.type_id], sub_cmp))
            ui_item = _component_creation_dict[sub_cmp.type_id](parent_ui_item, sub_cmp, pkg_asm_info)
        except KeyError:
            logger.debug('Can not find create function for: {}'.format(sub_cmp))

        logger.debug('UI item created by create func is: {}'.format(ui_item))

        if ui_item and sub_cmp.is_container():
                _recursively_produce_ui_items(ui_item, sub_cmp, pkg_asm_info)


current_ui = get_current_ui()


def update_pyrevit_ui(parsed_pkg, pkg_asm_info):
    """Updates/Creates pyRevit ui for the given package and provided assembly dll address.
    """
    logger.debug('Creating/Updating ui for package: {}'.format(parsed_pkg))
    _recursively_produce_ui_items(current_ui, parsed_pkg, pkg_asm_info)


def cleanup_pyrevit_ui():
    untouched_items = current_ui.get_unchanged_items()
    for item in untouched_items:
        if not item.is_native():
            try:
                logger.debug('Deactivating: {}'.format(item))
                item.deactivate()
            except Exception as deact_err:
                logger.debug(deact_err)
