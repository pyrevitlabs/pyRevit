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
PyRevitUI class and other auxiliary classes (e.g. PyRevitRibbonTab) do not understand _basecomponents and need raw
information about the components they need to create or update. update_revit_ui() will read the necessary info from
_basecomponents items and ask PyRevitUI to create or update the ui.

The rationale is that _basecomponents classes expect a folder for each component and that's why they're internal to
pyRevit.session. update_revit_ui() uses the functionality provided by PyRevitUI, however, PyRevitUI is also accessible
to user scripts (This helps scripts to be able to undate their own associated button (or other button) icons, title,
or other misc info.)

And because user script don't create components based on bundled folder (e.g. foldername.pushbutton) the PyRevitUI
interface doesn't need to understand that. Its main purpose is to capture the current state of ui and create or update
components as requested through its methods.
"""

from .config import SCRIPT_FILE_FORMAT
from .logger import logger
from .exceptions import PyRevitUIError

# dotnet imports
import clr
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPIUI')
from System import *
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

# revit api imports
from Autodesk.Revit.UI import PulldownButtonData

try:
    clr.AddReference('AdWindows')
    from Autodesk.Windows import ComponentManager
except Exception as err:
    logger.critical('Can not establish ui module. Error importing AdWindow.dll')
    raise err


class ButtonIcons:
    def __init__(self, file_address):
        uri = Uri(file_address)

        self.smallBitmap = BitmapImage()
        self.smallBitmap.BeginInit()
        self.smallBitmap.UriSource = uri
        self.smallBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.smallBitmap.DecodePixelHeight = 16
        self.smallBitmap.DecodePixelWidth = 16
        self.smallBitmap.EndInit()

        self.mediumBitmap = BitmapImage()
        self.mediumBitmap.BeginInit()
        self.mediumBitmap.UriSource = uri
        self.mediumBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.mediumBitmap.DecodePixelHeight = 24
        self.mediumBitmap.DecodePixelWidth = 24
        self.mediumBitmap.EndInit()

        self.largeBitmap = BitmapImage()
        self.largeBitmap.BeginInit()
        self.largeBitmap.UriSource = uri
        self.largeBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.largeBitmap.EndInit()


# todo
class PyRevitRibbonGroupItem(object):
    def __init__(self):
        pass

    @classmethod
    def from_component(cls, item):
        pass

    @classmethod
    def from_ribbon_item(cls, ribbon_item):
        pass

    def _make_tooltip(self):
        tooltip = self.item.doc_string
        tooltip += '\n\nScript Name:\n{0}'.format(self.item.name + ' ' + SCRIPT_FILE_FORMAT)
        tooltip += '\n\nAuthor:\n{0}'.format(self.item.author)
        return tooltip

    def contains(self, button):
        # todo
        pass

    def update_button(self, button, pkg_asm_location):
        # todo
        pass

    def create_button(self, button, pkg_asm_location):
        # todo
        pass

    def cleanup_orphaned_buttons(self):
        # todo
        pass


# todo
class PyRevitRibbonPanel(object):
    def __init__(self):
        # todo
        pass

    def contains(self, item):
        #todo
        pass

    def ribbon_item(self, item):
        pass

    def update_ribbon_item(self, item, pkg_asm_location):
        # todo
        pass

    # todo create and add to existing tabs
    def create_ribbon_item(self, item, pkg_asm_location):
        # todo
        pass

    def cleanup_orphaned_ribbon_items(self):
        # todo
        pass


# todo
class PyRevitRibbonTab(object):
    def __init__(self, tab_name):
        self.name = tab_name
        self.is_dirty = True

    @classmethod
    def from_data(cls, tab_name):
        return cls(tab_name)

    @classmethod
    def from_ribbon_tab(cls, ribbon_tab):
        return cls(ribbon_tab.Title)

    def contains(self, panel):
        #todo
        pass

    def ribbon_panel(self, panel):
        pass

    def update_ribbon_panel(self, panel):
        # todo
        pass

    # todo create and add to existing tabs
    def create_ribbon_panel(self, panel):
        # todo
        pass

    def cleanup_orphaned_ribbon_panels(self):
        # todo
        pass


# todo
class PyRevitUI(object):
    def __init__(self):
        """Captures the existing ui state and elements at creation."""
        self.current_ribbon_tabs = {}

        # Revit does not have any method to get a list of current tabs.
        # Getting a list of current tabs using adwindows.dll methods
        # Iterating over tabs since ComponentManager.Ribbon.Tabs.FindTab(tab.name) does not return invisible tabs
        for exiting_tab in ComponentManager.Ribbon.Tabs:
            # todo how to handle previously deactivated tabs?
            if exiting_tab.IsVisible:
                # feeding self.current_ribbon_tabs with an instance of PyRevitRibbonTab for each existing tab
                # PyRevitRibbonTab will find its existing panels internally
                self.current_ribbon_tabs[exiting_tab.Title] = PyRevitRibbonTab.from_ribbon_tab(exiting_tab)

    def contains(self, tab_name):
        """Checks the existing ui for given tab_name. Returns True if already exists."""
        return tab_name in self.current_ribbon_tabs.keys()

    def ribbon_tab(self, tab_name):
        """Returns an instance of PyRevitRibbonTab for existing tab matching tab_name"""
        try:
            return self.current_ribbon_tabs[tab_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve tab: {}'.format(tab_name))

    def create_ribbon_tab(self, tab_name):
        """Create revit ribbon tab from tab_name.
        Returns an instance of PyRevitRibbonTab for the created tab."""
        try:
            __revit__.CreateRibbonTab(tab_name)
            new_tab = PyRevitRibbonTab.from_data(tab_name)
            self.current_ribbon_tabs[tab_name] = new_tab
            return new_tab
        except Exception as err:
            logger.debug('Can not create tab: {} | Revit Error: {}'.format(tab_name, err))

    def cleanup_orphaned_ribbon_tabs(self, pkg):
        """Removes all tabs that do not exist in the given package."""
        # for tab in pkg:
        #     if tab.name not in self.current_ribbon_tabs.keys():
        #         self.current_ribbon_tabs[tab.name].deactivate()


def update_revit_ui(parsed_pkg, pkg_asm_info):
    """Updates/Creates pyRevit ui for the given package and provided assembly dll address.
    This functions has been kept outside the PyRevitUI class since it'll only be used
    at pyRevit startup and reloading, and more importantly it needs a properly created dll assembly.
    See pyRevit.session.load() for requesting load/reload of the pyRevit package.
    """

    # Collect exising ui elements and update/create
    logger.debug('Updating ui: {}'.format(parsed_pkg))
    logger.debug('Capturing exiting ui state...')
    current_ui = PyRevitUI()

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
                current_ui.ribbon_tab(tab.name).update()
            else:
                logger.debug('Ribbon tab does not exist in current ui: {}'.format(tab))
                logger.debug('Creating ribbon tab: {}'.format(tab))
                current_ui.create_ribbon_tab(tab.name)

            logger.debug('Current tab is: {}'.format(tab))
            current_tab = current_ui.ribbon_tab(tab.name)
            # Level 2: Panels (under tabs) -----------------------------------------------------------------------------
            # for panel in tab:
            #     if not current_tab.contains(panel):
            #         current_tab.create_ribbon_panel(panel)
            #
            #     current_panel = current_tab.ribbon_panel(panel)
            #     # Level 3: Ribbon items (simple push buttons or more complex button groups) ----------------------------
            #     for item in panel:
            #         if current_panel.contains(item):
            #             # update the ribbon_item that are single buttons (e.g. PushButton) or
            #             # updates the icon for ribbon_items that are groups of buttons  (e.g. PullDownButton)
            #             current_panel.update_ribbon_item(item)
            #
            #             # then update/create the sub items if any
            #             # Level 4: Ribbon items that include other push buttons (e.g. PullDownButton) ------------------
            #             if item.is_group():
            #                 for button in item:
            #                     if current_panel.ribbon_item(item).contains(button):
            #                         current_panel.ribbon_item(item).update_button(button)
            #                     else:
            #                         current_panel.ribbon_item(item).create_button(button)
            #
            #                 # current_ui.ribbon_item(item) now includes updated or new buttons.
            #                 # so cleanup all the remaining existing buttons that are not in this package anymore.
            #                 current_panel.ribbon_item(item).cleanup_orphaned_buttons()
            #         else:
            #             current_panel.create_ribbon_item(item)
            #
            #     # current_ui.panel(panel) now includes updated or new ribbon_items.
            #     # so cleanup all the remaining existing items that are not in this package anymore.
            #     current_panel.cleanup_orphaned_ribbon_items()
        #
        #     # current_ui.tab(tab) now includes updated or new ribbon_panels.
        #     # so cleanup all the remaining existing panels that are not in this package anymore.
        #     current_tab.cleanup_orphaned_ribbon_panels()
        # else:
        #     logger.debug('Tab {} does not have any commands. Skipping.'.format(tab.name))
        logger.debug('Updated ui: {}'.format(tab))

    # # current_ui.tab(tab) now includes updated or new ribbon_tabs.
    # # so cleanup all the remaining existing tabs that are not available anymore.
    # current_ui.cleanup_orphaned_ribbon_tabs(parsed_pkg)
