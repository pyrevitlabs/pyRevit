"""Base module to interact with Revit ribbon."""
from collections import OrderedDict

#pylint: disable=W0703,C0302,C0103
from pyrevit import HOST_APP, EXEC_PARAMS, PyRevitException
from pyrevit.compat import safe_strtype
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars
from pyrevit.framework import System, Uri, Windows
from pyrevit.framework import IO
from pyrevit.framework import Imaging
from pyrevit.framework import BindingFlags
from pyrevit.framework import Media, Convert
from pyrevit.api import UI, AdWindows, AdInternal
from pyrevit.runtime import types
from pyrevit.revit import ui


mlogger = get_logger(__name__)


PYREVIT_TAB_IDENTIFIER = 'pyrevit_tab'

ICON_SMALL = 16
ICON_MEDIUM = 24
ICON_LARGE = 32

DEFAULT_DPI = 96

DEFAULT_TOOLTIP_IMAGE_FORMAT = '.png'
DEFAULT_TOOLTIP_VIDEO_FORMAT = '.swf'
if HOST_APP.is_newer_than(2019, or_equal=True):
    DEFAULT_TOOLTIP_VIDEO_FORMAT = '.mp4'


def argb_to_brush(argb_color):
    # argb_color is formatted as #AARRGGBB
    a = r = g = b = "FF"
    try:
        b = argb_color[-2:]
        g = argb_color[-4:-2]
        r = argb_color[-6:-4]
        if len(argb_color) > 7:
            a = argb_color[-8:-6]
        return Media.SolidColorBrush(Media.Color.FromArgb(
                Convert.ToInt32("0x" + a, 16),
                Convert.ToInt32("0x" + r, 16),
                Convert.ToInt32("0x" + g, 16),
                Convert.ToInt32("0x" + b, 16)
                )
            )
    except Exception as color_ex:
        mlogger.error("Bad color format %s | %s", argb_color, color_ex)


def load_bitmapimage(image_file):
    """Load given png file.

    Args:
        image_file (str): image file path

    Returns:
        (Imaging.BitmapImage): bitmap image object
    """
    bitmap = Imaging.BitmapImage()
    bitmap.BeginInit()
    bitmap.UriSource = Uri(image_file)
    bitmap.CacheOption = Imaging.BitmapCacheOption.OnLoad
    bitmap.CreateOptions = Imaging.BitmapCreateOptions.IgnoreImageCache
    bitmap.EndInit()
    bitmap.Freeze()
    return bitmap


# Helper classes and functions -------------------------------------------------
class PyRevitUIError(PyRevitException):
    """Common base class for all pyRevit ui-related exceptions."""
    pass


class ButtonIcons(object):
    """pyRevit ui element icon.

    Upon init, this type reads the given image file into an io stream and
    releases the os lock on the file.

    Args:
        image_file (str): image file path to be used as icon

    Attributes:
        icon_file_path (str): icon image file path
        filestream (IO.FileStream): io stream containing image binary data
    """
    def __init__(self, image_file):
        self.icon_file_path = image_file
        self.check_icon_size()
        self.filestream = IO.FileStream(image_file,
                                        IO.FileMode.Open,
                                        IO.FileAccess.Read)

    @staticmethod
    def recolour(image_data, size, stride, color):
        # FIXME: needs doc, and argument types
        # ButtonIcons.recolour(image_data, image_size, stride, 0x8e44ad)
        step = stride / size
        for i in range(0, stride, step):
            for j in range(0, stride, step):
                idx = (i * size) + j
                # R = image_data[idx+2]
                # G = image_data[idx+1]
                # B = image_data[idx]
                # luminance = (0.299*R + 0.587*G + 0.114*B)
                image_data[idx] = color >> 0 & 0xff       # blue
                image_data[idx+1] = color >> 8 & 0xff     # green
                image_data[idx+2] = color >> 16 & 0xff    # red

    def check_icon_size(self):
        """Verify icon size is within acceptable range."""
        image = System.Drawing.Image.FromFile(self.icon_file_path)
        image_size = max(image.Width, image.Height)
        if image_size > 96:
            mlogger.warning('Icon file is too large. Large icons adversely '
                            'affect the load time since they need to be '
                            'processed and adjusted for screen scaling. '
                            'Keep icons at max 96x96 pixels: %s',
                            self.icon_file_path)

    def create_bitmap(self, icon_size):
        """Resamples image and creates bitmap for the given size.

        Icons are assumed to be square.

        Args:
            icon_size (int): icon size (width or height)

        Returns:
            (Imaging.BitmapSource): object containing image data at given size
        """
        mlogger.debug('Creating %sx%s bitmap from: %s',
                      icon_size, icon_size, self.icon_file_path)
        adjusted_icon_size = icon_size * 2
        adjusted_dpi = DEFAULT_DPI * 2
        screen_scaling = HOST_APP.proc_screen_scalefactor

        self.filestream.Seek(0, IO.SeekOrigin.Begin)
        base_image = Imaging.BitmapImage()
        base_image.BeginInit()
        base_image.StreamSource = self.filestream
        base_image.DecodePixelHeight = int(adjusted_icon_size * screen_scaling)
        base_image.EndInit()
        self.filestream.Seek(0, IO.SeekOrigin.Begin)

        image_size = base_image.PixelWidth
        image_format = base_image.Format
        image_byte_per_pixel = int(base_image.Format.BitsPerPixel / 8)
        palette = base_image.Palette

        stride = int(image_size * image_byte_per_pixel)
        array_size = stride * image_size
        image_data = System.Array.CreateInstance(System.Byte, array_size)
        base_image.CopyPixels(image_data, stride, 0)

        scaled_size = int(adjusted_icon_size * screen_scaling)
        scaled_dpi = int(adjusted_dpi * screen_scaling)
        bitmap_source = \
            Imaging.BitmapSource.Create(scaled_size, scaled_size,
                                        scaled_dpi, scaled_dpi,
                                        image_format,
                                        palette,
                                        image_data,
                                        stride)
        return bitmap_source

    @property
    def small_bitmap(self):
        """Resamples image and creates bitmap for size :obj:`ICON_SMALL`.

        Returns:
            (Imaging.BitmapSource): object containing image data at given size
        """
        return self.create_bitmap(ICON_SMALL)

    @property
    def medium_bitmap(self):
        """Resamples image and creates bitmap for size :obj:`ICON_MEDIUM`.

        Returns:
            (Imaging.BitmapSource): object containing image data at given size
        """
        return self.create_bitmap(ICON_MEDIUM)

    @property
    def large_bitmap(self):
        """Resamples image and creates bitmap for size :obj:`ICON_LARGE`.

        Returns:
            (Imaging.BitmapSource): object containing image data at given size
        """
        return self.create_bitmap(ICON_LARGE)


