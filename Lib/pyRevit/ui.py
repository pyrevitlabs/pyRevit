""" Module name: ui.py
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
This is the public module that makes internal UI wrappers accessible to the user.
"""

from .config import SCRIPT_FILE_FORMAT, ICON_SMALL_SIZE, ICON_MEDIUM_SIZE, ICON_LARGE_SIZE
from .logger import logger
from .exceptions import PyRevitUIError

# dotnet imports
import clr
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPIUI')
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

# revit api imports
from Autodesk.Revit.UI import PulldownButtonData, PushButtonData
from Autodesk.Revit.Exceptions import ArgumentException

try:
    clr.AddReference('AdWindows')
    from Autodesk.Windows import ComponentManager
except Exception as err:
    logger.critical('Can not establish ui module. Error importing AdWindow.dll')
    raise err


class _ButtonIcons:
    def __init__(self, file_address):
        uri = Uri(file_address)

        self.smallBitmap = BitmapImage()
        self.smallBitmap.BeginInit()
        self.smallBitmap.UriSource = uri
        self.smallBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.smallBitmap.DecodePixelHeight = ICON_SMALL_SIZE
        self.smallBitmap.DecodePixelWidth = ICON_SMALL_SIZE
        self.smallBitmap.EndInit()

        self.mediumBitmap = BitmapImage()
        self.mediumBitmap.BeginInit()
        self.mediumBitmap.UriSource = uri
        self.mediumBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.mediumBitmap.DecodePixelHeight = ICON_MEDIUM_SIZE
        self.mediumBitmap.DecodePixelWidth = ICON_MEDIUM_SIZE
        self.mediumBitmap.EndInit()

        self.largeBitmap = BitmapImage()
        self.largeBitmap.BeginInit()
        self.largeBitmap.UriSource = uri
        self.largeBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.mediumBitmap.DecodePixelHeight = ICON_LARGE_SIZE
        self.mediumBitmap.DecodePixelWidth = ICON_LARGE_SIZE
        self.largeBitmap.EndInit()


class _PyRevitRibbonGroupItem:
    def __init__(self, item_name):
        self.name = item_name
        self.ribbon_item_ctrl = None

        self.current_sub_items = {}

    @classmethod
    def from_data(cls, group_item_name):
        return cls(group_item_name)

    @classmethod
    def from_ribbon_item(cls, ribbon_item):
        group_item = cls(ribbon_item.Name)
        group_item.ribbon_item_ctrl = ribbon_item
        return group_item

    def _make_tooltip(self):
        tooltip = self.item.doc_string
        tooltip += '\n\nScript Name:\n{0}'.format(self.item.name + ' ' + SCRIPT_FILE_FORMAT)
        tooltip += '\n\nAuthor:\n{0}'.format(self.item.author)
        return tooltip

    def contains(self, button):
        # fixme
        pass

    def update_button(self, button_name, button_class_name, pkg_asm_location):
        # fixme
        pass

    def create_push_button(self, button_name, button_class_name, pkg_asm_location):
        # fixme complete this
        button_data = PushButtonData(button_class_name, button_name, pkg_asm_location, button_class_name)
        ribbon_button = self.ribbon_item_ctrl.AddPushButton(button_data)

    def cleanup_orphaned_buttons(self):
        # fixme
        pass


