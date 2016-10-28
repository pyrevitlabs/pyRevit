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

from .logger import logger
from .ui import _PyRevitUI


def _update_revit_ui(parsed_pkg, pkg_asm_info):
    """Updates/Creates pyRevit ui for the given package and provided assembly dll address.
    This functions has been kept outside the _PyRevitUI class since it'll only be used
    at pyRevit startup and reloading, and more importantly it needs a properly created dll assembly.
    See pyRevit.session.load() for requesting load/reload of the pyRevit package.
    """

    # Collect exising ui elements and update/create
    logger.debug('Updating ui: {}'.format(parsed_pkg))
    logger.debug('Capturing exiting ui state...')
    current_ui = _PyRevitUI()

    # Traverse thru the package and create necessary ui elements
    for tab in parsed_pkg:
        # creates pyrevit ribbon-panels for given tab data
        # A package might contain many tabs. Some tabs might not temporarily include any commands
        # So a ui tab is create only if the tab includes commands
        logger.debug('Processing tab: {}'.format(tab))
        #  Level 1: Tabs -----------------------------------------------------------------------------------------------
        if tab.has_commands():
            logger.debug('Tabs has command: {}'.format(tab))
            logger.debug('Updating ribbon tab: {}'.format(tab))
            if current_ui.contains(tab.name):
                logger.debug('Ribbon tab already exists: {}'.format(tab))
                current_ui.update_ribbon_tab(tab.name)
            else:
                logger.debug('Ribbon tab does not exist in current ui: {}'.format(tab))
                logger.debug('Creating ribbon tab: {}'.format(tab))
                current_ui.create_ribbon_tab(tab.name)

            logger.debug('Current tab is: {}'.format(tab))
            current_tab = current_ui.ribbon_tab(tab.name)
            # Level 2: Panels (under tabs) -----------------------------------------------------------------------------
            for panel in tab:
                logger.debug('Updating ribbon panel: {}'.format(panel))
                if current_tab.contains(panel.name):
                    logger.debug('Ribbon panel already exists: {}'.format(panel))
                    current_tab.update_ribbon_panel(panel.name)
                else:
                    logger.debug('Ribbon panel does not exist in tab: {}'.format(panel))
                    logger.debug('Creating ribbon panel: {}'.format(panel))
                    current_tab.create_ribbon_panel(panel.name)

                logger.debug('Current panel is: {}'.format(panel))
                current_panel = current_tab.ribbon_panel(panel.name)
                # Level 3: Ribbon items (simple push buttons or more complex button groups) ----------------------------
                for item in panel:
                    if item.is_group():
                        if current_panel.contains(item.name):
                            logger.debug('Ribbon item already exists: {}'.format(item))
                            current_panel.update_ribbon_item(item.name, pkg_asm_info.location)
                        else:
                            logger.debug('Ribbon item does not exist in panel: {}'.format(item))
                            logger.debug('Creating ribbon item: {}'.format(item))
                            current_panel.create_pulldown_button(item.name, pkg_asm_info.location)

                        logger.debug('Current ribbon group item is: {}'.format(item))
                        current_group_item = current_panel.ribbon_item(item.name)
                        # Level 4: Ribbon group items (simple push buttons under button groups) ------------------------
                        for sub_item in item:
                            if current_group_item.contains(sub_item.name):
                                logger.debug('Button item already exists: {}'.format(item))
                                current_group_item.update_button(item.name, item.unique_name, pkg_asm_info.location)
                            else:
                                logger.debug('Button does not exist in panel: {}'.format(item))
                                logger.debug('Creating ribbon item: {}'.format(item))
                                current_group_item.create_push_button(item.name, item.unique_name, pkg_asm_info.location)
        else:
            logger.debug('Tab {} does not have any commands. Skipping.'.format(tab.name))
        logger.debug('Updated ui: {}'.format(tab))

    # current_ui.tab(tab) now includes updated or new ribbon_tabs.
    # so cleanup all the remaining existing tabs that are not available anymore.
    current_ui.cleanup_orphaned_ui_items(parsed_pkg)
