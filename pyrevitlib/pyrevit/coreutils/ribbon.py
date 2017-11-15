from collections import OrderedDict

from pyrevit import HOST_APP, EXEC_PARAMS, PyRevitException
from pyrevit.coreutils.logger import get_logger
from pyrevit.framework import Uri, Imaging
from pyrevit.framework import BindingFlags
from pyrevit.api import UI, AdWindows


logger = get_logger(__name__)


PYREVIT_TAB_IDENTIFIER = 'pyrevit_tab'

ICON_SMALL = 16
ICON_MEDIUM = 24
ICON_LARGE = 32


# Helper classes and functions -------------------------------------------------
class PyRevitUIError(PyRevitException):
    pass


class _ButtonIcons:
    def __init__(self, file_address):
        self.smallBitmap = self.create_bitmap(file_address, ICON_SMALL)
        self.mediumBitmap = self.create_bitmap(file_address, ICON_MEDIUM)
        self.largeBitmap = self.create_bitmap(file_address, ICON_LARGE)

    @staticmethod
    def create_bitmap(file_address, image_size):
        logger.debug('Creating {0}x{0} bitmap from: {1}'
                     .format(image_size, file_address))
        bitmap_image = Imaging.BitmapImage()
        bitmap_image.BeginInit()
        bitmap_image.UriSource = Uri(file_address)
        bitmap_image.CacheOption = Imaging.BitmapCacheOption.OnLoad
        bitmap_image.CreateOptions = Imaging.BitmapCreateOptions.DelayCreation
        dpi_scalefactor = 96.0 / Imaging.BitmapImage(Uri(file_address)).DpiX
        adjusted_size = image_size / dpi_scalefactor
        bitmap_image.DecodePixelHeight = adjusted_size
        bitmap_image.EndInit()
        return bitmap_image


# Superclass to all ui item classes --------------------------------------------
class _GenericPyRevitUIContainer:
    def __init__(self):
        self.name = ''
        self._rvtapi_object = None
        self._sub_pyrvt_components = OrderedDict()
        self.itemdata_mode = False
        self._dirty = False

    def __iter__(self):
        return iter(self._sub_pyrvt_components.values())

    def __repr__(self):
        return 'Name: {} RevitAPIObject: {}'.format(self.name,
                                                    self._rvtapi_object)

    def _get_component(self, cmp_name):
        try:
            return self._sub_pyrvt_components[cmp_name]
        except KeyError:
            raise PyRevitUIError('Can not retrieve item {} from {}'
                                 .format(cmp_name, self))

    def _add_component(self, new_component):
        self._sub_pyrvt_components[new_component.name] = new_component

    def _remove_component(self, expired_cmp_name):
        try:
            self._sub_pyrvt_components.pop(expired_cmp_name)
        except KeyError:
            raise PyRevitUIError('Can not remove item {} from {}'
                                 .format(expired_cmp_name, self))

    def get_rvtapi_object(self):
        return self._rvtapi_object

    def set_rvtapi_object(self, rvtapi_obj):
        self._rvtapi_object = rvtapi_obj
        self.itemdata_mode = False
        self._dirty = True

    def get_adwindows_object(self):
        rvtapi_obj = self._rvtapi_object
        getRibbonItemMethod = \
            rvtapi_obj.GetType().GetMethod(
                'getRibbonItem',
                BindingFlags.NonPublic | BindingFlags.Instance
                )
        if getRibbonItemMethod:
            return getRibbonItemMethod.Invoke(rvtapi_obj, None)

    def get_flagged_children(self, state=True):
        flagged_cmps = []
        for component in self:
            flagged_cmps.extend(component.get_flagged_children(state))
            if component.is_dirty() == state:
                flagged_cmps.append(component)
        return flagged_cmps

    @staticmethod
    def is_native():
        return False

    def is_dirty(self):
        if self._dirty:
            return self._dirty
        else:
            # check if there is any dirty child
            for component in self:
                if component.is_dirty():
                    return True
            return False

    def set_dirty_flag(self, state=True):
        self._dirty = state

    def contains(self, pyrvt_cmp_name):
        return pyrvt_cmp_name in self._sub_pyrvt_components.keys()

    def find_child(self, child_name):
        for sub_cmp in self._sub_pyrvt_components.values():
            if child_name == sub_cmp.name:
                return sub_cmp
            elif hasattr(sub_cmp, 'ui_title') \
                    and child_name == sub_cmp.ui_title:
                return sub_cmp

            component = sub_cmp.find_child(child_name)
            if component:
                return component

        return None

    def activate(self):
        if hasattr(self._rvtapi_object, 'Enabled') \
                and hasattr(self._rvtapi_object, 'Visible'):
            self._rvtapi_object.Enabled = True
            self._rvtapi_object.Visible = True
            self._dirty = True
        elif hasattr(self._rvtapi_object, 'IsEnabled') \
                and hasattr(self._rvtapi_object, 'IsVisible'):
            self._rvtapi_object.IsEnabled = True
            self._rvtapi_object.IsVisible = True
            self._dirty = True
        else:
            raise PyRevitUIError('Can not activate: {}'.format(self))

    def deactivate(self):
        if hasattr(self._rvtapi_object, 'Enabled') \
                and hasattr(self._rvtapi_object, 'Visible'):
            self._rvtapi_object.Enabled = False
            self._rvtapi_object.Visible = False
            self._dirty = True
        elif hasattr(self._rvtapi_object, 'IsEnabled') \
                and hasattr(self._rvtapi_object, 'IsVisible'):
            self._rvtapi_object.IsEnabled = False
            self._rvtapi_object.IsVisible = False
            self._dirty = True
        else:
            raise PyRevitUIError('Can not deactivate: {}'.format(self))

    def get_updated_items(self):
        return self.get_flagged_children()

    def get_unchanged_items(self):
        return self.get_flagged_children(state=False)


