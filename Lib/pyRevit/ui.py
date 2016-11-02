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
from Autodesk.Revit.UI import PushButton, PulldownButton
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
# item state .Enabled
# stack items .AddStackedItems


# Helper classes and functions -----------------------------------------------------------------------------------------
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


def _set_item_icon(caller, icon_file):
    try:
        button_icon = _ButtonIcons(icon_file)
    except Exception as err:
        raise PyRevitUIError('Can not create icon from given file: {} | {}'.format(icon_file, caller))

    try:
        caller.ribbon_item_ctrl.Image = button_icon.smallBitmap
        caller.ribbon_item_ctrl.LargeImage = button_icon.largeBitmap
    except Exception as err:
        raise PyRevitUIError('Item does not have image property: {}'.format(err))


def _get_item_icon(caller):
    try:
        if caller._rvt_ui_ctrl.Image:
            return caller._rvt_ui_ctrl.Image.UriSource.LocalPath
        elif caller._rvt_ui_ctrl.LargeImage:
            return caller._rvt_ui_ctrl.LargeImage.UriSource.LocalPath
    except Exception as err:
        raise PyRevitUIError('Item does not have image property: {}'.format(err))


def _set_item_tooltip(caller, tooltip):
    try:
        caller._rvt_ui_ctrl.ToolTip = tooltip
    except Exception as err:
        raise PyRevitUIError('Item does not have tooltip property: {}'.format(err))


def _set_item_tooltip_ext(caller, tooltip_ext):
    try:
        caller._rvt_ui_ctrl.LongDescription = tooltip_ext
    except Exception as err:
        raise PyRevitUIError('Item does not have extended tooltip property: {}'.format(err))