# Superclass to all ui item classes --------------------------------------------
class GenericPyRevitUIContainer(object):
    """Common type for all pyRevit ui containers.

    Attributes:
        name (str): container name
        itemdata_mode (bool): if container is wrapping UI.*ItemData
    """
    def __init__(self):
        self.name = ''
        self._rvtapi_object = None
        self._sub_pyrvt_components = OrderedDict()
        self.itemdata_mode = False
        self._dirty = False
        self._visible = None
        self._enabled = None

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

    @property
    def visible(self):
        """Is container visible."""
        if hasattr(self._rvtapi_object, 'Visible'):
            return self._rvtapi_object.Visible
        elif hasattr(self._rvtapi_object, 'IsVisible'):
            return self._rvtapi_object.IsVisible
        else:
            return self._visible

    @visible.setter
    def visible(self, value):
        if hasattr(self._rvtapi_object, 'Visible'):
            self._rvtapi_object.Visible = value
        elif hasattr(self._rvtapi_object, 'IsVisible'):
            self._rvtapi_object.IsVisible = value
        else:
            self._visible = value

    @property
    def enabled(self):
        """Is container enabled."""
        if hasattr(self._rvtapi_object, 'Enabled'):
            return self._rvtapi_object.Enabled
        elif hasattr(self._rvtapi_object, 'IsEnabled'):
            return self._rvtapi_object.IsEnabled
        else:
            return self._enabled

    @enabled.setter
    def enabled(self, value):
        if hasattr(self._rvtapi_object, 'Enabled'):
            self._rvtapi_object.Enabled = value
        elif hasattr(self._rvtapi_object, 'IsEnabled'):
            self._rvtapi_object.IsEnabled = value
        else:
            self._enabled = value

    def process_deferred(self):
        try:
            if self._visible is not None:
                self.visible = self._visible
        except Exception as visible_err:
            raise PyRevitUIError('Error setting .visible {} | {} '
                                 .format(self, visible_err))

        try:
            if self._enabled is not None:
                self.enabled = self._enabled
        except Exception as enable_err:
            raise PyRevitUIError('Error setting .enabled {} | {} '
                                 .format(self, enable_err))

    def get_rvtapi_object(self):
        """Return underlying Revit API object for this container."""
        # FIXME: return type
        return self._rvtapi_object

    def set_rvtapi_object(self, rvtapi_obj):
        """Set underlying Revit API object for this container.

        Args:
            rvtapi_obj (obj): Revit API container object
        """
        # FIXME: rvtapi_obj type
        self._rvtapi_object = rvtapi_obj
        self.itemdata_mode = False
        self._dirty = True

    def get_adwindows_object(self):
        """Return underlying AdWindows API object for this container."""
        # FIXME: return type
        rvtapi_obj = self._rvtapi_object
        getRibbonItemMethod = \
            rvtapi_obj.GetType().GetMethod(
                'getRibbonItem',
                BindingFlags.NonPublic | BindingFlags.Instance
                )
        if getRibbonItemMethod:
            return getRibbonItemMethod.Invoke(rvtapi_obj, None)

    def get_flagged_children(self, state=True):
        """Get all children with their flag equal to given state.

        Flagging is a mechanism to mark certain containers. There are various
        reasons that container flagging might be used e.g. marking updated
        containers or the ones in need of an update or removal.

        Args:
            state (bool): flag state to filter children

        Returns:
            (list[*]): list of filtered child objects
        """
        # FIXME: return type
        flagged_cmps = []
        for component in self:
            flagged_cmps.extend(component.get_flagged_children(state))
            if component.is_dirty() == state:
                flagged_cmps.append(component)
        return flagged_cmps

    def keys(self):
        # FIXME: what does this do?
        list(self._sub_pyrvt_components.keys())

    def values(self):
        # FIXME: what does this do?
        list(self._sub_pyrvt_components.values())

    @staticmethod
    def is_native():
        """Is this container generated by pyRevit or is native."""
        return False

    def is_dirty(self):
        """Is dirty flag set."""
        if self._dirty:
            return self._dirty
        else:
            # check if there is any dirty child
            for component in self:
                if component.is_dirty():
                    return True
            return False

    def set_dirty_flag(self, state=True):
        """Set dirty flag to given state.

        See .get_flagged_children()

        Args:
            state (bool): state to set flag
        """
        self._dirty = state

    def contains(self, pyrvt_cmp_name):
        """Check if container contains a component with given name.

        Args:
            pyrvt_cmp_name (str): target component name
        """
        return pyrvt_cmp_name in self._sub_pyrvt_components.keys()

    def find_child(self, child_name):
        """Find a component with given name in children.

        Args:
            child_name (str): target component name

        Returns:
            (Any): component object if found, otherwise None
        """
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
        """Activate this container in ui."""
        try:
            self.enabled = True
            self.visible = True
            self._dirty = True
        except Exception:
            raise PyRevitUIError('Can not activate: {}'.format(self))

    def deactivate(self):
        """Deactivate this container in ui."""
        try:
            self.enabled = False
            self.visible = False
            self._dirty = True
        except Exception:
            raise PyRevitUIError('Can not deactivate: {}'.format(self))

    def get_updated_items(self):
        # FIXME: reduntant, this is a use case and should be on uimaker side?
        return self.get_flagged_children()

    def get_unchanged_items(self):
        # FIXME: reduntant, this is a use case and should be on uimaker side?
        return self.get_flagged_children(state=False)

    def reorder_before(self, item_name, ritem_name):
        """Reorder and place item_name before ritem_name.

        Args:
            item_name (str): name of component to be moved
            ritem_name (str): name of component that should be on the right
        """
        apiobj = self.get_rvtapi_object()
        litem_idx = ritem_idx = None
        if hasattr(apiobj, 'Panels'):
            for item in apiobj.Panels:
                if item.Source.AutomationName == item_name:
                    litem_idx = apiobj.Panels.IndexOf(item)
                elif item.Source.AutomationName == ritem_name:
                    ritem_idx = apiobj.Panels.IndexOf(item)
            if litem_idx and ritem_idx:
                if litem_idx < ritem_idx:
                    apiobj.Panels.Move(litem_idx, ritem_idx - 1)
                elif litem_idx > ritem_idx:
                    apiobj.Panels.Move(litem_idx, ritem_idx)

    def reorder_beforeall(self, item_name):
        """Reorder and place item_name before all others.

        Args:
            item_name (str): name of component to be moved
        """
        # FIXME: verify docs description is correct
        apiobj = self.get_rvtapi_object()
        litem_idx = None
        if hasattr(apiobj, 'Panels'):
            for item in apiobj.Panels:
                if item.Source.AutomationName == item_name:
                    litem_idx = apiobj.Panels.IndexOf(item)
            if litem_idx:
                apiobj.Panels.Move(litem_idx, 0)

    def reorder_after(self, item_name, ritem_name):
        """Reorder and place item_name after ritem_name.

        Args:
            item_name (str): name of component to be moved
            ritem_name (str): name of component that should be on the left
        """
        apiobj = self.get_rvtapi_object()
        litem_idx = ritem_idx = None
        if hasattr(apiobj, 'Panels'):
            for item in apiobj.Panels:
                if item.Source.AutomationName == item_name:
                    litem_idx = apiobj.Panels.IndexOf(item)
                elif item.Source.AutomationName == ritem_name:
                    ritem_idx = apiobj.Panels.IndexOf(item)
            if litem_idx and ritem_idx:
                if litem_idx < ritem_idx:
                    apiobj.Panels.Move(litem_idx, ritem_idx)
                elif litem_idx > ritem_idx:
                    apiobj.Panels.Move(litem_idx, ritem_idx + 1)

    def reorder_afterall(self, item_name):
        """Reorder and place item_name after all others.

        Args:
            item_name (str): name of component to be moved
        """
        apiobj = self.get_rvtapi_object()
        litem_idx = None
        if hasattr(apiobj, 'Panels'):
            for item in apiobj.Panels:
                if item.Source.AutomationName == item_name:
                    litem_idx = apiobj.Panels.IndexOf(item)
            if litem_idx:
                max_idx = len(apiobj.Panels) - 1
                apiobj.Panels.Move(litem_idx, max_idx)