# Classes holding existing native ui elements
# (These elements are native and can not be modified) --------------------------
class _GenericRevitNativeUIContainer(_GenericPyRevitUIContainer):
    def __init__(self):
        _GenericPyRevitUIContainer.__init__(self)

    @staticmethod
    def is_native():
        return True

    def deactivate(self):
        raise PyRevitUIError('Can not de/activate native item: {}'
                             .format(self))

    activate = deactivate


class _RevitNativeRibbonButton(_GenericRevitNativeUIContainer):
    def __init__(self, adwnd_ribbon_button):
        _GenericRevitNativeUIContainer.__init__(self)

        self.name = \
            unicode(adwnd_ribbon_button.AutomationName).replace('\r\n', ' ')
        self._rvtapi_object = adwnd_ribbon_button


class _RevitNativeRibbonGroupItem(_GenericRevitNativeUIContainer):
    def __init__(self, adwnd_ribbon_item):
        _GenericRevitNativeUIContainer.__init__(self)

        self.name = adwnd_ribbon_item.Source.Title
        self._rvtapi_object = adwnd_ribbon_item

        # finding children on this button group
        for adwnd_ribbon_button in adwnd_ribbon_item.Items:
            self._add_component(_RevitNativeRibbonButton(adwnd_ribbon_button))

    button = _GenericRevitNativeUIContainer._get_component


class _RevitNativeRibbonPanel(_GenericRevitNativeUIContainer):
    def __init__(self, adwnd_ribbon_panel):
        _GenericRevitNativeUIContainer.__init__(self)

        self.name = adwnd_ribbon_panel.Source.Title
        self._rvtapi_object = adwnd_ribbon_panel

        all_adwnd_ribbon_items = []
        # getting a list of existing items under this panel
        # RibbonFoldPanel items are not visible. they automatically fold
        # buttons into stack on revit ui resize since RibbonFoldPanel are
        # not visible it does not make sense to create objects for them.
        # This pre-cleaner loop, finds the RibbonFoldPanel items and
        # adds the children to the main list
        for adwnd_ribbon_item in adwnd_ribbon_panel.Source.Items:
            if isinstance(adwnd_ribbon_item, AdWindows.RibbonFoldPanel):
                try:
                    for sub_rvtapi_item in adwnd_ribbon_item.Items:
                        all_adwnd_ribbon_items.append(sub_rvtapi_item)
                except Exception as append_err:
                    logger.debug('Can not get RibbonFoldPanel children: {} '
                                 '| {}'.format(adwnd_ribbon_item,
                                               append_err))
            else:
                all_adwnd_ribbon_items.append(adwnd_ribbon_item)

        # processing the panel slideout for exising ribbon items
        for adwnd_slideout_item \
                in adwnd_ribbon_panel.Source.SlideOutPanelItemsView:
            all_adwnd_ribbon_items.append(adwnd_slideout_item)

        # processing the cleaned children list and
        # creating pyRevit native ribbon objects
        for adwnd_ribbon_item in all_adwnd_ribbon_items:
            try:
                if isinstance(adwnd_ribbon_item,
                              AdWindows.RibbonButton) \
                        or isinstance(adwnd_ribbon_item,
                                      AdWindows.RibbonToggleButton):
                    self._add_component(
                        _RevitNativeRibbonButton(adwnd_ribbon_item))
                elif isinstance(adwnd_ribbon_item,
                                AdWindows.RibbonSplitButton):
                    self._add_component(
                        _RevitNativeRibbonGroupItem(adwnd_ribbon_item))

            except Exception as append_err:
                logger.debug('Can not create native ribbon item: {} '
                             '| {}'.format(adwnd_ribbon_item, append_err))

    ribbon_item = _GenericRevitNativeUIContainer._get_component


