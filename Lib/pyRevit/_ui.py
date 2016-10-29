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
                    TAB_POSTFIX, PANEL_POSTFIX
from .logger import logger
from .ui import _PyRevitUI


def _update_pyrevit_ui_item(parent_rvtui_item, component, pkg_asm_info):
    for sub_cmp in component:
        _component_creation_dict[sub_cmp.type_id](parent_rvtui_item, sub_cmp, pkg_asm_info)


def _update_pyrevit_togglebutton(parent_ribbon_panel, togglebutton, pkg_asm_info):
    # scratch pad:
    # importedscript = __import__(cmd.getscriptbasename())
    # importedscript.selfInit(__revit__, cmd.getfullscriptaddress(), ribbonitem)
    pass


def _update_pyrevit_linkbutton(parent_ribbon_panel, linkbutton, pkg_asm_info):
    pass


def _update_pyrevit_pushbutton(parent_ui_item, pushbutton, pkg_asm_info):
    if parent_ui_item.contains(pushbutton.name):
        logger.debug('Push button item already exists: {}'.format(pushbutton))
        parent_ui_item.update_button(pushbutton.name, pushbutton.unique_name, pkg_asm_info.location)
    else:
        logger.debug('Push button does not exist in panel: {}'.format(pushbutton))
        logger.debug('Creating push button: {}'.format(pushbutton))
        parent_ui_item.create_push_button(pushbutton.name, pushbutton.unique_name, pkg_asm_info.location)


def _update_pyrevit_pulldown(parent_ribbon_panel, pulldown, pkg_asm_info):
    if parent_ribbon_panel.contains(pulldown.name):
        logger.debug('Pull down already exists: {}'.format(pulldown))
        parent_ribbon_panel.update_ribbon_item(pulldown.name, pkg_asm_info.location)
    else:
        logger.debug('Pull down does not exist in panel: {}'.format(pulldown))
        logger.debug('Creating Pull down: {}'.format(pulldown))
        parent_ribbon_panel.create_pulldown_button(pulldown.name, pkg_asm_info.location)

    logger.debug('Current pull down is: {}'.format(pulldown))

    for button in pulldown:
        _component_creation_dict[button.type_id](parent_ribbon_panel.ribbon_item(pulldown.name), button, pkg_asm_info)


def _update_pyrevit_split(parent_ribbon_panel, split, pkg_asm_info):
    pass


def _update_pyrevit_splitpush(parent_ribbon_panel, splitpush, pkg_asm_info):
    pass


def _update_pyrevit_stacktwo(parent_ribbon_panel, stacktwo, pkg_asm_info):
    pass


def _update_pyrevit_stackthree(parent_ribbon_panel, stackthree, pkg_asm_info):
    pass


def _update_pyrevit_panels(parent_rvtui_tab, panel, pkg_asm_info):
    logger.debug('Updating ribbon panel: {}'.format(panel))
    if parent_rvtui_tab.contains(panel.name):
        logger.debug('Ribbon panel already exists: {}'.format(panel))
        parent_rvtui_tab.update_ribbon_panel(panel.name)
    else:
        logger.debug('Ribbon panel does not exist in tab: {}'.format(panel))
        logger.debug('Creating ribbon panel: {}'.format(panel))
        parent_rvtui_tab.create_ribbon_panel(panel.name)

    logger.debug('Current panel is: {}'.format(panel))

    _update_pyrevit_ui_item(parent_rvtui_tab.ribbon_panel(panel.name), panel, pkg_asm_info)


def _update_pyrevit_tabs(parent_rvtui, tab, pkg_asm_info):
    # updates/creates tab
    # A package might contain many tabs. Some tabs might not temporarily include any commands
    # So a ui tab is create only if the tab includes commands
    logger.debug('Processing tab: {}'.format(tab))
    #  Level 1: Tabs -----------------------------------------------------------------------------------------------
    if tab.has_commands():
        logger.debug('Tabs has command: {}'.format(tab))
        logger.debug('Updating ribbon tab: {}'.format(tab))
        if parent_rvtui.contains(tab.name):
            logger.debug('Ribbon tab already exists: {}'.format(tab))
            parent_rvtui.update_ribbon_tab(tab.name)
        else:
            logger.debug('Ribbon tab does not exist in current ui: {}'.format(tab))
            logger.debug('Creating ribbon tab: {}'.format(tab))
            parent_rvtui.create_ribbon_tab(tab.name)

        logger.debug('Current tab is: {}'.format(tab))

        _update_pyrevit_ui_item(parent_rvtui.ribbon_tab(tab.name), tab, pkg_asm_info)

    else:
        logger.debug('Tab {} does not have any commands. Skipping.'.format(tab.name))
    logger.debug('Updated ui: {}'.format(tab))


_component_creation_dict = {TAB_POSTFIX: _update_pyrevit_tabs,
                            PANEL_POSTFIX: _update_pyrevit_panels,
                            PULLDOWN_BUTTON_POSTFIX: _update_pyrevit_pulldown,
                            SPLIT_BUTTON_POSTFIX: _update_pyrevit_split,
                            SPLITPUSH_BUTTON_POSTFIX: _update_pyrevit_splitpush,
                            STACKTWO_BUTTON_POSTFIX: _update_pyrevit_stacktwo,
                            STACKTHREE_BUTTON_POSTFIX: _update_pyrevit_stackthree,
                            PUSH_BUTTON_POSTFIX: _update_pyrevit_pushbutton,
                            TOGGLE_BUTTON_POSTFIX: _update_pyrevit_togglebutton,
                            LINK_BUTTON_POSTFIX: _update_pyrevit_linkbutton,
                            }


def _update_pyrevit_ui(parsed_pkg, pkg_asm_info):
    """Updates/Creates pyRevit ui for the given package and provided assembly dll address.
    This functions has been kept outside the _PyRevitUI class since it'll only be used
    at pyRevit startup and reloading, and more importantly it needs a properly created dll assembly.
    See pyRevit.session.load() for requesting load/reload of the pyRevit package.
    """
    logger.debug('Updating ui: {}'.format(parsed_pkg))
    current_ui = _PyRevitUI()
    _update_pyrevit_ui_item(current_ui, parsed_pkg, pkg_asm_info)

    # current_ui.tab(tab) now includes updated or new ribbon_tabs.
    # so cleanup all the remaining existing tabs that are not available anymore.
    # fixme current_ui.cleanup_orphaned_ui_items(parsed_pkg)