# Classes holding existing native ui elements
# (These elements are native and can not be modified) --------------------------
class GenericRevitNativeUIContainer(GenericPyRevitUIContainer):
    """Common base type for native Revit API UI containers."""
    def __init__(self):
        GenericPyRevitUIContainer.__init__(self)

    @staticmethod
    def is_native():
        """Is this container generated by pyRevit or is native."""
        return True

    def activate(self):
        """Activate this container in ui.

        Under current implementation, raises PyRevitUIError exception as
        native Revit API UI components should not be changed.
        """
        return self.deactivate()

    def deactivate(self):
        """Deactivate this container in ui.

        Under current implementation, raises PyRevitUIError exception as
        native Revit API UI components should not be changed.
        """
        raise PyRevitUIError('Can not de/activate native item: {}'
                             .format(self))


class RevitNativeRibbonButton(GenericRevitNativeUIContainer):
    """Revit API UI native ribbon button."""
    def __init__(self, adwnd_ribbon_button):
        GenericRevitNativeUIContainer.__init__(self)

        self.name = \
            safe_strtype(adwnd_ribbon_button.AutomationName)\
            .replace('\r\n', ' ')
        self._rvtapi_object = adwnd_ribbon_button


class RevitNativeRibbonGroupItem(GenericRevitNativeUIContainer):
    """Revit API UI native ribbon button."""
    def __init__(self, adwnd_ribbon_item):
        GenericRevitNativeUIContainer.__init__(self)

        self.name = adwnd_ribbon_item.Source.Title
        self._rvtapi_object = adwnd_ribbon_item

        # finding children on this button group
        for adwnd_ribbon_button in adwnd_ribbon_item.Items:
            self._add_component(RevitNativeRibbonButton(adwnd_ribbon_button))

    def button(self, name):
        """Get button item with given name.

        Args:
            name (str): name of button item to find

        Returns:
            (RevitNativeRibbonButton): button object if found
        """
        return super(RevitNativeRibbonGroupItem, self)._get_component(name)


class RevitNativeRibbonPanel(GenericRevitNativeUIContainer):
    """Revit API UI native ribbon button."""
    def __init__(self, adwnd_ribbon_panel):
        GenericRevitNativeUIContainer.__init__(self)

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
                    mlogger.debug('Can not get RibbonFoldPanel children: %s '
                                  '| %s', adwnd_ribbon_item, append_err)
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
                        RevitNativeRibbonButton(adwnd_ribbon_item))
                elif isinstance(adwnd_ribbon_item,
                                AdWindows.RibbonSplitButton):
                    self._add_component(
                        RevitNativeRibbonGroupItem(adwnd_ribbon_item))

            except Exception as append_err:
                mlogger.debug('Can not create native ribbon item: %s '
                              '| %s', adwnd_ribbon_item, append_err)

    def ribbon_item(self, item_name):
        """Get panel item with given name.

        Args:
            item_name (str): name of panel item to find

        Returns:
            (object):
                panel item if found, could be :obj:`RevitNativeRibbonButton`
                or :obj:`RevitNativeRibbonGroupItem`
        """
        return super(RevitNativeRibbonPanel, self)._get_component(item_name)