class _RevitNativeRibbonTab(_GenericRevitNativeUIContainer):
    def __init__(self, adwnd_ribbon_tab):
        _GenericRevitNativeUIContainer.__init__(self)

        self.name = adwnd_ribbon_tab.Title
        self._rvtapi_object = adwnd_ribbon_tab

        # getting a list of existing panels under this tab
        try:
            for adwnd_ribbon_panel in adwnd_ribbon_tab.Panels:
                # only listing visible panels
                if adwnd_ribbon_panel.IsVisible:
                    self._add_component(
                        _RevitNativeRibbonPanel(adwnd_ribbon_panel)
                    )
        except Exception as append_err:
            logger.debug('Can not get native panels for this native tab: {} '
                         '| {}'.format(adwnd_ribbon_tab, append_err))

    ribbon_panel = _GenericRevitNativeUIContainer._get_component

    @staticmethod
    def is_pyrevit_tab():
        return False


# Classes holding non-native ui elements ---------------------------------------
class _PyRevitRibbonButton(_GenericPyRevitUIContainer):
    def __init__(self, ribbon_button):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = ribbon_button.Name
        self._rvtapi_object = ribbon_button

        # when container is in itemdata_mode, self._rvtapi_object is a
        # RibbonItemData and not an actual ui item a sunsequent call to
        # create_data_items will create ui for RibbonItemData objects
        self.itemdata_mode = isinstance(self._rvtapi_object,
                                        UI.RibbonItemData)

        self.ui_title = self.name
        if not self.itemdata_mode:
            self.ui_title = self._rvtapi_object.ItemText

    def set_rvtapi_object(self, rvtapi_obj):
        _GenericPyRevitUIContainer.set_rvtapi_object(self, rvtapi_obj)
        # update the ui title for the newly added rvtapi_obj
        self._rvtapi_object.ItemText = self.ui_title

    def set_icon(self, icon_file, icon_size=ICON_MEDIUM):
        try:
            button_icon = _ButtonIcons(icon_file)
        except Exception:
            raise PyRevitUIError('Can not create icon from given file: {} '
                                 '| {}'.format(icon_file, self))

        try:
            self.get_rvtapi_object().Image = button_icon.smallBitmap
            self.get_rvtapi_object().LargeImage = button_icon.mediumBitmap
            if icon_size == ICON_LARGE:
                self.get_rvtapi_object().LargeImage = button_icon.largeBitmap
            self._dirty = True
        except Exception as icon_err:
            raise PyRevitUIError('Item does not have image property: {}'
                                 .format(icon_err))

    def get_icon(self):
        try:
            if self.get_rvtapi_object().Image:
                return self.get_rvtapi_object().Image.UriSource.LocalPath
            elif self.get_rvtapi_object().LargeImage:
                return self.get_rvtapi_object().LargeImage.UriSource.LocalPath
        except Exception as icon_err:
            raise PyRevitUIError('Item does not have image property: {}'
                                 .format(icon_err))

    def set_tooltip(self, tooltip):
        try:
            self.get_rvtapi_object().ToolTip = tooltip
            self._dirty = True
        except Exception as tooltip_err:
            raise PyRevitUIError('Item does not have tooltip property: {}'
                                 .format(tooltip_err))

    def set_tooltip_ext(self, tooltip_ext):
        try:
            self.get_rvtapi_object().LongDescription = tooltip_ext
            self._dirty = True
        except Exception as tooltip_err:
            raise PyRevitUIError('Item does not have extended '
                                 'tooltip property: {}'.format(tooltip_err))

    def set_tooltip_video(self, tooltip_video):
        try:
            adwindows_obj = self.get_adwindows_object()
            if adwindows_obj.ToolTip:
                adwindows_obj.ToolTip.ExpandedVideo = Uri(tooltip_video)
        except Exception as ttvideo_err:
            raise PyRevitUIError('Error setting tooltip video {} | {} '
                                 .format(tooltip_video, ttvideo_err))

    def set_title(self, ui_title):
        if self.itemdata_mode:
            self.ui_title = ui_title
            self._dirty = True
        else:
            self._rvtapi_object.ItemText = self.ui_title = ui_title
            self._dirty = True

    def get_title(self):
        if self.itemdata_mode:
            return self.ui_title
        else:
            return self._rvtapi_object.ItemText

    @property
    def assembly_name(self):
        return self._rvtapi_object.AssemblyName

    @property
    def class_name(self):
        return self._rvtapi_object.ClassName

    @property
    def availability_class_name(self):
        return self._rvtapi_object.AvailabilityClassName


