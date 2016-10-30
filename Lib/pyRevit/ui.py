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
from Autodesk.Revit.UI import PushButtonData, PulldownButtonData, SplitButtonData
from Autodesk.Revit.Exceptions import ArgumentException

try:
    clr.AddReference('AdWindows')
    from Autodesk.Windows import ComponentManager
except Exception as err:
    logger.critical('Can not establish ui module. Error importing AdWindow.dll')
    raise err

#fixme create classes for each corresponding ribbon item type
# scratch pad:
# for splitpush buttons use .IsSynchronizedWithCurrentItem
# item state .Enabled
# stack items .AddStackedItems


class _ButtonIcons:
    def __init__(self, file_address):
        logger.debug('Creating uri from: {}'.format(file_address))
        uri = Uri(file_address)

        logger.debug('Creating {0}x{0} bitmap from: {1}'.format(ICON_SMALL_SIZE, file_address))
        self.smallBitmap = BitmapImage()
        self.smallBitmap.BeginInit()
        self.smallBitmap.UriSource = uri
        self.smallBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.smallBitmap.DecodePixelHeight = ICON_SMALL_SIZE
        self.smallBitmap.DecodePixelWidth = ICON_SMALL_SIZE
        self.smallBitmap.EndInit()

        logger.debug('Creating {0}x{0} bitmap from: {1}'.format(ICON_MEDIUM_SIZE, file_address))
        self.mediumBitmap = BitmapImage()
        self.mediumBitmap.BeginInit()
        self.mediumBitmap.UriSource = uri
        self.mediumBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.mediumBitmap.DecodePixelHeight = ICON_MEDIUM_SIZE
        self.mediumBitmap.DecodePixelWidth = ICON_MEDIUM_SIZE
        self.mediumBitmap.EndInit()

        logger.debug('Creating {0}x{0} bitmap from: {1}'.format(ICON_LARGE_SIZE, file_address))
        self.largeBitmap = BitmapImage()
        self.largeBitmap.BeginInit()
        self.largeBitmap.UriSource = uri
        self.largeBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.mediumBitmap.DecodePixelHeight = ICON_LARGE_SIZE
        self.mediumBitmap.DecodePixelWidth = ICON_LARGE_SIZE
        self.largeBitmap.EndInit()


class _PyRevitRibbonButton:
    def __init__(self, ribbon_button):
        self.name = ribbon_button.Name
        self.ribbon_button_ctrl = ribbon_button

    def activate(self):
        self.ribbon_button_ctrl.Enabled = True
        self.ribbon_button_ctrl.Visible = True

    def set_icon(self, icon_file):
        try:
            button_icon = _ButtonIcons(icon_file)
        except Exception as err:
            raise PyRevitUIError('Can not create icon from given icon file.')

        self.ribbon_button_ctrl.Image = button_icon.smallBitmap
        self.ribbon_button_ctrl.LargeImage = button_icon.mediumBitmap

    def get_icon(self):
        if self.ribbon_button_ctrl.Image:
            return self.ribbon_button_ctrl.Image.UriSource.LocalPath
        elif self.ribbon_button_ctrl.LargeImage:
            return self.ribbon_button_ctrl.LargeImage.UriSource.LocalPath

        return None

    def set_tooltip(self, tooltip):
        self.ribbon_button_ctrl.ToolTip = tooltip

    def set_tooltip_ext(self, tooltip_ext):
        self.ribbon_button_ctrl.LongDescription = tooltip_ext


