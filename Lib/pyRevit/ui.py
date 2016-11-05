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

from .config import ICON_SMALL_SIZE, ICON_MEDIUM_SIZE, ICON_LARGE_SIZE, SPLITPUSH_BUTTON_SYNC_PARAM
from .logger import logger
from .exceptions import PyRevitUIError

# dotnet imports
import clr
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPIUI')
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

# revit api imports
from Autodesk.Revit.UI import PushButton, PulldownButton, SplitButton
from Autodesk.Revit.UI import RibbonItemData, PushButtonData, PulldownButtonData, SplitButtonData
from Autodesk.Revit.Exceptions import ArgumentException

try:
    clr.AddReference('AdWindows')
    from Autodesk.Windows import ComponentManager
    from Autodesk.Windows import RibbonRowPanel, RibbonButton, RibbonFoldPanel, RibbonSplitButton, \
                                 RibbonToggleButton, RibbonSeparator, RibbonPanelBreak, RibbonRowPanel, RibbonSeparator
except Exception as err:
    logger.critical('Can not establish ui module. Error importing AdWindow.dll')
    raise err


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
        self.largeBitmap.DecodePixelHeight = ICON_LARGE_SIZE
        self.largeBitmap.DecodePixelWidth = ICON_LARGE_SIZE
        self.largeBitmap.EndInit()