class _PyRevitRibbonGroupItem(_GenericPyRevitUIContainer):

    button = _GenericPyRevitUIContainer._get_component

    def __init__(self, ribbon_item):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = ribbon_item.Name
        self._rvtapi_object = ribbon_item

        # when container is in itemdata_mode, self._rvtapi_object is a
        # RibbonItemData and not an actual ui item when container is in
        # itemdata_mode, only the necessary RibbonItemData objects will
        # be created for children a sunsequent call to create_data_items
        # will create ui for RibbonItemData objects
        self.itemdata_mode = isinstance(self._rvtapi_object,
                                        UI.RibbonItemData)

        # if button group shows the active button icon, then the child
        # buttons need to have large icons
        self._use_active_item_icon = self._is_splitbutton()

        # by default the last item used, stays on top as the default button
        self._sync_with_cur_item = True

        # getting a list of existing items under this item group.
        if not self.itemdata_mode:
            for revit_button in ribbon_item.GetItems():
                # feeding _sub_native_ribbon_items with an instance of
                # _PyRevitRibbonButton for existing buttons
                self._add_component(_PyRevitRibbonButton(revit_button))

    def _is_splitbutton(self):
        return isinstance(self._rvtapi_object, UI.SplitButton) \
               or isinstance(self._rvtapi_object, UI.SplitButtonData)

    def set_rvtapi_object(self, rvtapi_obj):
        _GenericPyRevitUIContainer.set_rvtapi_object(self, rvtapi_obj)
        if self._is_splitbutton():
            self.get_rvtapi_object().IsSynchronizedWithCurrentItem = \
                self._sync_with_cur_item

    def create_data_items(self):
        # iterate through data items and their associated revit
        # api data objects and create ui objects
        for pyrvt_ui_item in [x for x in self if x.itemdata_mode]:
            rvtapi_data_obj = pyrvt_ui_item.get_rvtapi_object()

            # create item in ui and get correspoding revit ui objects
            if isinstance(pyrvt_ui_item, _PyRevitRibbonButton):
                rvtapi_ribbon_item = \
                    self.get_rvtapi_object().AddPushButton(rvtapi_data_obj)
                rvtapi_ribbon_item.ItemText = pyrvt_ui_item.get_title()
                # replace data object with the newly create ribbon item
                pyrvt_ui_item.set_rvtapi_object(rvtapi_ribbon_item)

        self.itemdata_mode = False

    def sync_with_current_item(self, state):
        try:
            if not self.itemdata_mode:
                self.get_rvtapi_object().IsSynchronizedWithCurrentItem = state
            self._sync_with_cur_item = state
            self._dirty = True
        except Exception as sync_item_err:
            raise PyRevitUIError('Item is not a split button. '
                                 '| {}'.format(sync_item_err))

    def set_icon(self, icon_file, icon_size=ICON_MEDIUM):
        try:
            button_icon = _ButtonIcons(icon_file)
        except Exception:
            raise PyRevitUIError('Can not create icon from given file: {} '
                                 '| {}'.format(icon_file, self))

        try:
            self.get_rvtapi_object().Image = button_icon.smallBitmap
            self.get_rvtapi_object().LargeImage = button_icon.largeBitmap
            if icon_size == ICON_LARGE:
                self.get_rvtapi_object().LargeImage = button_icon.largeBitmap
            self._dirty = True
        except Exception as icon_err:
            raise PyRevitUIError('Item does not have image property: {}'
                                 .format(icon_err))

    def get_icon(self):
        try:
            if self.get_rvtapi_object().Image:
                return self.get_rvtapi_object().Image.UriSource.LocalPath
            elif self.get_rvtapi_object().LargeImage:
                return self.get_rvtapi_object().LargeImage.UriSource.LocalPath
        except Exception as icon_err:
            raise PyRevitUIError('Item does not have image property: {}'
                                 .format(icon_err))

    def create_push_button(self, button_name, asm_location, class_name,
                           icon_path='',
                           tooltip='', tooltip_ext='', tooltip_video='',
                           avail_class_name=None,
                           update_if_exists=False, ui_title=None):
        if self.contains(button_name):
            if update_if_exists:
                existing_item = self._get_component(button_name)
                try:
                    # Assembly and Class info of current active script
                    # button can not be updated.
                    if button_name != EXEC_PARAMS.command_name:
                        rvtapi_obj = existing_item.get_rvtapi_object()
                        rvtapi_obj.AssemblyName = asm_location
                        rvtapi_obj.ClassName = class_name
                        if avail_class_name:
                            existing_item.get_rvtapi_object() \
                                .AvailabilityClassName = avail_class_name
                except Exception as asm_update_err:
                        logger.debug('Error updating button asm info: {} '
                                     '| {}'.format(button_name,
                                                   asm_update_err))

                if not icon_path:
                    logger.debug('Using parent item icon for {}'
                                 .format(existing_item))
                    parent_icon_path = self.get_icon()
                    if parent_icon_path:
                        # if button group shows the active button icon,
                        # then the child buttons need to have large icons
                        existing_item.set_icon(parent_icon_path,
                                               icon_size=ICON_LARGE
                                               if self._use_active_item_icon
                                               else ICON_MEDIUM)
                    else:
                        logger.debug('Can not get item icon from {}'
                                     .format(self))
                else:
                    try:
                        # if button group shows the active button icon,
                        # then the child buttons need to have large icons
                        existing_item.set_icon(icon_path,
                                               icon_size=ICON_LARGE
                                               if self._use_active_item_icon
                                               else ICON_MEDIUM)
                    except PyRevitUIError as iconerr:
                        logger.error('Error adding icon for {} | {}'
                                     .format(button_name, iconerr))

                existing_item.set_tooltip(tooltip)
                existing_item.set_tooltip_ext(tooltip_ext)
                if tooltip_video:
                    existing_item.set_tooltip_video(tooltip_video)

                if ui_title:
                    existing_item.set_title(ui_title)

                existing_item.activate()
                return
            else:
                raise PyRevitUIError('Push button already exits and update '
                                     'is not allowed: {}'.format(button_name))

        logger.debug('Parent does not include this button. Creating: {}'
                     .format(button_name))
        try:
            button_data = UI.PushButtonData(button_name, button_name,
                                         asm_location, class_name)
            if avail_class_name:
                button_data.AvailabilityClassName = avail_class_name
            if not self.itemdata_mode:
                ribbon_button = \
                    self.get_rvtapi_object().AddPushButton(button_data)
                new_button = _PyRevitRibbonButton(ribbon_button)
            else:
                new_button = _PyRevitRibbonButton(button_data)

            if ui_title:
                new_button.set_title(ui_title)

            if not icon_path:
                logger.debug('Using parent item icon for {}'
                             .format(new_button))
                parent_icon_path = self.get_icon()
                if parent_icon_path:
                    # if button group shows the active button icon,
                    # then the child buttons need to have large icons
                    new_button.set_icon(parent_icon_path,
                                        icon_size=ICON_LARGE
                                        if self._use_active_item_icon
                                        else ICON_MEDIUM)
                else:
                    logger.debug('Can not get item icon from {}'
                                 .format(self))
            else:
                logger.debug('Creating icon for push button {} from file: {}'
                             .format(button_name, icon_path))
                try:
                    # if button group shows the active button icon,
                    # then the child buttons need to have large icons
                    new_button.set_icon(icon_path,
                                        icon_size=ICON_LARGE
                                        if self._use_active_item_icon
                                        else ICON_MEDIUM)
                except PyRevitUIError as iconerr:
                    logger.debug('Error adding icon for {} from {} '
                                 '| {}'.format(button_name,
                                               icon_path,
                                               iconerr))

            new_button.set_tooltip(tooltip)
            new_button.set_tooltip_ext(tooltip_ext)
            if tooltip_video:
                new_button.set_tooltip_video(tooltip_video)

            new_button.set_dirty_flag()
            self._add_component(new_button)

        except Exception as create_err:
            raise PyRevitUIError('Can not create button '
                                 '| {}'.format(create_err))

    def add_separator(self):
        self.get_rvtapi_object().AddSeparator()
        self._dirty = True


