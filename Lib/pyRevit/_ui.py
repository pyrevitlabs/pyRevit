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
from .config import LINK_BUTTON_POSTFIX, PUSH_BUTTON_POSTFIX, TOGGLE_BUTTON_POSTFIX, PULLDOWN_BUTTON_POSTFIX,          \
                    STACKTHREE_BUTTON_POSTFIX, STACKTWO_BUTTON_POSTFIX, SPLIT_BUTTON_POSTFIX, SPLITPUSH_BUTTON_POSTFIX,\
                    TAB_POSTFIX, PANEL_POSTFIX, SCRIPT_FILE_FORMAT
from .logger import logger
from .ui import _PyRevitUI
from .exceptions import PyRevitUIError


def _make_button_tooltip(button):
    tooltip = button.doc_string
    tooltip += '\n\nScript Name:\n{0}'.format(button.name + ' ' + SCRIPT_FILE_FORMAT)
    tooltip += '\n\nAuthor:\n{0}'.format(button.author)
    return tooltip


def _make_button_tooltip_ext(button, asm_name):
    return 'Class Name:\n{}\n\nAssembly Name:\n{}'.format(button.unique_name, asm_name)


def _produce_ui_togglebutton(parent_ribbon_panel, togglebutton, pkg_asm_info):
    # scratch pad:
    # importedscript = __import__(cmd.getscriptbasename())
    # importedscript.selfInit(__revit__, cmd.getfullscriptaddress(), ribbonitem)
    pass


def _produce_ui_linkbutton(parent_ribbon_panel, linkbutton, pkg_asm_info):
    pass


def _produce_ui_pushbutton(parent_ui_item, pushbutton, pkg_asm_info):
    logger.debug('Producing button: {}'.format(pushbutton))
    try:
        parent_ui_item.create_push_button(pushbutton.name,
                                          pkg_asm_info.location,
                                          pushbutton.unique_name,
                                          pushbutton.icon_file,
                                          _make_button_tooltip(pushbutton),
                                          _make_button_tooltip_ext(pushbutton, pkg_asm_info.name),
                                          update_if_exists=True)
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
                            PULLDOWN_BUTTON_POSTFIX: _produce_ui_pulldown,
                            SPLIT_BUTTON_POSTFIX: _produce_ui_split,
                            SPLITPUSH_BUTTON_POSTFIX: _produce_ui_splitpush,
                            PUSH_BUTTON_POSTFIX: _produce_ui_pushbutton,
                            TOGGLE_BUTTON_POSTFIX: _produce_ui_togglebutton,
                            LINK_BUTTON_POSTFIX: _produce_ui_linkbutton,
                            }


def _recursively_produce_ui_items(parent_ui_item, component, asm_info):
    for sub_cmp in component:
        # if sub_cmp is a stack, ask parent_ui_item to open a stack (parent_ui_item.open_stack).
        # All subsequent items will be placed under this stack.
        # Close the stack (parent_ui_item.close_stack) to finish adding items to the stack.
        if sub_cmp.type_id == STACKTWO_BUTTON_POSTFIX or sub_cmp.type_id == STACKTHREE_BUTTON_POSTFIX:
            try:       # making sure parent_ui_item has open_stack()
                parent_ui_item.open_stack()
                logger.debug('Opened stack: {}'.format(sub_cmp.name))
                # capturing and logging any errors on stack item
                # (e.g when parent_ui_item's stack is full and can not add any more items it will raise an error)
                try:
                    _recursively_produce_ui_items(parent_ui_item, sub_cmp, asm_info)
                except PyRevitUIError as err:
                    # fixme: implement stack count error check
                    logger.error('Stack is full | {}'.format(err))
                parent_ui_item.close_stack()
                logger.debug('Closed stack: {}'.format(sub_cmp.name))
            except Exception as err:
                logger.error('Can not create stack under this parent: {} | {}'.format(parent_ui_item, err))
                parent_ui_item.reset_stack()

        # if sub_cmp is NOT a stack, create ui item for sub_cmp and continue creating its children (if any)
        else:
            logger.debug('Calling create function {} for: {}'.format(_component_creation_dict[sub_cmp.type_id], sub_cmp))
            ui_item = _component_creation_dict[sub_cmp.type_id](parent_ui_item, sub_cmp, asm_info)
            logger.debug('UI item created by create func is: {}'.format(ui_item))
            if ui_item:
                if sub_cmp.is_container():
                    _recursively_produce_ui_items(ui_item, sub_cmp, asm_info)


def _update_pyrevit_ui(parsed_pkg, pkg_asm_info):
    """Updates/Creates pyRevit ui for the given package and provided assembly dll address.
    """
    logger.debug('Updating ui: {}'.format(parsed_pkg))
    current_ui = _PyRevitUI()
    _recursively_produce_ui_items(current_ui, parsed_pkg, pkg_asm_info)

    # current_ui.tab(tab) now includes updated or new ribbon_tabs.
    # so cleanup all the remaining existing tabs that are not available anymore.
    # fixme current_ui.cleanup_orphaned_ui_items(parsed_pkg)