class _PyRevitRibbonGroupItem:
    def __init__(self, ribbon_item):
        self.name = ribbon_item.Name
        self.ribbon_item_ctrl = ribbon_item

        self.current_sub_items = {}

        # fixme handle loading current buttons

    def __iter__(self):
        return iter(self.current_sub_items.values())

    def contains(self, button_name):
        """Checks the existing item group for given item_name. Returns True if already exists."""
        return button_name in self.current_sub_items.keys()

    def button(self, button_name):
        """Returns an instance of _PyRevitRibbonItem for existing panel matching panel_name"""
        try:
            return self.current_sub_items[button_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve button.')

    def activate(self):
        self.ribbon_item_ctrl.Enabled = True
        self.ribbon_item_ctrl.Visible = True

    def set_icon(self, icon_file):
        try:
            button_icon = _ButtonIcons(icon_file)
        except Exception as err:
            logger.debug('Can not create icon from given file: {} | {}'.format(icon_file, self))
            return

        self.ribbon_item_ctrl.Image = button_icon.smallBitmap
        self.ribbon_item_ctrl.LargeImage = button_icon.largeBitmap

    def get_icon(self):
        if self.ribbon_item_ctrl.Image:
            return self.ribbon_item_ctrl.Image.UriSource.LocalPath
        elif self.ribbon_item_ctrl.LargeImage:
            return self.ribbon_item_ctrl.LargeImage.UriSource.LocalPath

        return None

    def create_push_button(self, button_name, asm_location, class_name,
                           button_icon_path, tooltip, tooltip_ext='',
                           update_if_exists=False, use_parent_icon=True):
        # fixme handle exiting buttons
        button_data = PushButtonData(class_name, button_name, asm_location, class_name)
        ribbon_button = self.ribbon_item_ctrl.AddPushButton(button_data)
        logger.debug('Creating button_icon_path for PushButton {} from file: {}'.format(button_name, button_icon_path))
        new_button = _PyRevitRibbonButton(ribbon_button)
        try:
            new_button.set_icon(button_icon_path)
        except PyRevitUIError as err:
            logger.debug('Error adding button_icon_path for {}'.format(button_name))
            if use_parent_icon:
                logger.debug('Using icon from parent ui item.')
                button_icon = self.get_icon()
                if button_icon:
                    new_button.set_icon(button_icon)
                else:
                    logger.debug('Can not get icon file path from parent ui element.')

        self.current_sub_items[button_name] = new_button


class _PyRevitRibbonPanel:
    def __init__(self, ribbon_panel):
        self.name = ribbon_panel.Name
        self.current_ribbon_items = {}
        self.ribbon_panel_ctrl = ribbon_panel

        # getting a list of existing panels under this tab
        for revit_ribbon_item in ribbon_panel.GetItems():
            # fixme how to handle previously deactivated items?
            if revit_ribbon_item.Visible:
                # feeding current_ribbon_items with an instance of _PyRevitRibbonGroupItem for existing group items
                # _PyRevitRibbonPanel will find its existing ribbon items internally
                self.current_ribbon_items[revit_ribbon_item.Name] = _PyRevitRibbonGroupItem(revit_ribbon_item)

    def __iter__(self):
        return iter(self.current_ribbon_items.values())

    def contains(self, item_name):
        """Checks the existing panel for given item_name. Returns True if already exists."""
        return item_name in self.current_ribbon_items.keys()

    def ribbon_item(self, item_name):
        """Returns an instance of _PyRevitRibbonItem for existing panel matching panel_name"""
        try:
            return self.current_ribbon_items[item_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve panel item.')

    def create_pulldown_button(self, item_name, item_icon, update_if_exists=False):
        if self.contains(item_name):
            if update_if_exists:
                exiting_item = self.current_ribbon_items[item_name]
                exiting_item.activate()
                exiting_item.set_icon(item_icon)
            else:
                raise PyRevitUIError('PullDownButton already exits and update is not allowed: {}'.format(item_name))
        else:
            logger.debug('Panel does not include this PullDownButton. Creating: {}'.format(item_name))
            try:
                # creating pull down button
                logger.debug('Creating PullDownButton: {} in RibbonPanel: {}'.format(item_name, self.name))
                revit_push_button = self.ribbon_panel_ctrl.AddItem(PulldownButtonData(item_name, item_name))
                logger.debug('Creating icon for PullDownButton {} from file: {}'.format(item_name, item_icon))

                # creating _PyRevitRibbonGroupItem object and assign Revits PushButton object to controller
                new_push_button = _PyRevitRibbonGroupItem(revit_push_button)

                # add icon
                new_push_button.set_icon(item_icon)

                # add new pulldown to list of current ribbon items
                self.current_ribbon_items[item_name] = new_push_button
            except Exception as err:
                raise PyRevitUIError('Can not create PullDownButton: {}'.format(err))

    def create_split_button(self, item_name, item_icon, update_if_exists=False):
        if self.contains(item_name):
            if update_if_exists:
                exiting_item = self.current_ribbon_items[item_name]
                exiting_item.activate()
                exiting_item.set_icon(item_icon)
            else:
                raise PyRevitUIError('SplitButton already exits and update is not allowed: {}'.format(item_name))
        else:
            logger.debug('Panel does not include this SplitButton. Creating: {}'.format(item_name))
            try:
                # creating pull down button
                logger.debug('Creating SplitButton: {} in RibbonPanel: {}'.format(item_name, self.name))
                revit_split_button = self.ribbon_panel_ctrl.AddItem(SplitButtonData(item_name, item_name))
                logger.debug('Creating icon for SplitButton {} from file: {}'.format(item_name, item_icon))

                # creating _PyRevitRibbonGroupItem object and assign Revits PushButton object to controller
                new_split_button = _PyRevitRibbonGroupItem(revit_split_button)

                # adding icons
                new_split_button.set_icon(item_icon)

                # add new pulldown to list of current ribbon items
                self.current_ribbon_items[item_name] = new_split_button
            except Exception as err:
                raise PyRevitUIError('Can not create SplitButton: {}'.format(err))

    def create_splitpush_button(self, item_name, item_icon, update_if_exists=False):
        if self.contains(item_name):
            if update_if_exists:
                exiting_item = self.current_ribbon_items[item_name]
                exiting_item.activate()
                exiting_item.set_icon(item_icon)
            else:
                raise PyRevitUIError('SplitButton already exits and update is not allowed: {}'.format(item_name))
        else:
            logger.debug('Panel does not include this SplitButton. Creating: {}'.format(item_name))
            try:
                # creating pull down button
                logger.debug('Creating SplitButton: {} in RibbonPanel: {}'.format(item_name, self.name))
                revit_splitpush_button = self.ribbon_panel_ctrl.AddItem(SplitButtonData(item_name, item_name))
                logger.debug('Creating icon for SplitButton {} from file: {}'.format(item_name, item_icon))

                # creating _PyRevitRibbonGroupItem object and assign Revits PushButton object to controller
                new_splitpush_button = _PyRevitRibbonGroupItem(revit_splitpush_button)

                # adding icons
                new_splitpush_button.set_icon(item_icon)

                # add new pulldown to list of current ribbon items
                self.current_ribbon_items[item_name] = new_splitpush_button
            except Exception as err:
                raise PyRevitUIError('Can not create SplitButton: {}'.format(err))


class _PyRevitRibbonTab:
    def __init__(self, existing_ribbon_tab):
        self.name = existing_ribbon_tab.Title
        self.current_ribbon_panels = {}
        self.ribbon_tab_ctrl = existing_ribbon_tab

        # getting a list of existing panels under this tab
        try:
            existing_ribbon_panel_list = __revit__.GetRibbonPanels(existing_ribbon_tab.Title)
            if existing_ribbon_panel_list:
                for revit_ui_panel in existing_ribbon_panel_list:
                    # fixme how to handle previously deactivated panels?
                    if revit_ui_panel.Visible:
                        # feeding current_ribbon_panels with an instance of _PyRevitRibbonPanel for existing panels
                        # _PyRevitRibbonPanel will find its existing ribbon items internally
                        self.current_ribbon_panels[revit_ui_panel.Name] = _PyRevitRibbonPanel(revit_ui_panel)
        except ArgumentException:
            raise PyRevitUIError('Can not get panels for this tab: {}'.format(existing_ribbon_tab))

    def __iter__(self):
        return iter(self.current_ribbon_panels.values())

    def contains(self, panel_name):
        """Checks the existing tab for given panel_name. Returns True if already exists."""
        return panel_name in self.current_ribbon_panels.keys()

    def ribbon_panel(self, panel_name):
        """Returns an instance of _PyRevitRibbonPanel for existing panel matching panel_name"""
        try:
            return self.current_ribbon_panels[panel_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve panel.')

    def create_ribbon_panel(self, panel_name, update_if_exists=False):
        """Create ribbon panel (RevitUI.RibbonPanel) from panel_name."""
        if self.contains(panel_name):
            if update_if_exists:
                exiting_panel = self.current_ribbon_panels[panel_name]
                # exiting_panel.ribbon_panel_ctrl.Name = panel_name
                exiting_panel.ribbon_panel_ctrl.Visible = True
                exiting_panel.ribbon_panel_ctrl.Enabled = True
            else:
                raise PyRevitUIError('RibbonPanel already exits and update is not allowed: {}'.format(panel_name))
        else:
            try:
                # creating panel in tab
                ribbon_panel = __revit__.CreateRibbonPanel(self.name, panel_name)

                # creating _PyRevitRibbonPanel object and assign Revits ribbon panel object to controller
                new_panel = _PyRevitRibbonPanel(ribbon_panel)

                # add new tab to list of current tabs
                self.current_ribbon_panels[panel_name] = new_panel
            except Exception as err:
                raise PyRevitUIError('Can not create panel: {}'.format(err))


class _PyRevitUI:
    def __init__(self):
        """Captures the existing ui state and elements at creation."""
        self.current_ribbon_tabs = {}

        # Revit does not have any method to get a list of current tabs.
        # Getting a list of current tabs using adwindows.dll methods
        # Iterating over tabs since ComponentManager.Ribbon.Tabs.FindTab(tab.name) does not return invisible tabs
        for revit_ui_tab in ComponentManager.Ribbon.Tabs:
            # fixme how to handle previously deactivated tabs?
            if revit_ui_tab.IsVisible:
                # feeding self.current_ribbon_tabs with an instance of _PyRevitRibbonTab for each existing tab
                # _PyRevitRibbonTab will find its existing panels internally
                try:
                    self.current_ribbon_tabs[revit_ui_tab.Title] = _PyRevitRibbonTab(revit_ui_tab)
                except PyRevitUIError:
                    logger.debug('Could not add tab to exiting tabs: {}'.format(revit_ui_tab.Title))

    def __iter__(self):
        return iter(self.current_ribbon_tabs.values())

    def contains(self, tab_name):
        """Checks the existing ui for given tab_name. Returns True if already exists."""
        return tab_name in self.current_ribbon_tabs.keys()

    def ribbon_tab(self, tab_name):
        """Returns an instance of _PyRevitRibbonTab for existing tab matching tab_name"""
        try:
            return self.current_ribbon_tabs[tab_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve tab.')

    def create_ribbon_tab(self, tab_name, update_if_exists=False):
        if self.contains(tab_name):
            if update_if_exists:
                exiting_tab = self.current_ribbon_tabs[tab_name]
                # exiting_tab.ribbon_tab_ctrl.Title = tab_name
                exiting_tab.ribbon_tab_ctrl.IsVisible = True
                exiting_tab.ribbon_tab_ctrl.IsEnabled = True
            else:
                raise PyRevitUIError('RibbonTab already exits and update is not allowed: {}'.format(tab_name))
        else:
            try:
                # creating tab in Revit ui
                __revit__.CreateRibbonTab(tab_name)
                # __revit__.CreateRibbonTab() does not return the created tab object.
                # so find the tab object in exiting ui and assign to new_tab controller.
                revit_tab_ctrl = None
                for exiting_tab in ComponentManager.Ribbon.Tabs:
                    if exiting_tab.Title == tab_name:
                        revit_tab_ctrl = exiting_tab

                # creating _PyRevitRibbonTab object
                new_tab = _PyRevitRibbonTab(revit_tab_ctrl)

                # add new tab to list of current tabs
                self.current_ribbon_tabs[tab_name] = new_tab
            except Exception as err:
                raise PyRevitUIError('Can not create tab: {}'.format(err))


def get_current_ui():
    """Revit UI Wrapper class for interacting with current pyRevit UI.
    Returned class provides min required functionality for user interaction
    Example:
        current_ui = pyRevit.session.current_ui()
        this_script = pyRevit.session.get_this_command()
        current_ui.update_button_icon(this_script, new_icon)
    """
    return _PyRevitUI()