class _PyRevitRibbonPanel(_GenericPyRevitUIContainer):

    button = _GenericPyRevitUIContainer._get_component
    ribbon_item = _GenericPyRevitUIContainer._get_component

    def __init__(self, rvt_ribbon_panel):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = rvt_ribbon_panel.Name
        self._rvtapi_object = rvt_ribbon_panel

        # when container is in itemdata_mode, only the necessary
        # RibbonItemData objects will be created for children a sunsequent
        # call to create_data_items will create ui for RibbonItemData objects
        # This is specifically helpful when creating stacks in panels.
        # open_stack and close_stack control this parameter
        self.itemdata_mode = False

        # getting a list of existing panels under this tab
        for revit_ribbon_item in self.get_rvtapi_object().GetItems():
            # feeding _sub_native_ribbon_items with an instance of
            # _PyRevitRibbonGroupItem for existing group items
            # _PyRevitRibbonPanel will find its existing ribbon items internally
            if isinstance(revit_ribbon_item, UI.PulldownButton):
                self._add_component(
                    _PyRevitRibbonGroupItem(revit_ribbon_item))
            elif isinstance(revit_ribbon_item, UI.PushButton):
                self._add_component(_PyRevitRibbonButton(revit_ribbon_item))
            else:
                raise PyRevitUIError('Can not determin ribbon item type: {}'
                                     .format(revit_ribbon_item))

    def open_stack(self):
        self.itemdata_mode = True

    def close_stack(self):
        self._create_data_items()

    def add_separator(self):
        self.get_rvtapi_object().AddSeparator()
        self._dirty = True

    def add_slideout(self):
        try:
            self.get_rvtapi_object().AddSlideOut()
            self._dirty = True
        except Exception as slideout_err:
            raise PyRevitUIError('Error adding slide out: {}'
                                 .format(slideout_err))

    def _create_data_items(self):
        # fixme: if one item changes in stack and others dont change,
        # button will be created as pushbutton out of stack
        self.itemdata_mode = False

        # get a list of data item names and the
        # associated revit api data objects
        pyrvt_data_item_names = [x.name for x in self if x.itemdata_mode]
        rvtapi_data_objs = [x.get_rvtapi_object()
                            for x in self if x.itemdata_mode]

        # list of newly created revit_api ribbon items
        created_rvtapi_ribbon_items = []

        # create stack items in ui and get correspoding revit ui objects
        data_obj_count = len(rvtapi_data_objs)

        # if there are two or 3 items, create a proper stack
        if data_obj_count == 2 or data_obj_count == 3:
            created_rvtapi_ribbon_items = \
                self.get_rvtapi_object().AddStackedItems(*rvtapi_data_objs)
        # if there is only one item added,
        # add that to panel and forget about stacking
        elif data_obj_count == 1:
            rvtapi_pushbutton = \
                self.get_rvtapi_object().AddItem(*rvtapi_data_objs)
            created_rvtapi_ribbon_items.append(rvtapi_pushbutton)
        # if no items have been added, log the empty stack and return
        elif data_obj_count == 0:
            logger.debug('No new items has been added to stack. '
                         'Skipping stack creation.')
        # if none of the above, more than 3 items have been added.
        # Cleanup data item cache and raise an error.
        else:
            for pyrvt_data_item_name in pyrvt_data_item_names:
                self._remove_component(pyrvt_data_item_name)
            raise PyRevitUIError('Can not create stack of {}. '
                                 'Stack can only have 2 or 3 items.'
                                 .format(data_obj_count))

        # now that items are created and revit api objects are ready
        # iterate over the ribbon items and inject revit api objects
        # into the child pyrevit items
        for rvtapi_ribbon_item, pyrvt_data_item_name \
                in zip(created_rvtapi_ribbon_items, pyrvt_data_item_names):
            pyrvt_ui_item = self._get_component(pyrvt_data_item_name)
            # pyrvt_ui_item only had button data info.
            # Now that ui ribbon item has created, update pyrvt_ui_item
            # with corresponding revit api object.
            # .set_rvtapi_object() disables .itemdata_mode since
            # they're no longer data objects
            pyrvt_ui_item.set_rvtapi_object(rvtapi_ribbon_item)

            # if pyrvt_ui_item is a group,
            # create children and update group item data
            if isinstance(pyrvt_ui_item, _PyRevitRibbonGroupItem):
                pyrvt_ui_item.create_data_items()

    def create_push_button(self, button_name, asm_location, class_name,
                           icon_path='',
                           tooltip='', tooltip_ext='', tooltip_video='',
                           avail_class_name=None,
                           update_if_exists=False, ui_title=None):
        if self.contains(button_name):
            if update_if_exists:
                existing_item = self._get_component(button_name)
                try:
                    # Assembly and Class info of current active
                    # script button can not be updated.
                    if button_name != EXEC_PARAMS.command_name:
                        rvtapi_obj = existing_item.get_rvtapi_object()
                        rvtapi_obj.AssemblyName = asm_location
                        rvtapi_obj.ClassName = class_name
                        if avail_class_name:
                            rvtapi_obj.AvailabilityClassName = avail_class_name
                except Exception as asm_update_err:
                    logger.debug('Error updating button asm info: {} '
                                 '| {}'.format(button_name, asm_update_err))

                existing_item.set_tooltip(tooltip)
                existing_item.set_tooltip_ext(tooltip_ext)
                if tooltip_video:
                    existing_item.set_tooltip_video(tooltip_video)

                if ui_title:
                    existing_item.set_title(ui_title)
                try:
                    existing_item.set_icon(icon_path, icon_size=ICON_LARGE)
                except PyRevitUIError as iconerr:
                    logger.error('Error adding icon for {} '
                                 '| {}'.format(button_name, iconerr))
                existing_item.activate()
            else:
                raise PyRevitUIError('Push button already exits and update '
                                     'is not allowed: {}'.format(button_name))
        else:
            logger.debug('Parent does not include this button. Creating: {}'
                         .format(button_name))
            try:
                button_data = UI.PushButtonData(button_name, button_name,
                                             asm_location, class_name)
                if avail_class_name:
                    button_data.AvailabilityClassName = avail_class_name
                if not self.itemdata_mode:
                    ribbon_button = \
                        self.get_rvtapi_object().AddItem(button_data)
                    new_button = _PyRevitRibbonButton(ribbon_button)
                else:
                    new_button = _PyRevitRibbonButton(button_data)

                if ui_title:
                    new_button.set_title(ui_title)

                if not icon_path:
                    logger.debug('Parent ui item is a panel and '
                                 'panels don\'t have icons.')
                else:
                    logger.debug('Creating icon for push button {} '
                                 'from file: {}'.format(button_name,
                                                        icon_path))
                    try:
                        new_button.set_icon(icon_path, icon_size=ICON_LARGE)
                    except PyRevitUIError as iconerr:
                        logger.error('Error adding icon for {} from {} '
                                     '| {}'.format(button_name,
                                                   icon_path,
                                                   iconerr))

                new_button.set_tooltip(tooltip)
                new_button.set_tooltip_ext(tooltip_ext)
                if tooltip_video:
                    new_button.set_tooltip_video(tooltip_video)

                new_button.set_dirty_flag()
                self._add_component(new_button)

            except Exception as create_err:
                raise PyRevitUIError('Can not create button '
                                     '| {}'.format(create_err))

    def _create_button_group(self, pulldowndata_type, item_name, icon_path,
                             update_if_exists=False):
        if self.contains(item_name):
            if update_if_exists:
                exiting_item = self._get_component(item_name)
                exiting_item.activate()
                if icon_path:
                    exiting_item.set_icon(icon_path)
            else:
                raise PyRevitUIError('Pull down button already exits and '
                                     'update is not allowed: {}'
                                     .format(item_name))
        else:
            logger.debug('Panel does not include this pull down button. '
                         'Creating: {}'.format(item_name))
            try:
                # creating pull down button data and add to child list
                pdbutton_data = pulldowndata_type(item_name, item_name)
                if not self.itemdata_mode:
                    logger.debug('Creating pull down button: {} in {}'
                                 .format(item_name, self))
                    new_push_button = \
                        self.get_rvtapi_object().AddItem(pdbutton_data)
                    pyrvt_pdbutton = _PyRevitRibbonGroupItem(new_push_button)
                    try:
                        pyrvt_pdbutton.set_icon(icon_path)
                    except PyRevitUIError as iconerr:
                        logger.debug('Error adding icon for {} from {} '
                                     '| {}'.format(item_name,
                                                   icon_path,
                                                   iconerr))
                else:
                    logger.debug('Creating pull down button under stack: '
                                 '{} in {}'.format(item_name, self))
                    pyrvt_pdbutton = _PyRevitRibbonGroupItem(pdbutton_data)
                    try:
                        pyrvt_pdbutton.set_icon(icon_path)
                    except PyRevitUIError as iconerr:
                        logger.debug('Error adding icon for {} from {} '
                                     '| {}'.format(item_name,
                                                   icon_path,
                                                   iconerr))

                pyrvt_pdbutton.set_dirty_flag()
                self._add_component(pyrvt_pdbutton)

            except Exception as button_err:
                raise PyRevitUIError('Can not create pull down button: {}'
                                     .format(button_err))

    def create_pulldown_button(self, item_name, icon_path,
                               update_if_exists=False):
        self._create_button_group(UI.PulldownButtonData, item_name, icon_path,
                                  update_if_exists)

    def create_split_button(self, item_name, icon_path,
                            update_if_exists=False):
        if self.itemdata_mode and HOST_APP.is_older_than('2017'):
            raise PyRevitUIError('Revits earlier than 2017 do not support '
                                 'split buttons in a stack.')
        else:
            self._create_button_group(UI.SplitButtonData, item_name, icon_path,
                                      update_if_exists)
            self.ribbon_item(item_name).sync_with_current_item(True)

    def create_splitpush_button(self, item_name, icon_path,
                                update_if_exists=False):
        if self.itemdata_mode and HOST_APP.is_older_than('2017'):
            raise PyRevitUIError('Revits earlier than 2017 do not support '
                                 'split buttons in a stack.')
        else:
            self._create_button_group(UI.SplitButtonData, item_name, icon_path,
                                      update_if_exists)
            self.ribbon_item(item_name).sync_with_current_item(False)