class _PyRevitRibbonPanel:
    def __init__(self, panel_name):
        self.name = panel_name
        self.ribbon_panel_ctrl = None

        self.current_ribbon_items = {}

    @classmethod
    def from_data(cls, panel_name):
        return cls(panel_name)

    @classmethod
    def from_ribbon_panel(cls, ribbon_panel):
        panel = cls(ribbon_panel.Name)
        panel.ribbon_panel_ctrl = ribbon_panel

        # getting a list of existing panels under this tab
        for ribbon_item in ribbon_panel.GetItems():
            # fixme how to handle previously deactivated items?
            if ribbon_item.Visible:
                # feeding current_ribbon_items with an instance of _PyRevitRibbonGroupItem for existing group items
                # _PyRevitRibbonPanel will find its existing ribbon items internally
                panel.current_ribbon_items[ribbon_item.Name] = _PyRevitRibbonGroupItem.from_ribbon_item(ribbon_item)

        return panel

    def contains(self, item_name):
        """Checks the existing panel for given item_name. Returns True if already exists."""
        return item_name in self.current_ribbon_items.keys()

    def ribbon_item(self, item_name):
        """Returns an instance of _PyRevitRibbonItem for existing panel matching panel_name"""
        try:
            return self.current_ribbon_items[item_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve panel item.')

    def update_ribbon_item(self, item_name, pkg_asm_location):
        try:
            exiting_item = self.current_ribbon_items[item_name]
            exiting_item.ribbon_item_ctrl.Visible = True
            exiting_item.ribbon_item_ctrl.Enabled = True
        except KeyError:
            raise PyRevitUIError('Can not update panel.')

    def create_pulldown_button(self, item_name, pkg_asm_location):
        """Create revit ribbon item from item info.
        Returns an instance of _PyRevitRibbonGroupItem for the created item."""
        try:
            # creating pull down button
            ribbon_push_button = self.ribbon_panel_ctrl.AddItem(PulldownButtonData(item_name, item_name))
            # creating _PyRevitRibbonGroupItem object and assign Revits PushButton object to controller
            new_push_button= _PyRevitRibbonGroupItem.from_data(item_name)
            new_push_button.ribbon_item_ctrl = ribbon_push_button
            # add new tab to list of current tabs
            self.current_ribbon_items[item_name] = new_push_button
        except Exception as err:
            raise PyRevitUIError('Can not create PushButton: {}'.format(err))

    def cleanup_orphaned_ribbon_items(self):
        # fixme
        pass


class _PyRevitRibbonTab:
    def __init__(self, tab_name):
        self.name = tab_name
        self.ribbon_tab_ctrl = None

        self.current_ribbon_panels = {}

    @classmethod
    def from_data(cls, tab_name):
        return cls(tab_name)

    @classmethod
    def from_ribbon_tab(cls, existing_ribbon_tab):
        tab = cls(existing_ribbon_tab.Title)
        tab.ribbon_tab_ctrl = existing_ribbon_tab

        # getting a list of existing panels under this tab
        try:
            existing_ribbon_panel_list = __revit__.GetRibbonPanels(existing_ribbon_tab.Title)
            if existing_ribbon_panel_list:
                for panel in existing_ribbon_panel_list:
                    # fixme how to handle previously deactivated panels?
                    if panel.Visible:
                        # feeding current_ribbon_panels with an instance of _PyRevitRibbonPanel for existing panels
                        # _PyRevitRibbonPanel will find its existing ribbon items internally
                        tab.current_ribbon_panels[panel.Name] = _PyRevitRibbonPanel.from_ribbon_panel(panel)
        except ArgumentException:
            raise PyRevitUIError('Can not get panels for this tab: {}'.format(existing_ribbon_tab))

        return tab

    def contains(self, panel_name):
        """Checks the existing tab for given panel_name. Returns True if already exists."""
        return panel_name in self.current_ribbon_panels.keys()

    def ribbon_panel(self, panel_name):
        """Returns an instance of _PyRevitRibbonPanel for existing panel matching panel_name"""
        try:
            return self.current_ribbon_panels[panel_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve panel.')

    def update_ribbon_panel(self, panel_name):
        try:
            exiting_panel = self.current_ribbon_panels[panel_name]
            # exiting_panel.ribbon_panel_ctrl.Name = panel_name
            exiting_panel.ribbon_panel_ctrl.Visible = True
            exiting_panel.ribbon_panel_ctrl.Enabled = True
        except KeyError:
            raise PyRevitUIError('Can not update panel.')

    def create_ribbon_panel(self, panel_name):
        """Create revit ribbon panel_name from panel_name.
        Returns an instance of _PyRevitRibbonPanel for the created tab."""
        try:
            # creating panel in tab
            ribbon_panel = __revit__.CreateRibbonPanel(self.name, panel_name)
            # creating _PyRevitRibbonPanel object and assign Revits ribbon panel object to controller
            new_panel = _PyRevitRibbonPanel.from_data(panel_name)
            new_panel.ribbon_panel_ctrl = ribbon_panel
            # add new tab to list of current tabs
            self.current_ribbon_panels[panel_name] = new_panel
        except Exception as err:
            raise PyRevitUIError('Can not create panel: {}'.format(err))

    def cleanup_orphaned_ribbon_panels(self, tab):
        """Removes all panels that do not exist in the given tab."""
        # fixme cleanup panels
        for existing_panel_name, existing_panel in self.current_ribbon_panels.items():
            pass


class _PyRevitUI:
    def __init__(self):
        """Captures the existing ui state and elements at creation."""
        self.current_ribbon_tabs = {}

        # Revit does not have any method to get a list of current tabs.
        # Getting a list of current tabs using adwindows.dll methods
        # Iterating over tabs since ComponentManager.Ribbon.Tabs.FindTab(tab.name) does not return invisible tabs
        for exiting_tab in ComponentManager.Ribbon.Tabs:
            # fixme how to handle previously deactivated tabs?
            if exiting_tab.IsVisible:
                # feeding self.current_ribbon_tabs with an instance of _PyRevitRibbonTab for each existing tab
                # _PyRevitRibbonTab will find its existing panels internally
                try:
                    self.current_ribbon_tabs[exiting_tab.Title] = _PyRevitRibbonTab.from_ribbon_tab(exiting_tab)
                except PyRevitUIError:
                    continue

    def contains(self, tab_name):
        """Checks the existing ui for given tab_name. Returns True if already exists."""
        return tab_name in self.current_ribbon_tabs.keys()

    def ribbon_tab(self, tab_name):
        """Returns an instance of _PyRevitRibbonTab for existing tab matching tab_name"""
        try:
            return self.current_ribbon_tabs[tab_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve tab.')

    def update_ribbon_tab(self, tab_name):
        try:
            exiting_tab = self.current_ribbon_tabs[tab_name]
            # exiting_tab.ribbon_tab_ctrl.Title = tab_name
            exiting_tab.ribbon_tab_ctrl.IsVisible = True
            exiting_tab.ribbon_tab_ctrl.IsEnabled = True
        except KeyError:
            raise PyRevitUIError('Can not update tab.')

    def create_ribbon_tab(self, tab_name):
        """Create revit ribbon tab from tab_name.
        Returns an instance of _PyRevitRibbonTab for the created tab."""
        try:
            # creating tab in Revit ui
            __revit__.CreateRibbonTab(tab_name)
            # creating _PyRevitRibbonTab object
            new_tab = _PyRevitRibbonTab.from_data(tab_name)
            # __revit__.CreateRibbonTab() does not return the created tab object.
            # so find the tab object in exiting ui and assign to new_tab controller.
            for exiting_tab in ComponentManager.Ribbon.Tabs:
                if exiting_tab.Title == new_tab.name:
                    new_tab.ribbon_tab_ctrl = exiting_tab
            # add new tab to list of current tabs
            self.current_ribbon_tabs[tab_name] = new_tab
        except Exception as err:
            raise PyRevitUIError('Can not create tab: {}'.format(err))

    def cleanup_orphaned_ui_items(self, pkg):
        """Removes all tabs that do not exist in the given package."""
        # fixme cleanup tabs
        for existing_tab_name, existing_tab in self.current_ribbon_tabs.items():
            pass


def get_current_ui():
    """Revit UI Wrapper class for interacting with current pyRevit UI.
    Returned class provides min required functionality for user interaction
    Example:
        current_ui = pyRevit.session.current_ui()
        this_script = pyRevit.session.get_this_command()
        current_ui.update_button_icon(this_script, new_icon)
    """
    return _PyRevitUI()