# Superclass to all ui item classes ---------------------------------------------------------------------------------
class _GenericPyRevitUIContainer:
    def __init__(self):
        self.name = ''
        self._rvt_ui_ctrl = None
        self._sub_pyrvt_components = {}

    def __iter__(self):
        return iter(self._sub_pyrvt_components.values())

    def _get_component(self, cmp_name):
        try:
            return self._sub_pyrvt_components[cmp_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve item {} from {}'.format(cmp_name, self))

    def _add_component(self, new_component):
        self._sub_pyrvt_components[new_component.name] = new_component

    def contains(self, pyrvt_cmp_name):
        return True if pyrvt_cmp_name in self._sub_pyrvt_components.keys() else False

    def set_name(self, new_name):
        self._rvt_ui_ctrl.Name = new_name

    def get_name(self):
        return self._rvt_ui_ctrl.Name

    def activate(self):
        self._rvt_ui_ctrl.Enabled = True
        self._rvt_ui_ctrl.Visible = True

    def deactivate(self):
        self._rvt_ui_ctrl.Enabled = False
        self._rvt_ui_ctrl.Visible = False


# Classes holding existing native ui elements (These elements are native and can not be modified) ----------------------
class _RevitNativeRibbonButton(_GenericPyRevitUIContainer):
    pass


class _RevitNativeRibbonGroupItem(_GenericPyRevitUIContainer):
    pass


class _RevitNativeRibbonPanel(_GenericPyRevitUIContainer):
    def __init__(self, rvt_ribbon_panel):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = rvt_ribbon_panel.Source.Title
        self._rvt_ui_ctrl = rvt_ribbon_panel

        # getting a list of existing panels under this tab
        for revit_ribbon_item in rvt_ribbon_panel.Source.Items:
            if revit_ribbon_item.IsVisible:
                item_name = str(revit_ribbon_item.AutomationName).replace('\n', ' ')
                self._sub_pyrvt_components[item_name] = revit_ribbon_item

    ribbon_item = _GenericPyRevitUIContainer._get_component


class _RevitNativeRibbonTab(_GenericPyRevitUIContainer):
    def __init__(self, revit_ribbon_tab):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = revit_ribbon_tab.Title
        self._rvt_ui_ctrl = revit_ribbon_tab

        # getting a list of existing panels under this tab
        try:
            revit_ribbon_panels = revit_ribbon_tab.Panels
            for rvt_panel in revit_ribbon_panels:
                if rvt_panel.IsVisible:
                    self._sub_pyrvt_components[rvt_panel.Source.Title] = _RevitNativeRibbonPanel(rvt_panel)
        except Exception as err:
            raise PyRevitUIError('Can not get native panels for this native tab: {} | {}'.format(revit_ribbon_tab, err))

    ribbon_panel = _GenericPyRevitUIContainer._get_component


# Classes holding non-native ui elements -------------------------------------------------------------------------------
class _PyRevitRibbonButton(_GenericPyRevitUIContainer):

    set_icon = _set_item_icon
    get_icon = _get_item_icon
    set_tooltip = _set_item_tooltip
    set_tooltip_ext = _set_item_tooltip_ext

    def __init__(self, ribbon_button):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = ribbon_button.Name
        self._rvt_ui_ctrl = ribbon_button


class _PyRevitRibbonGroupItem(_GenericPyRevitUIContainer):

    set_icon = _set_item_icon
    get_icon = _get_item_icon
    button = _GenericPyRevitUIContainer._get_component

    def __init__(self, ribbon_item):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = ribbon_item.Name
        self._rvt_ui_ctrl = ribbon_item

        # getting a list of existing panels under this tab
        for revit_button in ribbon_item.GetItems():
            # feeding _sub_native_ribbon_items with an instance of _PyRevitRibbonButton for existing buttons
            self._add_component(_PyRevitRibbonButton(revit_button))

    def _create_item_from_data(self, ribbon_button_data):
        return self._rvt_ui_ctrl.AddPushButton(ribbon_button_data)

    def create_push_button(self, button_name, asm_location, class_name,
                           icon_path='', tooltip='', tooltip_ext='',
                           update_if_exists=False, use_parent_icon=True):
        if self.contains(button_name):
            if update_if_exists:
                exiting_item = self._get_component(button_name)
                exiting_item.activate()
                if icon_path != '':
                    exiting_item.set_icon(icon_path)
            else:
                raise PyRevitUIError('Pulldown button already exits and update is not allowed: {}'.format(button_name))
        else:
            logger.debug('Panel does not include this button. Creating: {}'.format(button_name))
            try:
                button_data = PushButtonData(class_name, button_name, asm_location, class_name)
                ribbon_button = self.self._rvt_ui_ctrl.AddPushButton(button_data)
                logger.debug('Creating icon_path for PushButton {} from file: {}'.format(button_name, icon_path))
                new_button = _PyRevitRibbonButton(ribbon_button)
            except Exception as err:
                raise PyRevitUIError('Can not create button: {}'.format(err))

            try:
                new_button.set_icon(icon_path)
            except PyRevitUIError as err:
                logger.debug('Error adding icon_path for {}'.format(button_name))
                if use_parent_icon:
                    logger.debug('Using icon from parent ui item.')
                    button_icon = self.get_icon()
                    if button_icon:
                        new_button.set_icon(button_icon)
                    else:
                        logger.debug('Can not get icon file path from parent ui element.')

            self._add_component(new_button)


class _PyRevitRibbonPanel(_GenericPyRevitUIContainer):

    ribbon_item = _GenericPyRevitUIContainer._get_component

    def __init__(self, rvt_ribbon_panel):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = rvt_ribbon_panel.Name
        self._rvt_ui_ctrl = rvt_ribbon_panel

        self.stack_mode = False

        # getting a list of existing panels under this tab
        for revit_ribbon_item in self._rvt_ui_ctrl.GetItems():
            # feeding _sub_native_ribbon_items with an instance of _PyRevitRibbonGroupItem for existing group items
            # _PyRevitRibbonPanel will find its existing ribbon items internally
            if isinstance(revit_ribbon_item, PulldownButton):
                self._add_component(_PyRevitRibbonGroupItem(revit_ribbon_item))
            elif isinstance(revit_ribbon_item, PushButton):
                self._add_component(_PyRevitRibbonButton(revit_ribbon_item))
            else:
                raise PyRevitUIError('Can not determin ribbon item type: {}'.format(revit_ribbon_item))

    def open_stack(self):
        self.stack_mode = True
        pass

    def close_stack(self):
        self.stack_mode = False
        # fixme: self._rvt_ui_ctrl.AddStackedItems()
        pass

    def create_push_button(self, button_name, asm_location, class_name,
                           icon_path='', tooltip='', tooltip_ext='',
                           update_if_exists=False, use_parent_icon=True):
        if self.contains(button_name):
            if update_if_exists:
                exiting_item = self._get_component(button_name)
                exiting_item.activate()
                if icon_path != '':
                    exiting_item.set_icon(icon_path)
            else:
                raise PyRevitUIError('Pulldown button already exits and update is not allowed: {}'.format(button_name))
        else:
            logger.debug('Panel does not include this button. Creating: {}'.format(button_name))
            try:
                button_data = PushButtonData(class_name, button_name, asm_location, class_name)
                ribbon_button = self.self._rvt_ui_ctrl.AddItem(button_data)
                logger.debug('Creating icon_path for PushButton {} from file: {}'.format(button_name, icon_path))
                new_button = _PyRevitRibbonButton(ribbon_button)
            except Exception as err:
                raise PyRevitUIError('Can not create button: {}'.format(err))

            try:
                new_button.set_icon(icon_path)
            except PyRevitUIError as err:
                logger.debug('Error adding icon_path for {}'.format(button_name))
                if use_parent_icon:
                    logger.debug('Using icon from parent ui item.')
                    button_icon = self.get_icon()
                    if button_icon:
                        new_button.set_icon(button_icon)
                    else:
                        logger.debug('Can not get icon file path from parent ui element.')

            self._add_component(new_button)

    def create_pulldown_button(self, item_name, item_icon, update_if_exists=False):
        if self.contains(item_name):
            if update_if_exists:
                exiting_item = self._get_component(item_name)
                exiting_item.activate()
                exiting_item.set_icon(item_icon)
            else:
                raise PyRevitUIError('Pulldown button already exits and update is not allowed: {}'.format(item_name))
        else:
            logger.debug('Panel does not include this Pulldown button. Creating: {}'.format(item_name))
            try:
                # creating pull down button data and asking self to add to list
                logger.debug('Creating Pulldown button: {} in {}'.format(item_name, self))
                pdbutton_data = PulldownButtonData(item_name, item_name)
                if not self.stack_mode:
                    new_push_button = self._rvt_ui_ctrl.AddItem(pdbutton_data)
                    pyrvt_pdbutton = _PyRevitRibbonGroupItem(new_push_button)
                else:
                    pyrvt_pdbutton = _PyRevitRibbonGroupItem(pdbutton_data)

                pyrvt_pdbutton.set_icon(item_icon)
                self._add_component(pyrvt_pdbutton)

            except Exception as err:
                raise PyRevitUIError('Can not create Pulldown button: {}'.format(err))

    def create_split_button(self, item_name, item_icon, update_if_exists=False):
        if self.contains(item_name):
            if update_if_exists:
                exiting_item = self._get_component(item_name)
                exiting_item.activate()
                exiting_item.set_icon(item_icon)
            else:
                raise PyRevitUIError('SplitButton already exits and update is not allowed: {}'.format(item_name))
        else:
            logger.debug('Panel does not include this SplitButton. Creating: {}'.format(item_name))
            try:
                # creating pull down button
                logger.debug('Creating SplitButton: {} in RibbonPanel: {}'.format(item_name, self.name))
                revit_split_button = self._rvt_ui_ctrl.AddItem(SplitButtonData(item_name, item_name))
                logger.debug('Creating icon for SplitButton {} from file: {}'.format(item_name, item_icon))

                # creating _PyRevitRibbonGroupItem object and assign Revits PushButton object to controller
                new_split_button = _PyRevitRibbonGroupItem(revit_split_button)
                # adding icons
                new_split_button.set_icon(item_icon)

                # add new pulldown to list of current ribbon items
                self._add_component(new_split_button)
            except Exception as err:
                raise PyRevitUIError('Can not create SplitButton: {}'.format(err))

    def create_splitpush_button(self, item_name, item_icon, update_if_exists=False):
        if self.contains(item_name):
            if update_if_exists:
                exiting_item = self._get_component(item_name)
                exiting_item.activate()
                exiting_item.set_icon(item_icon)
            else:
                raise PyRevitUIError('SplitButton already exits and update is not allowed: {}'.format(item_name))
        else:
            logger.debug('Panel does not include this SplitButton. Creating: {}'.format(item_name))
            try:
                # creating pull down button
                logger.debug('Creating SplitButton: {} in RibbonPanel: {}'.format(item_name, self.name))
                revit_splitpush_button = self._rvt_ui_ctrl.AddItem(SplitButtonData(item_name, item_name))
                revit_splitpush_button.IsSynchronizedWithCurrentItem = False
                logger.debug('Creating icon for SplitButton {} from file: {}'.format(item_name, item_icon))

                # creating _PyRevitRibbonGroupItem object and assign Revits PushButton object to controller
                new_splitpush_button = _PyRevitRibbonGroupItem(revit_splitpush_button)
                # adding icons
                new_splitpush_button.set_icon(item_icon)

                # add new pulldown to list of current ribbon items
                self._add_component(new_splitpush_button)
            except Exception as err:
                raise PyRevitUIError('Can not create SplitButton: {}'.format(err))


class _PyRevitRibbonTab(_GenericPyRevitUIContainer):

    ribbon_panel = _GenericPyRevitUIContainer._get_component

    def __init__(self, revit_ribbon_tab):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = revit_ribbon_tab.Title
        self._rvt_ui_ctrl = revit_ribbon_tab

        # getting a list of existing panels under this tab
        try:
            for revit_ui_panel in __revit__.GetRibbonPanels(self.name):
                # feeding _sub_pyrvt_ribbon_panels with an instance of _PyRevitRibbonPanel for existing panels
                # _PyRevitRibbonPanel will find its existing ribbon items internally
                new_pyrvt_panel = _PyRevitRibbonPanel(revit_ui_panel)
                self._add_component(new_pyrvt_panel)
        except:
            # if .GetRibbonPanels fails, this tab is an existing native tab
            raise PyRevitUIError('Can not get panels for this tab: {}'.format(self._rvt_ui_ctrl))

    def update_name(self, new_name):
        self._rvt_ui_ctrl.Title = new_name

    def create_ribbon_panel(self, panel_name, update_if_exists=False):
        """Create ribbon panel (RevitUI.RibbonPanel) from panel_name."""
        if self.contains(panel_name):
            if update_if_exists:
                exiting_pyrvt_panel = self._get_component(panel_name)
                exiting_pyrvt_panel.update_name(panel_name)
                exiting_pyrvt_panel.activate()
            else:
                raise PyRevitUIError('RibbonPanel already exits and update is not allowed: {}'.format(panel_name))
        else:
            try:
                # creating panel in tab
                ribbon_panel = __revit__.CreateRibbonPanel(panel_name)

                # creating _PyRevitRibbonPanel object and add new tab to list of current tabs
                self._add_component(_PyRevitRibbonPanel(ribbon_panel))

            except Exception as err:
                raise PyRevitUIError('Can not create panel: {}'.format(err))


class _PyRevitUI(_GenericPyRevitUIContainer):
    """Captures the existing ui state and elements at creation."""

    ribbon_tab = _GenericPyRevitUIContainer._get_component

    def __init__(self):
        _GenericPyRevitUIContainer.__init__(self)

        # Revit does not have any method to get a list of current tabs.
        # Getting a list of current tabs using adwindows.dll methods
        # Iterating over tabs, because ComponentManager.Ribbon.Tabs.FindTab(tab.name) does not return invisible tabs
        for revit_ui_tab in ComponentManager.Ribbon.Tabs:
            # feeding self._sub_pyrvt_ribbon_tabs with an instance of _PyRevitRibbonTab or _RevitNativeRibbonTab
            # for each existing tab. _PyRevitRibbonTab or _RevitNativeRibbonTab will find their existing panels
            try:
                new_pyrvt_tab = _PyRevitRibbonTab(revit_ui_tab)
                self._add_component(new_pyrvt_tab)
                logger.debug('Tab added to the list of tabs: {}'.format(new_pyrvt_tab.name))
            except PyRevitUIError:
                # if _PyRevitRibbonTab(revit_ui_tab) fails, Revit restricts access to its panels
                # _RevitNativeRibbonTab uses a different method to access the panels and provides minimal functionality
                # to interact with existing native ui
                new_pyrvt_tab = _RevitNativeRibbonTab(revit_ui_tab)
                self._add_component(new_pyrvt_tab)
                logger.debug('Native tab added to the list of tabs: {}'.format(new_pyrvt_tab.name))

    def create_ribbon_tab(self, tab_name, update_if_exists=False):
        if self.contains(tab_name):
            if update_if_exists:
                pyrvt_ribbon_tab = self._get_component[tab_name]
                pyrvt_ribbon_tab.update_name(tab_name)
                pyrvt_ribbon_tab.activate()
            else:
                raise PyRevitUIError('RibbonTab already exits and update is not allowed: {}'.format(tab_name))
        else:
            try:
                # creating tab in Revit ui
                __revit__.CreateRibbonTab(tab_name)
                # __revit__.CreateRibbonTab() does not return the created tab object.
                # so find the tab object in exiting ui and assign to new_tab controller.
                revit_tab_ctrl = None
                for exiting_rvt_ribbon_tab in ComponentManager.Ribbon.Tabs:
                    if exiting_rvt_ribbon_tab.Title == tab_name:
                        revit_tab_ctrl = exiting_rvt_ribbon_tab

                # creating _PyRevitRibbonTab object
                if revit_tab_ctrl:
                    # add new tab to list of current tabs
                    self._add_component(_PyRevitRibbonTab(revit_tab_ctrl))
                else:
                    raise PyRevitUIError('Tab created but can not be obtained from ui.')

            except Exception as err:
                raise PyRevitUIError('Can not create tab: {}'.format(err))


# Public function to return an instance of _PyRevitUI which is used to interact with current ui ------------------------
def get_current_ui():
    """Revit UI Wrapper class for interacting with current pyRevit UI.
    Returned class provides min required functionality for user interaction
    Example:
        current_ui = pyRevit.session.current_ui()
        this_script = pyRevit.session.get_this_command()
        current_ui.update_button_icon(this_script, new_icon)
    """
    return _PyRevitUI()