class _PyRevitRibbonTab(_GenericPyRevitUIContainer):
    ribbon_panel = _GenericPyRevitUIContainer._get_component

    def __init__(self, revit_ribbon_tab, is_pyrvt_tab=False):
        _GenericPyRevitUIContainer.__init__(self)

        self.name = revit_ribbon_tab.Title
        self._rvtapi_object = revit_ribbon_tab

        # is this tab created by pyrevit.revitui?
        if is_pyrvt_tab:
            self._rvtapi_object.Tag = PYREVIT_TAB_IDENTIFIER

        # getting a list of existing panels under this tab
        try:
            for revit_ui_panel in HOST_APP.uiapp.GetRibbonPanels(self.name):
                # feeding _sub_pyrvt_ribbon_panels with an instance of
                # _PyRevitRibbonPanel for existing panels _PyRevitRibbonPanel
                # will find its existing ribbon items internally
                new_pyrvt_panel = _PyRevitRibbonPanel(revit_ui_panel)
                self._add_component(new_pyrvt_panel)
        except:
            # if .GetRibbonPanels fails, this tab is an existing native tab
            raise PyRevitUIError('Can not get panels for this tab: {}'
                                 .format(self._rvtapi_object))

    @staticmethod
    def check_pyrevit_tab(revit_ui_tab):
        return hasattr(revit_ui_tab, 'Tag') \
               and revit_ui_tab.Tag == PYREVIT_TAB_IDENTIFIER

    def is_pyrevit_tab(self):
        return self.get_rvtapi_object().Tag == PYREVIT_TAB_IDENTIFIER

    def update_name(self, new_name):
        self.get_rvtapi_object().Title = new_name

    def create_ribbon_panel(self, panel_name, update_if_exists=False):
        """Create ribbon panel (RevitUI.RibbonPanel) from panel_name."""
        if self.contains(panel_name):
            if update_if_exists:
                exiting_pyrvt_panel = self._get_component(panel_name)
                exiting_pyrvt_panel.activate()
            else:
                raise PyRevitUIError('RibbonPanel already exits and update '
                                     'is not allowed: {}'.format(panel_name))
        else:
            try:
                # creating panel in tab
                ribbon_panel = \
                    HOST_APP.uiapp.CreateRibbonPanel(self.name, panel_name)
                # creating _PyRevitRibbonPanel object and
                # add new panel to list of current panels
                pyrvt_ribbon_panel = _PyRevitRibbonPanel(ribbon_panel)
                pyrvt_ribbon_panel.set_dirty_flag()
                self._add_component(pyrvt_ribbon_panel)

            except Exception as panel_err:
                raise PyRevitUIError('Can not create panel: {}'
                                     .format(panel_err))