# Superclass to all ui item classes ---------------------------------------------------------------------------------
class _GenericPyRevitUIContainer:
    def __init__(self):
        self.name = ''
        self._rvtapi_object = None
        self._sub_pyrvt_components = {}

    def __iter__(self):
        return iter(self._sub_pyrvt_components.values())

    def __repr__(self):
        return 'Name: {} RevitAPIObject: {} Children: {}'.format(self.name,
                                                                 self._rvtapi_object,
                                                                 self._sub_pyrvt_components)

    def _get_component(self, cmp_name):
        try:
            return self._sub_pyrvt_components[cmp_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve item {} from {}'.format(cmp_name, self))

    def _add_component(self, new_component):
        self._sub_pyrvt_components[new_component.name] = new_component

    def _get_rvtapi_object(self):
        return self._rvtapi_object

    def _set_rvtapi_object(self, rvtapi_obj):
        self._rvtapi_object = rvtapi_obj

    def contains(self, pyrvt_cmp_name):
        return pyrvt_cmp_name in self._sub_pyrvt_components.keys()

    # def set_name(self, new_name):
    #     if hasattr(self._rvtapi_object, 'Text'):
    #         self._rvtapi_object.Text = new_name
    #     elif hasattr(self._rvtapi_object, 'Title'):
    #         self._rvtapi_object.Title = new_name
    #     elif hasattr(self._rvtapi_object, 'Name'):
    #         self._rvtapi_object.Name = new_name
    #     else:
    #         raise PyRevitUIError('Can not set name for: {}'.format(self))

    def activate(self):
        if hasattr(self._rvtapi_object, 'Enabled') and hasattr(self._rvtapi_object, 'Visible'):
            self._rvtapi_object.Enabled = True
            self._rvtapi_object.Visible = True
        elif hasattr(self._rvtapi_object, 'IsEnabled') and hasattr(self._rvtapi_object, 'IsVisible'):
            self._rvtapi_object.IsEnabled = True
            self._rvtapi_object.IsVisible = True
        else:
            raise PyRevitUIError('Can not activate: {}'.format(self))

    def deactivate(self):
        if hasattr(self._rvtapi_object, 'Enabled') and hasattr(self._rvtapi_object, 'Visible'):
            self._rvtapi_object.Enabled = False
            self._rvtapi_object.Visible = False
        elif hasattr(self._rvtapi_object, 'IsEnabled') and hasattr(self._rvtapi_object, 'IsVisible'):
            self._rvtapi_object.IsEnabled = False
            self._rvtapi_object.IsVisible = False
        else:
            raise PyRevitUIError('Can not deactivate: {}'.format(self))


# Classes holding existing native ui elements (These elements are native and can not be modified) ----------------------
class _RevitNativeRibbonButton(_GenericPyRevitUIContainer):
    def __init__(self, adskwnd_ribbon_button):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = str(adskwnd_ribbon_button.AutomationName).replace('\r\n', ' ')
        self._rvtapi_object = adskwnd_ribbon_button


class _RevitNativeRibbonGroupItem(_GenericPyRevitUIContainer):
    def __init__(self, adskwnd_ribbon_item):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = adskwnd_ribbon_item.Source.Title
        self._rvtapi_object = adskwnd_ribbon_item

        # finding children on this button group
        for adskwnd_ribbon_button in adskwnd_ribbon_item.Items:
            self._add_component(_RevitNativeRibbonButton(adskwnd_ribbon_button))

    button = _GenericPyRevitUIContainer._get_component


class _RevitNativeRibbonPanel(_GenericPyRevitUIContainer):
    def __init__(self, adskwnd_ribbon_panel):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = adskwnd_ribbon_panel.Source.Title
        self._rvtapi_object = adskwnd_ribbon_panel

        all_adskwnd_ribbon_items = []
        # getting a list of existing items under this panel
        # RibbonFoldPanel items are not visible. they automatically fold buttons into stack on revit ui resize
        # since RibbonFoldPanel are not visible it does not make sense to create objects for them.
        # This pre cleaner loop, finds the RibbonFoldPanel items and adds the children to the main list
        for adskwnd_ribbon_item in adskwnd_ribbon_panel.Source.Items:
            if isinstance(adskwnd_ribbon_item, RibbonFoldPanel):
                try:
                    for sub_rvtapi_item in adskwnd_ribbon_item.Items:
                        all_adskwnd_ribbon_items.append(sub_rvtapi_item)
                except Exception as err:
                    logger.debug('Can not get RibbonFoldPanel children: {} | {}'.format(adskwnd_ribbon_item, err))
            else:
                all_adskwnd_ribbon_items.append(adskwnd_ribbon_item)

        # processing the cleaned children list and creating pyrevit native ribbon objects
        for adskwnd_ribbon_item in all_adskwnd_ribbon_items:
            try:
                if isinstance(adskwnd_ribbon_item, RibbonButton) or isinstance(adskwnd_ribbon_item, RibbonToggleButton):
                    self._add_component(_RevitNativeRibbonButton(adskwnd_ribbon_item))
                elif isinstance(adskwnd_ribbon_item, RibbonSplitButton):
                    self._add_component(_RevitNativeRibbonGroupItem(adskwnd_ribbon_item))

            except Exception as err:
                logger.debug('Can not create native ribbon item: {} | {}'.format(adskwnd_ribbon_item, err))

    ribbon_item = _GenericPyRevitUIContainer._get_component


class _RevitNativeRibbonTab(_GenericPyRevitUIContainer):
    def __init__(self, adskwnd_ribbon_tab):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = adskwnd_ribbon_tab.Title
        self._rvtapi_object = adskwnd_ribbon_tab

        # getting a list of existing panels under this tab
        try:
            for adskwnd_ribbon_panel in adskwnd_ribbon_tab.Panels:
                # only listing visible panels
                if adskwnd_ribbon_panel.IsVisible:
                    self._add_component(_RevitNativeRibbonPanel(adskwnd_ribbon_panel))
        except Exception as err:
            logger.debug('Can not get native panels for this native tab: {} | {}'.format(adskwnd_ribbon_tab, err))

    ribbon_panel = _GenericPyRevitUIContainer._get_component


# Classes holding non-native ui elements -------------------------------------------------------------------------------
class _PyRevitRibbonButton(_GenericPyRevitUIContainer):
    def __init__(self, ribbon_button):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = ribbon_button.Name
        self._rvtapi_object = ribbon_button
        self._itemdata_mode = isinstance(self._rvtapi_object, RibbonItemData)

    def set_icon(self, icon_file, icon_size=ICON_MEDIUM_SIZE):
        try:
            button_icon = _ButtonIcons(icon_file)
        except Exception as err:
            raise PyRevitUIError('Can not create icon from given file: {} | {}'.format(icon_file, self))

        try:
            self._get_rvtapi_object().Image = button_icon.smallBitmap
            self._get_rvtapi_object().LargeImage = button_icon.mediumBitmap
            if icon_size == ICON_LARGE_SIZE:
                self._get_rvtapi_object().LargeImage = button_icon.largeBitmap

        except Exception as err:
            raise PyRevitUIError('Item does not have image property: {}'.format(err))

    def get_icon(self):
        try:
            if self._get_rvtapi_object().Image:
                return self._get_rvtapi_object().Image.UriSource.LocalPath
            elif self._get_rvtapi_object().LargeImage:
                return self._get_rvtapi_object().LargeImage.UriSource.LocalPath
        except Exception as err:
            raise PyRevitUIError('Item does not have image property: {}'.format(err))

    def set_tooltip(self, tooltip):
        try:
            self._get_rvtapi_object().ToolTip = tooltip
        except Exception as err:
            raise PyRevitUIError('Item does not have tooltip property: {}'.format(err))

    def set_tooltip_ext(self, tooltip_ext):
        try:
            self._get_rvtapi_object().LongDescription = tooltip_ext
        except Exception as err:
            raise PyRevitUIError('Item does not have extended tooltip property: {}'.format(err))


class _PyRevitRibbonGroupItem(_GenericPyRevitUIContainer):

    button = _GenericPyRevitUIContainer._get_component

    def __init__(self, ribbon_item):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = ribbon_item.Name
        self._rvtapi_object = ribbon_item
        self._itemdata_mode = isinstance(self._rvtapi_object, RibbonItemData)

        # if button group shows the active button icon, then the child buttons need to have large icons
        self._use_active_item_icon = (isinstance(self._rvtapi_object, SplitButton) or
                                      isinstance(self._rvtapi_object, SplitButtonData))

        # by default the last item used, stays on top as the default button
        self._sync_with_cur_item = True

        # getting a list of existing items under this item group.
        if not self._itemdata_mode:
            for revit_button in ribbon_item.GetItems():
                # feeding _sub_native_ribbon_items with an instance of _PyRevitRibbonButton for existing buttons
                self._add_component(_PyRevitRibbonButton(revit_button))

    def sync_with_current_item(self, state):
        if state:
            self._sync_with_cur_item = True
            if hasattr(self._get_rvtapi_object(), SPLITPUSH_BUTTON_SYNC_PARAM):
                self._get_rvtapi_object().IsSynchronizedWithCurrentItem = True
        else:
            self._sync_with_cur_item = False
            if hasattr(self._get_rvtapi_object(), SPLITPUSH_BUTTON_SYNC_PARAM):
                self._get_rvtapi_object().IsSynchronizedWithCurrentItem = False

    def set_icon(self, icon_file):
        try:
            button_icon = _ButtonIcons(icon_file)
        except Exception as err:
            raise PyRevitUIError('Can not create icon from given file: {} | {}'.format(icon_file, self))

        try:
            self._get_rvtapi_object().Image = button_icon.smallBitmap
            self._get_rvtapi_object().LargeImage = button_icon.largeBitmap
        except Exception as err:
            raise PyRevitUIError('Item does not have image property: {}'.format(err))

    def get_icon(self):
        try:
            if self._get_rvtapi_object().Image:
                return self._get_rvtapi_object().Image.UriSource.LocalPath
            elif self._get_rvtapi_object().LargeImage:
                return self._get_rvtapi_object().LargeImage.UriSource.LocalPath
        except Exception as err:
            raise PyRevitUIError('Item does not have image property: {}'.format(err))

    def create_push_button(self, button_name, asm_location, class_name,
                           icon_path, tooltip, tooltip_ext,
                           update_if_exists=False):
        if self.contains(button_name):
            if update_if_exists:
                exiting_item = self._get_component(button_name)
                exiting_item.activate()
                if icon_path:
                    # if button group shows the active button icon, then the child buttons need to have large icons
                    exiting_item.set_icon(icon_path,
                                          icon_size=ICON_LARGE_SIZE if self._use_active_item_icon else ICON_MEDIUM_SIZE)
                return
            else:
                raise PyRevitUIError('Push button already exits and update is not allowed: {}'.format(button_name))

        logger.debug('Parent does not include this button. Creating: {}'.format(button_name))
        try:
            button_data = PushButtonData(button_name, button_name, asm_location, class_name)
            if not self._itemdata_mode:
                ribbon_button = self._get_rvtapi_object().AddPushButton(button_data)
                new_button = _PyRevitRibbonButton(ribbon_button)
            else:
                new_button = _PyRevitRibbonButton(button_data)

            if not icon_path:
                logger.debug('Using parent item icon for {}'.format(new_button))
                parent_icon_path = self.get_icon()
                if parent_icon_path:
                    # if button group shows the active button icon, then the child buttons need to have large icons
                    new_button.set_icon(parent_icon_path,
                                        icon_size=ICON_LARGE_SIZE if self._use_active_item_icon else ICON_MEDIUM_SIZE)
                else:
                    logger.debug('Can not get item icon from {}'.format(self))
            else:
                logger.debug('Creating icon for push button {} from file: {}'.format(button_name, icon_path))
                try:
                    # if button group shows the active button icon, then the child buttons need to have large icons
                    new_button.set_icon(icon_path,
                                        icon_size=ICON_LARGE_SIZE if self._use_active_item_icon else ICON_MEDIUM_SIZE)
                except PyRevitUIError as iconerr:
                    logger.debug('Error adding icon for {} from {} | {}'.format(button_name, icon_path, iconerr))

            new_button.set_tooltip(tooltip)
            new_button.set_tooltip_ext(tooltip_ext)

            self._add_component(new_button)

        except Exception as err:
            raise PyRevitUIError('Can not create button | {}'.format(err))


class _PyRevitRibbonPanel(_GenericPyRevitUIContainer):

    button = _GenericPyRevitUIContainer._get_component
    ribbon_item = _GenericPyRevitUIContainer._get_component

    def __init__(self, rvt_ribbon_panel):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = rvt_ribbon_panel.Name
        self._rvtapi_object = rvt_ribbon_panel

        # when creating stacks of ribbon items, the ui needs to wait until all stack items have been added and the
        # creates the ui for the items. self.open_stack and .close_stack control set and unset this parameter.
        self._itemdata_mode = False
        self._pyrvt_item_cache = []

        # getting a list of existing panels under this tab
        for revit_ribbon_item in self._get_rvtapi_object().GetItems():
            # feeding _sub_native_ribbon_items with an instance of _PyRevitRibbonGroupItem for existing group items
            # _PyRevitRibbonPanel will find its existing ribbon items internally
            if isinstance(revit_ribbon_item, PulldownButton):
                self._add_component(_PyRevitRibbonGroupItem(revit_ribbon_item))
            elif isinstance(revit_ribbon_item, PushButton):
                self._add_component(_PyRevitRibbonButton(revit_ribbon_item))
            else:
                raise PyRevitUIError('Can not determin ribbon item type: {}'.format(revit_ribbon_item))

    def open_stack(self):
        self._itemdata_mode = True
        pass

    def reset_stack(self):
        self._itemdata_mode = False

    def close_stack(self):
        self._itemdata_mode = False
        self._create_stack()

    def _create_button_group(self, pulldowndata_type, item_name, icon_path, update_if_exists=False):
        if self.contains(item_name):
            if update_if_exists:
                exiting_item = self._get_component(item_name)
                exiting_item.activate()
                if icon_path:
                    exiting_item.set_icon(icon_path)
            else:
                raise PyRevitUIError('Pull down button already exits and update is not allowed: {}'.format(item_name))
        else:
            logger.debug('Panel does not include this pull down button. Creating: {}'.format(item_name))
            try:
                # creating pull down button data and add to child list
                pdbutton_data = pulldowndata_type(item_name, item_name)
                if not self._itemdata_mode:
                    logger.debug('Creating pull down button: {} in {}'.format(item_name, self))
                    new_push_button = self._get_rvtapi_object().AddItem(pdbutton_data)
                    pyrvt_pdbutton = _PyRevitRibbonGroupItem(new_push_button)
                    try:
                        pyrvt_pdbutton.set_icon(icon_path)
                    except PyRevitUIError as iconerr:
                        logger.debug('Error adding icon for {} from {} | {}'.format(item_name, icon_path, iconerr))
                else:
                    logger.debug('Creating pull down button under stack: {} in {}'.format(item_name, self))
                    pyrvt_pdbutton = _PyRevitRibbonGroupItem(pdbutton_data)
                    try:
                        pyrvt_pdbutton.set_icon(icon_path)
                    except PyRevitUIError as iconerr:
                        logger.debug('Error adding icon for {} from {} | {}'.format(item_name, icon_path, iconerr))
                    self._pyrvt_item_cache.append(pyrvt_pdbutton)

                self._add_component(pyrvt_pdbutton)

            except Exception as err:
                raise PyRevitUIError('Can not create pull down button: {}'.format(err))

    def _create_stack(self):
        # fixme: properly write stack
        parent_data_objects = [x._get_rvtapi_object() for x in self._pyrvt_item_cache]
        rvtui_items = self._get_rvtapi_object().AddStackedItems(*parent_data_objects)
        for rvtui_item, pyrvt_item in zip(rvtui_items, self._pyrvt_item_cache):
            self._get_component(pyrvt_item.name)._set_rvtapi_object(rvtui_item)
            if isinstance(pyrvt_item, _PyRevitRibbonGroupItem):
                if not pyrvt_item._sync_with_cur_item and hasattr(rvtui_item, SPLITPUSH_BUTTON_SYNC_PARAM):
                    rvtui_item.IsSynchronizedWithCurrentItem = False

                for pyrvt_item_sub_cmp in pyrvt_item:
                    rvt_ui_button = rvtui_item.AddPushButton(pyrvt_item_sub_cmp._get_rvtapi_object())
                    pyrvt_item_sub_cmp._set_rvtapi_object(rvt_ui_button)



        # clear the cache
        self._pyrvt_item_cache = []

    def create_push_button(self, button_name, asm_location, class_name,
                           icon_path, tooltip, tooltip_ext,
                           update_if_exists=False):
        if self.contains(button_name):
            if update_if_exists:
                exiting_item = self._get_component(button_name)
                exiting_item.activate()
                if icon_path:
                    exiting_item.set_icon(icon_path)
            else:
                raise PyRevitUIError('Push button already exits and update is not allowed: {}'.format(button_name))
        else:
            logger.debug('Parent does not include this button. Creating: {}'.format(button_name))
            try:
                button_data = PushButtonData(button_name, button_name, asm_location, class_name)
                if not self._itemdata_mode:
                    ribbon_button = self._get_rvtapi_object().AddItem(button_data)
                    new_button = _PyRevitRibbonButton(ribbon_button)
                else:
                    new_button = _PyRevitRibbonButton(button_data)
                    self._pyrvt_item_cache.append(new_button)

                if not icon_path:
                    logger.debug('Parent ui item is a panel and panels don\'t have icons.')
                else:
                    logger.debug('Creating icon for push button {} from file: {}'.format(button_name, icon_path))
                    try:
                        new_button.set_icon(icon_path)
                    except PyRevitUIError as iconerr:
                        logger.error('Error adding icon for {} from {} | {}'.format(button_name, icon_path, iconerr))

                new_button.set_tooltip(tooltip)
                new_button.set_tooltip_ext(tooltip_ext)

                self._add_component(new_button)

            except Exception as err:
                raise PyRevitUIError('Can not create button | {}'.format(err))

    def create_pulldown_button(self, item_name, icon_path, update_if_exists=False):
        self._create_button_group(PulldownButtonData, item_name, icon_path, update_if_exists)

    def create_split_button(self, item_name, icon_path, update_if_exists=False):
        self._create_button_group(SplitButtonData, item_name, icon_path, update_if_exists)
        self.ribbon_item(item_name).sync_with_current_item(True)

    def create_splitpush_button(self, item_name, icon_path, update_if_exists=False):
        self._create_button_group(SplitButtonData, item_name, icon_path, update_if_exists)
        self.ribbon_item(item_name).sync_with_current_item(False)


class _PyRevitRibbonTab(_GenericPyRevitUIContainer):

    ribbon_panel = _GenericPyRevitUIContainer._get_component

    def __init__(self, revit_ribbon_tab):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = revit_ribbon_tab.Title
        self._rvtapi_object = revit_ribbon_tab

        # getting a list of existing panels under this tab
        try:
            for revit_ui_panel in __revit__.GetRibbonPanels(self.name):
                # feeding _sub_pyrvt_ribbon_panels with an instance of _PyRevitRibbonPanel for existing panels
                # _PyRevitRibbonPanel will find its existing ribbon items internally
                new_pyrvt_panel = _PyRevitRibbonPanel(revit_ui_panel)
                self._add_component(new_pyrvt_panel)
        except:
            # if .GetRibbonPanels fails, this tab is an existing native tab
            raise PyRevitUIError('Can not get panels for this tab: {}'.format(self._rvtapi_object))

    def update_name(self, new_name):
        self._get_rvtapi_object().Title = new_name

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
                ribbon_panel = __revit__.CreateRibbonPanel(self.name, panel_name)
                # creating _PyRevitRibbonPanel object and add new panel to list of current panels
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
            # only listing visible tabs (there might be tabs with identical names
            # e.g. there are two Annotate tabs. They are activated as neccessary per context
            if revit_ui_tab.IsVisible:
                try:
                    new_pyrvt_tab = _PyRevitRibbonTab(revit_ui_tab)
                    self._add_component(new_pyrvt_tab)
                    logger.debug('Tab added to the list of tabs: {}'.format(new_pyrvt_tab.name))
                except PyRevitUIError:
                    # if _PyRevitRibbonTab(revit_ui_tab) fails, Revit restricts access to its panels
                    # _RevitNativeRibbonTab uses a different method to access the panels
                    # to interact with existing native ui
                    new_pyrvt_tab = _RevitNativeRibbonTab(revit_ui_tab)
                    self._add_component(new_pyrvt_tab)
                    logger.debug('Native tab added to the list of tabs: {}'.format(new_pyrvt_tab.name))

    def create_ribbon_tab(self, tab_name, update_if_exists=False):
        if self.contains(tab_name):
            if update_if_exists:
                pyrvt_ribbon_tab = self._get_component(tab_name)
                pyrvt_ribbon_tab.update_name(tab_name)
                pyrvt_ribbon_tab.activate()
            else:
                raise PyRevitUIError('RibbonTab already exits and update is not allowed: {}'.format(tab_name))
        else:
            try:
                # creating tab in Revit ui
                __revit__.CreateRibbonTab(tab_name)
                # __revit__.CreateRibbonTab() does not return the created tab object.
                # so find the tab object in exiting ui
                revit_tab_ctrl = None
                for exiting_rvt_ribbon_tab in ComponentManager.Ribbon.Tabs:
                    if exiting_rvt_ribbon_tab.Title == tab_name:
                        revit_tab_ctrl = exiting_rvt_ribbon_tab

                # create _PyRevitRibbonTab object with the recovered RibbonTab object
                # and add new _PyRevitRibbonTab to list of current tabs
                if revit_tab_ctrl:
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