class RevitNativeRibbonTab(GenericRevitNativeUIContainer):
    """Revit API UI native ribbon tab."""
    def __init__(self, adwnd_ribbon_tab):
        GenericRevitNativeUIContainer.__init__(self)

        self.name = adwnd_ribbon_tab.Title
        self._rvtapi_object = adwnd_ribbon_tab

        # getting a list of existing panels under this tab
        try:
            for adwnd_ribbon_panel in adwnd_ribbon_tab.Panels:
                # only listing visible panels
                if adwnd_ribbon_panel.IsVisible:
                    self._add_component(
                        RevitNativeRibbonPanel(adwnd_ribbon_panel)
                    )
        except Exception as append_err:
            mlogger.debug('Can not get native panels for this native tab: %s '
                          '| %s', adwnd_ribbon_tab, append_err)

    def ribbon_panel(self, panel_name):
        """Get panel with given name.

        Args:
            panel_name (str): name of panel to find

        Returns:
            (RevitNativeRibbonPanel): panel if found
        """
        return super(RevitNativeRibbonTab, self)._get_component(panel_name)

    @staticmethod
    def is_pyrevit_tab():
        """Is this tab generated by pyRevit."""
        return False


# Classes holding non-native ui elements --------------------------------------
class _PyRevitSeparator(GenericPyRevitUIContainer):
    def __init__(self):
        GenericPyRevitUIContainer.__init__(self)
        self.name = coreutils.new_uuid()
        self.itemdata_mode = True


class _PyRevitRibbonButton(GenericPyRevitUIContainer):
    def __init__(self, ribbon_button):
        GenericPyRevitUIContainer.__init__(self)

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

        self.tooltip_image = self.tooltip_video = None

    def set_rvtapi_object(self, rvtapi_obj):
        GenericPyRevitUIContainer.set_rvtapi_object(self, rvtapi_obj)
        # update the ui title for the newly added rvtapi_obj
        self._rvtapi_object.ItemText = self.ui_title

    def set_icon(self, icon_file, icon_size=ICON_MEDIUM):
        try:
            button_icon = ButtonIcons(icon_file)
            rvtapi_obj = self.get_rvtapi_object()
            rvtapi_obj.Image = button_icon.small_bitmap
            if icon_size == ICON_LARGE:
                rvtapi_obj.LargeImage = button_icon.large_bitmap
            else:
                rvtapi_obj.LargeImage = button_icon.medium_bitmap
            self._dirty = True
        except Exception as icon_err:
            raise PyRevitUIError('Error in applying icon to button > {} : {}'
                                 .format(icon_file, icon_err))

    def set_tooltip(self, tooltip):
        try:
            if tooltip:
                self.get_rvtapi_object().ToolTip = tooltip
            else:
                adwindows_obj = self.get_adwindows_object()
                if adwindows_obj and adwindows_obj.ToolTip:
                    adwindows_obj.ToolTip.Content = None
            self._dirty = True
        except Exception as tooltip_err:
            raise PyRevitUIError('Item does not have tooltip property: {}'
                                 .format(tooltip_err))

    def set_tooltip_ext(self, tooltip_ext):
        try:
            if tooltip_ext:
                self.get_rvtapi_object().LongDescription = tooltip_ext
            else:
                adwindows_obj = self.get_adwindows_object()
                if adwindows_obj and adwindows_obj.ToolTip:
                    adwindows_obj.ToolTip.ExpandedContent = None
            self._dirty = True
        except Exception as tooltip_err:
            raise PyRevitUIError('Item does not have extended '
                                 'tooltip property: {}'.format(tooltip_err))

    def set_tooltip_image(self, tooltip_image):
        try:
            adwindows_obj = self.get_adwindows_object()
            if adwindows_obj:
                exToolTip = self.get_rvtapi_object().ToolTip
                if not isinstance(exToolTip, str):
                    exToolTip = None
                adwindows_obj.ToolTip = AdWindows.RibbonToolTip()
                adwindows_obj.ToolTip.Title = self.ui_title
                adwindows_obj.ToolTip.Content = exToolTip
                _StackPanel = System.Windows.Controls.StackPanel()
                _image = System.Windows.Controls.Image()
                _image.Source = load_bitmapimage(tooltip_image)
                _StackPanel.Children.Add(_image)
                adwindows_obj.ToolTip.ExpandedContent = _StackPanel
                adwindows_obj.ResolveToolTip()
            else:
                self.tooltip_image = tooltip_image
        except Exception as ttimage_err:
            raise PyRevitUIError('Error setting tooltip image {} | {} '
                                 .format(tooltip_image, ttimage_err))

    def set_tooltip_video(self, tooltip_video):
        try:
            adwindows_obj = self.get_adwindows_object()
            if adwindows_obj:
                exToolTip = self.get_rvtapi_object().ToolTip
                if not isinstance(exToolTip, str):
                    exToolTip = None
                adwindows_obj.ToolTip = AdWindows.RibbonToolTip()
                adwindows_obj.ToolTip.Title = self.ui_title
                adwindows_obj.ToolTip.Content = exToolTip
                _StackPanel = System.Windows.Controls.StackPanel()
                _video = System.Windows.Controls.MediaElement()
                _video.Source = Uri(tooltip_video)
                _video.LoadedBehavior = System.Windows.Controls.MediaState.Manual
                _video.UnloadedBehavior = System.Windows.Controls.MediaState.Manual

                def on_media_ended(sender, args):
                    sender.Position = System.TimeSpan.Zero
                    sender.Play()
                _video.MediaEnded += on_media_ended

                def on_loaded(sender, args):
                    sender.Play()
                _video.Loaded += on_loaded
                _StackPanel.Children.Add(_video)
                adwindows_obj.ToolTip.ExpandedContent = _StackPanel
                adwindows_obj.ResolveToolTip()
            else:
                self.tooltip_video = tooltip_video
        except Exception as ttvideo_err:
            raise PyRevitUIError('Error setting tooltip video {} | {} '
                                 .format(tooltip_video, ttvideo_err))

    def set_tooltip_media(self, tooltip_media):
        if tooltip_media.endswith(DEFAULT_TOOLTIP_IMAGE_FORMAT):
            self.set_tooltip_image(tooltip_media)
        elif tooltip_media.endswith(DEFAULT_TOOLTIP_VIDEO_FORMAT):
            self.set_tooltip_video(tooltip_media)

    def reset_highlights(self):
        if hasattr(AdInternal.Windows, 'HighlightMode'):
            adwindows_obj = self.get_adwindows_object()
            if adwindows_obj:
                adwindows_obj.Highlight = \
                    coreutils.get_enum_none(AdInternal.Windows.HighlightMode)

    def highlight_as_new(self):
        if hasattr(AdInternal.Windows, 'HighlightMode'):
            adwindows_obj = self.get_adwindows_object()
            if adwindows_obj:
                adwindows_obj.Highlight = \
                    AdInternal.Windows.HighlightMode.New

    def highlight_as_updated(self):
        if hasattr(AdInternal.Windows, 'HighlightMode'):
            adwindows_obj = self.get_adwindows_object()
            if adwindows_obj:
                adwindows_obj.Highlight = \
                    AdInternal.Windows.HighlightMode.Updated

    def process_deferred(self):
        GenericPyRevitUIContainer.process_deferred(self)

        try:
            if self.tooltip_image:
                self.set_tooltip_image(self.tooltip_image)
        except Exception as ttvideo_err:
            raise PyRevitUIError('Error setting deffered tooltip image {} | {} '
                                 .format(self.tooltip_video, ttvideo_err))

        try:
            if self.tooltip_video:
                self.set_tooltip_video(self.tooltip_video)
        except Exception as ttvideo_err:
            raise PyRevitUIError('Error setting deffered tooltip video {} | {} '
                                 .format(self.tooltip_video, ttvideo_err))

    def get_contexthelp(self):
        return self.get_rvtapi_object().GetContextualHelp()

    def set_contexthelp(self, ctxhelpurl):
        if ctxhelpurl:
            ch = UI.ContextualHelp(UI.ContextualHelpType.Url, ctxhelpurl)
            self.get_rvtapi_object().SetContextualHelp(ch)

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

    def get_control_id(self):
        adwindows_obj = self.get_adwindows_object()
        if adwindows_obj and hasattr(adwindows_obj, 'Id'):
            return getattr(adwindows_obj, 'Id', '')

    @property
    def assembly_name(self):
        return self._rvtapi_object.AssemblyName

    @property
    def class_name(self):
        return self._rvtapi_object.ClassName

    @property
    def availability_class_name(self):
        return self._rvtapi_object.AvailabilityClassName