class _PyRevitUI(_GenericPyRevitUIContainer):
    """Captures the existing ui state and elements at creation."""

    ribbon_tab = _GenericPyRevitUIContainer._get_component

    def __init__(self):
        _GenericPyRevitUIContainer.__init__(self)

        # Revit does not have any method to get a list of current tabs.
        # Getting a list of current tabs using adwindows.dll methods
        # Iterating over tabs,
        # because ComponentManager.Ribbon.Tabs.FindTab(tab.name)
        # does not return invisible tabs
        for revit_ui_tab in AdWindows.ComponentManager.Ribbon.Tabs:
            # feeding self._sub_pyrvt_ribbon_tabs with an instance of
            # _PyRevitRibbonTab or _RevitNativeRibbonTab for each existing
            # tab. _PyRevitRibbonTab or _RevitNativeRibbonTab will find
            # their existing panels only listing visible tabs
            # (there might be tabs with identical names
            # e.g. there are two Annotate tabs. They are activated as
            # neccessary per context but need to add inactive/invisible
            # pyrevit tabs (PYREVIT_TAB_IDENTIFIER) anyway.
            # if revit_ui_tab.IsVisible
            try:
                if _PyRevitRibbonTab.check_pyrevit_tab(revit_ui_tab):
                    new_pyrvt_tab = _PyRevitRibbonTab(revit_ui_tab)
                else:
                    new_pyrvt_tab = _RevitNativeRibbonTab(revit_ui_tab)
                self._add_component(new_pyrvt_tab)
                logger.debug('Tab added to the list of tabs: {}'
                             .format(new_pyrvt_tab.name))
            except PyRevitUIError:
                # if _PyRevitRibbonTab(revit_ui_tab) fails,
                # Revit restricts access to its panels _RevitNativeRibbonTab
                # uses a different method to access the panels
                # to interact with existing native ui
                new_pyrvt_tab = _RevitNativeRibbonTab(revit_ui_tab)
                self._add_component(new_pyrvt_tab)
                logger.debug('Native tab added to the list of tabs: {}'
                             .format(new_pyrvt_tab.name))

    def get_pyrevit_tabs(self):
        return [tab for tab in self if tab.is_pyrevit_tab()]

    def create_ribbon_tab(self, tab_name, update_if_exists=False):
        if self.contains(tab_name):
            if update_if_exists:
                existing_pyrvt_tab = self._get_component(tab_name)
                existing_pyrvt_tab.activate()
            else:
                raise PyRevitUIError('RibbonTab already exits and update is '
                                     'not allowed: {}'.format(tab_name))
        else:
            try:
                # creating tab in Revit ui
                HOST_APP.uiapp.CreateRibbonTab(tab_name)
                # HOST_APP.uiapp.CreateRibbonTab() does
                # not return the created tab object.
                # so find the tab object in exiting ui
                revit_tab_ctrl = None
                for exiting_rvt_ribbon_tab in AdWindows.ComponentManager.Ribbon.Tabs:
                    if exiting_rvt_ribbon_tab.Title == tab_name:
                        revit_tab_ctrl = exiting_rvt_ribbon_tab

                # create _PyRevitRibbonTab object with
                # the recovered RibbonTab object
                # and add new _PyRevitRibbonTab to list of current tabs
                if revit_tab_ctrl:
                    pyrvt_ribbon_tab = _PyRevitRibbonTab(revit_tab_ctrl,
                                                         is_pyrvt_tab=True)
                    pyrvt_ribbon_tab.set_dirty_flag()
                    self._add_component(pyrvt_ribbon_tab)
                else:
                    raise PyRevitUIError('Tab created but can not '
                                         'be obtained from ui.')

            except Exception as tab_create_err:
                raise PyRevitUIError('Can not create tab: {}'
                                     .format(tab_create_err))


# Public function to return an instance of _PyRevitUI which is used
# to interact with current ui --------------------------------------------------
def get_current_ui():
    """Revit UI Wrapper class for interacting with current pyRevit UI.
    Returned class provides min required functionality for user interaction

    :Example:

        current_ui = pyrevit.session.current_ui()
        this_script = pyrevit.session.get_this_command()
        current_ui.update_button_icon(this_script, new_icon)

    :return: Returns an instance of _PyRevitUI that contains info on current ui
    :rtype: _PyRevitUI
    """
    return _PyRevitUI()


def get_uibutton(command_unique_name):
    pyrvt_tabs = get_current_ui().get_pyrevit_tabs()
    for tab in pyrvt_tabs:
        button = tab.find_child(command_unique_name)
        if button:
            return button
    return None