class _PyRevitRibbonGroupItem(GenericPyRevitUIContainer):

    button = GenericPyRevitUIContainer._get_component

    def __init__(self, ribbon_item):
        GenericPyRevitUIContainer.__init__(self)

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
        self._use_active_item_icon = self.is_splitbutton()

        # by default the last item used, stays on top as the default button
        self._sync_with_cur_item = True

        # getting a list of existing items under this item group.
        if not self.itemdata_mode:
            for revit_button in ribbon_item.GetItems():
                # feeding _sub_native_ribbon_items with an instance of
                # _PyRevitRibbonButton for existing buttons
                self._add_component(_PyRevitRibbonButton(revit_button))

    def is_splitbutton(self):
        return isinstance(self._rvtapi_object, UI.SplitButton) \
               or isinstance(self._rvtapi_object, UI.SplitButtonData)

    def set_rvtapi_object(self, rvtapi_obj):
        GenericPyRevitUIContainer.set_rvtapi_object(self, rvtapi_obj)
        if self.is_splitbutton():
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

                # extended tooltips (images and videos) can only be applied when
                # the ui element is created
                pyrvt_ui_item.process_deferred()

            elif isinstance(pyrvt_ui_item, _PyRevitSeparator):
                self.get_rvtapi_object().AddSeparator()

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

    def set_icon(self, icon_file, icon_size=ICON_LARGE):
        try:
            button_icon = ButtonIcons(icon_file)
            rvtapi_obj = self.get_rvtapi_object()
            rvtapi_obj.Image = button_icon.small_bitmap
            if icon_size == ICON_LARGE:
                rvtapi_obj.LargeImage = button_icon.large_bitmap
            else:
                rvtapi_obj.LargeImage = button_icon.medium_bitmap
            self._dirty = True
        except Exception as icon_err:
            raise PyRevitUIError('Error in applying icon to button > {} : {}'
                                 .format(icon_file, icon_err))

    def get_contexthelp(self):
        return self.get_rvtapi_object().GetContextualHelp()

    def set_contexthelp(self, ctxhelpurl):
        if ctxhelpurl:
            ch = UI.ContextualHelp(UI.ContextualHelpType.Url, ctxhelpurl)
            self.get_rvtapi_object().SetContextualHelp(ch)

    def reset_highlights(self):
        if hasattr(AdInternal.Windows, 'HighlightMode'):
            adwindows_obj = self.get_adwindows_object()
            if adwindows_obj:
                adwindows_obj.HighlightDropDown = \
                    coreutils.get_enum_none(AdInternal.Windows.HighlightMode)

    def highlight_as_new(self):
        if hasattr(AdInternal.Windows, 'HighlightMode'):
            adwindows_obj = self.get_adwindows_object()
            if adwindows_obj:
                adwindows_obj.HighlightDropDown = \
                    AdInternal.Windows.HighlightMode.New

    def highlight_as_updated(self):
        if hasattr(AdInternal.Windows, 'HighlightMode'):
            adwindows_obj = self.get_adwindows_object()
            if adwindows_obj:
                adwindows_obj.HighlightDropDown = \
                    AdInternal.Windows.HighlightMode.Updated

    def create_push_button(self, button_name, asm_location, class_name,
                           icon_path='',
                           tooltip='', tooltip_ext='', tooltip_media='',
                           ctxhelpurl=None,
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
                    mlogger.debug('Error updating button asm info: %s '
                                  '| %s', button_name, asm_update_err)

                if not icon_path:
                    mlogger.debug('Icon not set for %s', button_name)
                else:
                    try:
                        # if button group shows the active button icon,
                        # then the child buttons need to have large icons
                        existing_item.set_icon(icon_path,
                                               icon_size=ICON_LARGE
                                               if self._use_active_item_icon
                                               else ICON_MEDIUM)
                    except PyRevitUIError as iconerr:
                        mlogger.error('Error adding icon for %s | %s',
                                      button_name, iconerr)

                existing_item.set_tooltip(tooltip)
                existing_item.set_tooltip_ext(tooltip_ext)
                if tooltip_media:
                    existing_item.set_tooltip_media(tooltip_media)

                # if ctx help on this group matches the existing,
                # update self ctx before changing the existing item ctx help
                self_ctxhelp = self.get_contexthelp()
                ctx_help = existing_item.get_contexthelp()
                if self_ctxhelp and ctx_help \
                        and self_ctxhelp.HelpType == ctx_help.HelpType \
                        and self_ctxhelp.HelpPath == ctx_help.HelpPath:
                    self.set_contexthelp(ctxhelpurl)
                # now change the existing item ctx help
                existing_item.set_contexthelp(ctxhelpurl)

                if ui_title:
                    existing_item.set_title(ui_title)

                existing_item.activate()
                return
            else:
                raise PyRevitUIError('Push button already exits and update '
                                     'is not allowed: {}'.format(button_name))

        mlogger.debug('Parent does not include this button. Creating: %s',
                      button_name)
        try:
            button_data = \
                UI.PushButtonData(button_name,
                                  button_name,
                                  asm_location,
                                  class_name)
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
                mlogger.debug('Icon not set for %s', button_name)
            else:
                mlogger.debug('Creating icon for push button %s from file: %s',
                              button_name, icon_path)
                try:
                    # if button group shows the active button icon,
                    # then the child buttons need to have large icons
                    new_button.set_icon(
                        icon_path,
                        icon_size=ICON_LARGE
                        if self._use_active_item_icon else ICON_MEDIUM)
                except PyRevitUIError as iconerr:
                    mlogger.debug('Error adding icon for %s from %s '
                                  '| %s', button_name, icon_path, iconerr)

            new_button.set_tooltip(tooltip)
            new_button.set_tooltip_ext(tooltip_ext)
            if tooltip_media:
                new_button.set_tooltip_media(tooltip_media)

            new_button.set_contexthelp(ctxhelpurl)
            # if this is the first button being added
            if not self.keys():
                mlogger.debug('Setting ctx help on parent: %s', ctxhelpurl)
                self.set_contexthelp(ctxhelpurl)

            new_button.set_dirty_flag()
            self._add_component(new_button)

        except Exception as create_err:
            raise PyRevitUIError('Can not create button '
                                 '| {}'.format(create_err))

    def add_separator(self):
        if not self.itemdata_mode:
            self.get_rvtapi_object().AddSeparator()
        else:
            sep_cmp = _PyRevitSeparator()
            self._add_component(sep_cmp)
        self._dirty = True


class _PyRevitRibbonPanel(GenericPyRevitUIContainer):

    button = GenericPyRevitUIContainer._get_component
    ribbon_item = GenericPyRevitUIContainer._get_component

    def __init__(self, rvt_ribbon_panel, parent_tab):
        GenericPyRevitUIContainer.__init__(self)

        self.name = rvt_ribbon_panel.Name
        self._rvtapi_object = rvt_ribbon_panel

        self.parent_tab = parent_tab

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

    def get_adwindows_object(self):
        for panel in self.parent_tab.Panels:
            if panel.Source and panel.Source.Title == self.name:
                return panel

    def set_background(self, argb_color):
        panel_adwnd_obj = self.get_adwindows_object()
        color = argb_to_brush(argb_color)
        panel_adwnd_obj.CustomPanelBackground = color
        panel_adwnd_obj.CustomPanelTitleBarBackground = color
        panel_adwnd_obj.CustomSlideOutPanelBackground = color

    def reset_backgrounds(self):
        panel_adwnd_obj = self.get_adwindows_object()
        panel_adwnd_obj.CustomPanelBackground = None
        panel_adwnd_obj.CustomPanelTitleBarBackground = None
        panel_adwnd_obj.CustomSlideOutPanelBackground = None

    def set_panel_background(self, argb_color):
        panel_adwnd_obj = self.get_adwindows_object()
        panel_adwnd_obj.CustomPanelBackground = \
            argb_to_brush(argb_color)

    def set_title_background(self, argb_color):
        panel_adwnd_obj = self.get_adwindows_object()
        panel_adwnd_obj.CustomPanelTitleBarBackground = \
            argb_to_brush(argb_color)

    def set_slideout_background(self, argb_color):
        panel_adwnd_obj = self.get_adwindows_object()
        panel_adwnd_obj.CustomSlideOutPanelBackground = \
            argb_to_brush(argb_color)

    def reset_highlights(self):
        # no highlighting options for panels
        pass

    def highlight_as_new(self):
        # no highlighting options for panels
        pass

    def highlight_as_updated(self):
        # no highlighting options for panels
        pass

    def get_collapse(self):
        panel_adwnd_obj = self.get_adwindows_object()
        return panel_adwnd_obj.IsCollapsed

    def set_collapse(self, state):
        panel_adwnd_obj = self.get_adwindows_object()
        panel_adwnd_obj.IsCollapsed = state

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
        # FIXME: if one item changes in stack and others dont change,
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
            mlogger.debug('No new items has been added to stack. '
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

            # extended tooltips (images and videos) can only be applied when
            # the ui element is created
            if isinstance(pyrvt_ui_item, _PyRevitRibbonButton):
                pyrvt_ui_item.process_deferred()

            # if pyrvt_ui_item is a group,
            # create children and update group item data
            if isinstance(pyrvt_ui_item, _PyRevitRibbonGroupItem):
                pyrvt_ui_item.create_data_items()

    def set_dlglauncher(self, dlg_button):
        panel_adwnd_obj = self.get_adwindows_object()
        button_adwnd_obj = dlg_button.get_adwindows_object()
        panel_adwnd_obj.Source.Items.Remove(button_adwnd_obj)
        panel_adwnd_obj.Source.DialogLauncher = button_adwnd_obj
        mlogger.debug('Added panel dialog button %s', dlg_button.name)

    def create_push_button(self, button_name, asm_location, class_name,
                           icon_path='',
                           tooltip='', tooltip_ext='', tooltip_media='',
                           ctxhelpurl=None,
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
                    mlogger.debug('Error updating button asm info: %s '
                                  '| %s', button_name, asm_update_err)

                existing_item.set_tooltip(tooltip)
                existing_item.set_tooltip_ext(tooltip_ext)
                if tooltip_media:
                    existing_item.set_tooltip_media(tooltip_media)

                existing_item.set_contexthelp(ctxhelpurl)

                if ui_title:
                    existing_item.set_title(ui_title)

                if not icon_path:
                    mlogger.debug('Icon not set for %s', button_name)
                else:
                    try:
                        existing_item.set_icon(icon_path, icon_size=ICON_LARGE)
                    except PyRevitUIError as iconerr:
                        mlogger.error('Error adding icon for %s '
                                      '| %s', button_name, iconerr)
                existing_item.activate()
            else:
                raise PyRevitUIError('Push button already exits and update '
                                     'is not allowed: {}'.format(button_name))
        else:
            mlogger.debug('Parent does not include this button. Creating: %s',
                          button_name)
            try:
                button_data = \
                    UI.PushButtonData(button_name,
                                      button_name,
                                      asm_location,
                                      class_name)
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
                    mlogger.debug('Parent ui item is a panel and '
                                  'panels don\'t have icons.')
                else:
                    mlogger.debug('Creating icon for push button %s '
                                  'from file: %s', button_name, icon_path)
                    try:
                        new_button.set_icon(icon_path, icon_size=ICON_LARGE)
                    except PyRevitUIError as iconerr:
                        mlogger.error('Error adding icon for %s from %s '
                                      '| %s', button_name, icon_path, iconerr)

                new_button.set_tooltip(tooltip)
                new_button.set_tooltip_ext(tooltip_ext)
                if tooltip_media:
                    new_button.set_tooltip_media(tooltip_media)

                new_button.set_contexthelp(ctxhelpurl)

                new_button.set_dirty_flag()
                self._add_component(new_button)

            except Exception as create_err:
                raise PyRevitUIError('Can not create button | {}'
                                     .format(create_err))

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
            mlogger.debug('Panel does not include this pull down button. '
                          'Creating: %s', item_name)
            try:
                # creating pull down button data and add to child list
                pdbutton_data = pulldowndata_type(item_name, item_name)
                if not self.itemdata_mode:
                    mlogger.debug('Creating pull down button: %s in %s',
                                  item_name, self)
                    new_push_button = \
                        self.get_rvtapi_object().AddItem(pdbutton_data)
                    pyrvt_pdbutton = _PyRevitRibbonGroupItem(new_push_button)
                    try:
                        pyrvt_pdbutton.set_icon(icon_path)
                    except PyRevitUIError as iconerr:
                        mlogger.debug('Error adding icon for %s from %s '
                                      '| %s', item_name, icon_path, iconerr)
                else:
                    mlogger.debug('Creating pull down button under stack: '
                                  '%s in %s', item_name, self)
                    pyrvt_pdbutton = _PyRevitRibbonGroupItem(pdbutton_data)
                    try:
                        pyrvt_pdbutton.set_icon(icon_path)
                    except PyRevitUIError as iconerr:
                        mlogger.debug('Error adding icon for %s from %s '
                                      '| %s', item_name, icon_path, iconerr)

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

    def create_panel_push_button(self, button_name, asm_location, class_name,
                                 tooltip='', tooltip_ext='', tooltip_media='',
                                 ctxhelpurl=None,
                                 avail_class_name=None,
                                 update_if_exists=False,
                                 ui_title=None):
        self.create_push_button(button_name=button_name,
                                asm_location=asm_location,
                                class_name=class_name,
                                icon_path=None,
                                tooltip=tooltip,
                                tooltip_ext=tooltip_ext,
                                tooltip_media=tooltip_media,
                                ctxhelpurl=ctxhelpurl,
                                avail_class_name=avail_class_name,
                                update_if_exists=update_if_exists,
                                ui_title=ui_title)
        self.set_dlglauncher(self.button(button_name))



class _PyRevitRibbonTab(GenericPyRevitUIContainer):
    ribbon_panel = GenericPyRevitUIContainer._get_component

    def __init__(self, revit_ribbon_tab, is_pyrvt_tab=False):
        GenericPyRevitUIContainer.__init__(self)

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
                new_pyrvt_panel = _PyRevitRibbonPanel(revit_ui_panel,
                                                      self._rvtapi_object)
                self._add_component(new_pyrvt_panel)
        except:
            # if .GetRibbonPanels fails, this tab is an existing native tab
            raise PyRevitUIError('Can not get panels for this tab: {}'
                                 .format(self._rvtapi_object))

    def get_adwindows_object(self):
        return self.get_rvtapi_object()

    def reset_highlights(self):
        # no highlighting options for tabs
        pass

    def highlight_as_new(self):
        # no highlighting options for tabs
        pass

    def highlight_as_updated(self):
        # no highlighting options for tabs
        pass

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
                pyrvt_ribbon_panel = _PyRevitRibbonPanel(ribbon_panel,
                                                         self._rvtapi_object)
                pyrvt_ribbon_panel.set_dirty_flag()
                self._add_component(pyrvt_ribbon_panel)

            except Exception as panel_err:
                raise PyRevitUIError('Can not create panel: {}'
                                     .format(panel_err))


class _PyRevitUI(GenericPyRevitUIContainer):
    """Captures the existing ui state and elements at creation."""

    ribbon_tab = GenericPyRevitUIContainer._get_component

    def __init__(self, all_native=False):
        GenericPyRevitUIContainer.__init__(self)

        # Revit does not have any method to get a list of current tabs.
        # Getting a list of current tabs using adwindows.dll methods
        # Iterating over tabs,
        # because ComponentManager.Ribbon.Tabs.FindTab(tab.name)
        # does not return invisible tabs
        for revit_ui_tab in AdWindows.ComponentManager.Ribbon.Tabs:
            # feeding self._sub_pyrvt_ribbon_tabs with an instance of
            # _PyRevitRibbonTab or RevitNativeRibbonTab for each existing
            # tab. _PyRevitRibbonTab or RevitNativeRibbonTab will find
            # their existing panels only listing visible tabs
            # (there might be tabs with identical names
            # e.g. there are two Annotate tabs. They are activated as
            # neccessary per context but need to add inactive/invisible
            # pyrevit tabs (PYREVIT_TAB_IDENTIFIER) anyway.
            # if revit_ui_tab.IsVisible
            try:
                if not all_native \
                        and _PyRevitRibbonTab.check_pyrevit_tab(revit_ui_tab):
                    new_pyrvt_tab = _PyRevitRibbonTab(revit_ui_tab)
                else:
                    new_pyrvt_tab = RevitNativeRibbonTab(revit_ui_tab)
                self._add_component(new_pyrvt_tab)
                mlogger.debug('Tab added to the list of tabs: %s',
                              new_pyrvt_tab.name)
            except PyRevitUIError:
                # if _PyRevitRibbonTab(revit_ui_tab) fails,
                # Revit restricts access to its panels RevitNativeRibbonTab
                # uses a different method to access the panels
                # to interact with existing native ui
                new_pyrvt_tab = RevitNativeRibbonTab(revit_ui_tab)
                self._add_component(new_pyrvt_tab)
                mlogger.debug('Native tab added to the list of tabs: %s',
                              new_pyrvt_tab.name)

    def get_adwindows_ribbon_control(self):
        return AdWindows.ComponentManager.Ribbon

    @staticmethod
    def toggle_ribbon_updator(
            state,
            flow_direction=Windows.FlowDirection.LeftToRight):
        # cancel out the ribbon updator from previous runtime version
        current_ribbon_updator = \
            envvars.get_pyrevit_env_var(envvars.RIBBONUPDATOR_ENVVAR)
        if current_ribbon_updator:
            current_ribbon_updator.StopUpdatingRibbon()

        # reset env var
        envvars.set_pyrevit_env_var(envvars.RIBBONUPDATOR_ENVVAR, None)
        if state:
            # start or stop the ribbon updator
            panel_set = None
            try:
                main_wnd = ui.get_mainwindow()
                ribbon_root_type = ui.get_ribbon_roottype()
                panel_set = \
                    main_wnd.FindFirstChild[ribbon_root_type](main_wnd)
            except Exception as raex:
                mlogger.error('Error activating ribbon updator. | %s', raex)
                return

            if panel_set:
                types.RibbonEventUtils.StartUpdatingRibbon(
                    panelSet=panel_set,
                    flowDir=flow_direction,
                    tagTag=PYREVIT_TAB_IDENTIFIER
                )
                # set the new colorizer
                envvars.set_pyrevit_env_var(
                    envvars.RIBBONUPDATOR_ENVVAR,
                    types.RibbonEventUtils
                    )

    def set_RTL_flow(self):
        _PyRevitUI.toggle_ribbon_updator(
            state=True,
            flow_direction=Windows.FlowDirection.RightToLeft
            )

    def set_LTR_flow(self):
        # default is LTR, make sure any existing is stopped
        _PyRevitUI.toggle_ribbon_updator(state=False)

    def unset_RTL_flow(self):
        _PyRevitUI.toggle_ribbon_updator(state=False)

    def unset_LTR_flow(self):
        # default is LTR, make sure any existing is stopped
        _PyRevitUI.toggle_ribbon_updator(state=False)

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
                for exiting_rvt_ribbon_tab in \
                        AdWindows.ComponentManager.Ribbon.Tabs:
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
def get_current_ui(all_native=False):
    """Revit UI Wrapper class for interacting with current pyRevit UI.

    Returned class provides min required functionality for user interaction

    Examples:
        ```python
        current_ui = pyrevit.session.current_ui()
        this_script = pyrevit.session.get_this_command()
        current_ui.update_button_icon(this_script, new_icon)
        ```

    Returns:
        (_PyRevitUI): wrapper around active ribbon gui
    """
    return _PyRevitUI(all_native=all_native)


def get_uibutton(command_unique_name):
    """Find and return ribbon ui button with given unique id.

    Args:
        command_unique_name (str): unique id of pyRevit command

    Returns:
        (_PyRevitRibbonButton): ui button wrapper object
    """
    # FIXME: verify return type
    pyrvt_tabs = get_current_ui().get_pyrevit_tabs()
    for tab in pyrvt_tabs:
        button = tab.find_child(command_unique_name)
        if button:
            return button
    return None
