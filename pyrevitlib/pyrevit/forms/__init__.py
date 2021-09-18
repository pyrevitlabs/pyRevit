"""Reusable WPF forms for pyRevit.

Example:
    >>> from pyrevit.forms import WPFWindow
"""

import sys
import os
import os.path as op
import string
from collections import OrderedDict, namedtuple
import threading
from functools import wraps
import datetime
import webbrowser

from pyrevit import HOST_APP, EXEC_PARAMS, DOCS, BIN_DIR
from pyrevit import PyRevitCPythonNotSupported, PyRevitException, PyRevitCPythonNotSupported
import pyrevit.compat as compat
from pyrevit.compat import safe_strtype

if compat.PY3:
    raise PyRevitCPythonNotSupported('pyrevit.forms')

from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import colors
from pyrevit import framework
from pyrevit.framework import System
from pyrevit.framework import Threading
from pyrevit.framework import Interop
from pyrevit.framework import Input
from pyrevit.framework import wpf, Forms, Controls, Media
from pyrevit.framework import CPDialogs
from pyrevit.framework import ComponentModel
from pyrevit.framework import ObservableCollection
from pyrevit.api import AdWindows
from pyrevit import revit, UI, DB
from pyrevit.forms import utils
from pyrevit.forms import toaster
from pyrevit import versionmgr

import pyevent #pylint: disable=import-error


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


DEFAULT_CMDSWITCHWND_WIDTH = 600
DEFAULT_SEARCHWND_WIDTH = 600
DEFAULT_SEARCHWND_HEIGHT = 100
DEFAULT_INPUTWINDOW_WIDTH = 500
DEFAULT_INPUTWINDOW_HEIGHT = 600
DEFAULT_RECOGNIZE_ACCESS_KEY = False

WPF_HIDDEN = framework.Windows.Visibility.Hidden
WPF_COLLAPSED = framework.Windows.Visibility.Collapsed
WPF_VISIBLE = framework.Windows.Visibility.Visible


XAML_FILES_DIR = op.dirname(__file__)


ParamDef = namedtuple('ParamDef', ['name', 'istype', 'definition', 'isreadonly'])
"""Parameter definition tuple.

Attributes:
    name (str): parameter name
    istype (bool): true if type parameter, otherwise false
    definition (Autodesk.Revit.DB.Definition): parameter definition object
    isreadonly (bool): true if the parameter value can't be edited
"""


# https://gui-at.blogspot.com/2009/11/inotifypropertychanged-in-ironpython.html
class reactive(property):
    """Decorator for WPF bound properties"""
    def __init__(self, getter):
        def newgetter(ui_control):
            try:
                return getter(ui_control)
            except AttributeError:
                return None
        super(reactive, self).__init__(newgetter)

    def setter(self, setter):
        def newsetter(ui_control, newvalue):
            oldvalue = self.fget(ui_control)
            if oldvalue != newvalue:
                setter(ui_control, newvalue)
                ui_control.OnPropertyChanged(setter.__name__)
        return property(
            fget=self.fget,
            fset=newsetter,
            fdel=self.fdel,
            doc=self.__doc__)


class Reactive(ComponentModel.INotifyPropertyChanged):
    """WPF property updator base mixin"""
    PropertyChanged, _propertyChangedCaller = pyevent.make_event()

    def add_PropertyChanged(self, value):
        self.PropertyChanged += value

    def remove_PropertyChanged(self, value):
        self.PropertyChanged -= value

    def OnPropertyChanged(self, prop_name):
        if self._propertyChangedCaller:
            args = ComponentModel.PropertyChangedEventArgs(prop_name)
            self._propertyChangedCaller(self, args)


class WindowToggler(object):
    def __init__(self, window):
        self._window = window

    def __enter__(self):
        self._window.hide()

    def __exit__(self, exception, exception_value, traceback):
        self._window.show_dialog()


class WPFWindow(framework.Windows.Window):
    r"""WPF Window base class for all pyRevit forms.

    Args:
        xaml_source (str): xaml source filepath or xaml content
        literal_string (bool): xaml_source contains xaml content, not filepath
        handle_esc (bool): handle Escape button and close the window
        set_owner (bool): set the owner of window to host app window

    Example:
        >>> from pyrevit import forms
        >>> layout = '<Window ' \
        >>>          'xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" ' \
        >>>          'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" ' \
        >>>          'ShowInTaskbar="False" ResizeMode="NoResize" ' \
        >>>          'WindowStartupLocation="CenterScreen" ' \
        >>>          'HorizontalContentAlignment="Center">' \
        >>>          '</Window>'
        >>> w = forms.WPFWindow(layout, literal_string=True)
        >>> w.show()
    """

    def __init__(self, xaml_source, literal_string=False, handle_esc=True, set_owner=True):
        """Initialize WPF window and resources."""
        # load xaml
        self.load_xaml(
            xaml_source,
            literal_string=literal_string,
            handle_esc=handle_esc,
            set_owner=set_owner
            )

    def load_xaml(self, xaml_source, literal_string=False, handle_esc=True, set_owner=True):
        # create new id for this window
        self.window_id = coreutils.new_uuid()

        if not literal_string:
            if not op.exists(xaml_source):
                wpf.LoadComponent(self,
                                  os.path.join(EXEC_PARAMS.command_path,
                                               xaml_source))
            else:
                wpf.LoadComponent(self, xaml_source)
        else:
            wpf.LoadComponent(self, framework.StringReader(xaml_source))

        # set properties
        self.thread_id = framework.get_current_thread_id()
        if set_owner:
            self.setup_owner()
        self.setup_icon()
        WPFWindow.setup_resources(self)
        if handle_esc:
            self.setup_default_handlers()

    def setup_owner(self):
        wih = Interop.WindowInteropHelper(self)
        wih.Owner = AdWindows.ComponentManager.ApplicationWindow

    @staticmethod
    def setup_resources(wpf_ctrl):
        #2c3e50
        wpf_ctrl.Resources['pyRevitDarkColor'] = \
            Media.Color.FromArgb(0xFF, 0x2c, 0x3e, 0x50)

        #23303d
        wpf_ctrl.Resources['pyRevitDarkerDarkColor'] = \
            Media.Color.FromArgb(0xFF, 0x23, 0x30, 0x3d)

        #ffffff
        wpf_ctrl.Resources['pyRevitButtonColor'] = \
            Media.Color.FromArgb(0xFF, 0xff, 0xff, 0xff)

        #f39c12
        wpf_ctrl.Resources['pyRevitAccentColor'] = \
            Media.Color.FromArgb(0xFF, 0xf3, 0x9c, 0x12)

        wpf_ctrl.Resources['pyRevitDarkBrush'] = \
            Media.SolidColorBrush(wpf_ctrl.Resources['pyRevitDarkColor'])
        wpf_ctrl.Resources['pyRevitAccentBrush'] = \
            Media.SolidColorBrush(wpf_ctrl.Resources['pyRevitAccentColor'])

        wpf_ctrl.Resources['pyRevitDarkerDarkBrush'] = \
            Media.SolidColorBrush(wpf_ctrl.Resources['pyRevitDarkerDarkColor'])

        wpf_ctrl.Resources['pyRevitButtonForgroundBrush'] = \
            Media.SolidColorBrush(wpf_ctrl.Resources['pyRevitButtonColor'])

        wpf_ctrl.Resources['pyRevitRecognizesAccessKey'] = \
            DEFAULT_RECOGNIZE_ACCESS_KEY

    def setup_default_handlers(self):
        self.PreviewKeyDown += self.handle_input_key    #pylint: disable=E1101

    def handle_input_key(self, sender, args):    #pylint: disable=W0613
        """Handle keyboard input and close the window on Escape."""
        if args.Key == Input.Key.Escape:
            self.Close()

    def set_icon(self, icon_path):
        """Set window icon to given icon path."""
        self.Icon = utils.bitmap_from_file(icon_path)

    def setup_icon(self):
        """Setup default window icon."""
        self.set_icon(op.join(BIN_DIR, 'pyrevit_settings.png'))

    def hide(self):
        self.Hide()

    def show(self, modal=False):
        """Show window."""
        if modal:
            return self.ShowDialog()
        # else open non-modal
        self.Show()

    def show_dialog(self):
        """Show modal window."""
        return self.ShowDialog()

    @staticmethod
    def set_image_source_file(wpf_element, image_file):
        """Set source file for image element.

        Args:
            element_name (System.Windows.Controls.Image): xaml image element
            image_file (str): image file path
        """
        if not op.exists(image_file):
            wpf_element.Source = \
                utils.bitmap_from_file(
                    os.path.join(EXEC_PARAMS.command_path,
                                 image_file)
                    )
        else:
            wpf_element.Source = utils.bitmap_from_file(image_file)

    def set_image_source(self, wpf_element, image_file):
        """Set source file for image element.

        Args:
            element_name (System.Windows.Controls.Image): xaml image element
            image_file (str): image file path
        """
        WPFWindow.set_image_source_file(wpf_element, image_file)

    def dispatch(self, func, *args, **kwargs):
        if framework.get_current_thread_id() == self.thread_id:
            t = threading.Thread(
                target=func,
                args=args,
                kwargs=kwargs
                )
            t.start()
        else:
            # ask ui thread to call the func with args and kwargs
            self.Dispatcher.Invoke(
                System.Action(
                    lambda: func(*args, **kwargs)
                    ),
                Threading.DispatcherPriority.Background
                )

    def conceal(self):
        return WindowToggler(self)

    @property
    def pyrevit_version(self):
        """Active pyRevit formatted version e.g. '4.9-beta'"""
        return 'pyRevit {}'.format(
            versionmgr.get_pyrevit_version().get_formatted()
            )

    @staticmethod
    def hide_element(*wpf_elements):
        """Collapse elements.

        Args:
            *wpf_elements: WPF framework elements to be collaped
        """
        for wpfel in wpf_elements:
            wpfel.Visibility = WPF_COLLAPSED

    @staticmethod
    def show_element(*wpf_elements):
        """Show collapsed elements.

        Args:
            *wpf_elements: WPF framework elements to be set to visible.
        """
        for wpfel in wpf_elements:
            wpfel.Visibility = WPF_VISIBLE

    @staticmethod
    def toggle_element(*wpf_elements):
        """Toggle visibility of elements.

        Args:
            *wpf_elements: WPF framework elements to be toggled.
        """
        for wpfel in wpf_elements:
            if wpfel.Visibility == WPF_VISIBLE:
                WPFWindow.hide_element(wpfel)
            elif wpfel.Visibility == WPF_COLLAPSED:
                WPFWindow.show_element(wpfel)

    @staticmethod
    def disable_element(*wpf_elements):
        """Enable elements.

        Args:
            *wpf_elements: WPF framework elements to be enabled
        """
        for wpfel in wpf_elements:
            wpfel.IsEnabled = False

    @staticmethod
    def enable_element(*wpf_elements):
        """Enable elements.

        Args:
            *wpf_elements: WPF framework elements to be enabled
        """
        for wpfel in wpf_elements:
            wpfel.IsEnabled = True

    def handle_url_click(self, sender, args): #pylint: disable=unused-argument
        """Callback for handling click on package website url"""
        return webbrowser.open_new_tab(sender.NavigateUri.AbsoluteUri)


class WPFPanel(framework.Windows.Controls.Page):
    r"""WPF panel base class for all pyRevit dockable panels.

    panel_id (str) must be set on the type to dockable panel uuid
    panel_source (str): xaml source filepath

    Example:
        >>> from pyrevit import forms
        >>> class MyPanel(forms.WPFPanel):
        ...     panel_id = "181e05a4-28f6-4311-8a9f-d2aa528c8755"
        ...     panel_source = "MyPanel.xaml"

        >>> forms.register_dockable_panel(MyPanel)
        >>> # then from the button that needs to open the panel
        >>> forms.open_dockable_panel("181e05a4-28f6-4311-8a9f-d2aa528c8755")
    """

    panel_id = None
    panel_source = None

    def __init__(self):
        """Initialize WPF panel and resources."""
        if not self.panel_id:
            raise PyRevitException("\"panel_id\" property is not set")
        if not self.panel_source:
            raise PyRevitException("\"panel_source\" property is not set")

        if not op.exists(self.panel_source):
            wpf.LoadComponent(self,
                              os.path.join(EXEC_PARAMS.command_path,
                              self.panel_source))
        else:
            wpf.LoadComponent(self, self.panel_source)

        # set properties
        self.thread_id = framework.get_current_thread_id()
        WPFWindow.setup_resources(self)

    def set_image_source(self, wpf_element, image_file):
        """Set source file for image element.

        Args:
            element_name (System.Windows.Controls.Image): xaml image element
            image_file (str): image file path
        """
        WPFWindow.set_image_source_file(wpf_element, image_file)

    @staticmethod
    def hide_element(*wpf_elements):
        """Collapse elements.

        Args:
            *wpf_elements: WPF framework elements to be collaped
        """
        WPFPanel.hide_element(*wpf_elements)

    @staticmethod
    def show_element(*wpf_elements):
        """Show collapsed elements.

        Args:
            *wpf_elements: WPF framework elements to be set to visible.
        """
        WPFPanel.show_element(*wpf_elements)

    @staticmethod
    def toggle_element(*wpf_elements):
        """Toggle visibility of elements.

        Args:
            *wpf_elements: WPF framework elements to be toggled.
        """
        WPFPanel.toggle_element(*wpf_elements)

    @staticmethod
    def disable_element(*wpf_elements):
        """Enable elements.

        Args:
            *wpf_elements: WPF framework elements to be enabled
        """
        WPFPanel.disable_element(*wpf_elements)

    @staticmethod
    def enable_element(*wpf_elements):
        """Enable elements.

        Args:
            *wpf_elements: WPF framework elements to be enabled
        """
        WPFPanel.enable_element(*wpf_elements)

    def handle_url_click(self, sender, args): #pylint: disable=unused-argument
        """Callback for handling click on package website url"""
        return webbrowser.open_new_tab(sender.NavigateUri.AbsoluteUri)


class _WPFPanelProvider(UI.IDockablePaneProvider):
    """Internal Panel provider for panels"""

    def __init__(self, panel_type, default_visible=True):
        self._panel_type = panel_type
        self._default_visible = default_visible
        self.panel = self._panel_type()

    def SetupDockablePane(self, data):
        """Setup forms.WPFPanel set on this instance"""
        # TODO: need to implement panel data
        # https://apidocs.co/apps/revit/2021.1/98157ec2-ab26-6ab7-2933-d1b4160ba2b8.htm
        data.FrameworkElement = self.panel
        data.VisibleByDefault = self._default_visible


def register_dockable_panel(panel_type, default_visible=True):
    """Register dockable panel

    Args:
        panel_type (forms.WPFPanel): dockable panel type
        default_visible (bool, optional):
            whether panel should be visible by default
    """
    if not issubclass(panel_type, WPFPanel):
        raise PyRevitException(
            "Dockable pane must be a subclass of forms.WPFPanel"
            )

    panel_uuid = coreutils.Guid.Parse(panel_type.panel_id)
    dockable_panel_id = UI.DockablePaneId(panel_uuid)
    panel_provider = _WPFPanelProvider(panel_type, default_visible)
    HOST_APP.uiapp.RegisterDockablePane(
        dockable_panel_id,
        panel_type.panel_title,
        panel_provider
    )

    return panel_provider.panel


def open_dockable_panel(panel_type_or_id):
    """Open previously registered dockable panel

    Args:
        panel_type_or_id (forms.WPFPanel, str): panel type or id
    """
    toggle_dockable_panel(panel_type_or_id, True)


def close_dockable_panel(panel_type_or_id):
    """Close previously registered dockable panel

    Args:
        panel_type_or_id (forms.WPFPanel, str): panel type or id
    """
    toggle_dockable_panel(panel_type_or_id, False)


def toggle_dockable_panel(panel_type_or_id, state):
    """Toggle previously registered dockable panel

    Args:
        panel_type_or_id (forms.WPFPanel, str): panel type or id
    """
    dpanel_id = None
    if isinstance(panel_type_or_id, str):
        panel_id = coreutils.Guid.Parse(panel_type_or_id)
        dpanel_id = UI.DockablePaneId(panel_id)
    elif issubclass(panel_type_or_id, WPFPanel):
        panel_id = coreutils.Guid.Parse(panel_type_or_id.panel_id)
        dpanel_id = UI.DockablePaneId(panel_id)
    else:
        raise PyRevitException("Given type is not a forms.WPFPanel")

    if dpanel_id:
        if UI.DockablePane.PaneIsRegistered(dpanel_id):
            dockable_panel = HOST_APP.uiapp.GetDockablePane(dpanel_id)
            if state:
                dockable_panel.Show()
            else:
                dockable_panel.Hide()
        else:
            raise PyRevitException(
                "Panel with id \"%s\" is not registered" % panel_type_or_id
                )


class TemplateUserInputWindow(WPFWindow):
    """Base class for pyRevit user input standard forms.

    Args:
        context (any): window context element(s)
        title (str): window title
        width (int): window width
        height (int): window height
        **kwargs: other arguments to be passed to :func:`_setup`
    """

    xaml_source = 'BaseWindow.xaml'

    def __init__(self, context, title, width, height, **kwargs):
        """Initialize user input window."""
        WPFWindow.__init__(self,
                           op.join(XAML_FILES_DIR, self.xaml_source),
                           handle_esc=True)
        self.Title = title or 'pyRevit'
        self.Width = width
        self.Height = height

        self._context = context
        self.response = None

        # parent window?
        owner = kwargs.get('owner', None)
        if owner:
            # set wpf windows directly
            self.Owner = owner
            self.WindowStartupLocation = \
                framework.Windows.WindowStartupLocation.CenterOwner

        self._setup(**kwargs)

    def _setup(self, **kwargs):
        """Private method to be overriden by subclasses for window setup."""
        pass

    @classmethod
    def show(cls, context,  #pylint: disable=W0221
             title='User Input',
             width=DEFAULT_INPUTWINDOW_WIDTH,
             height=DEFAULT_INPUTWINDOW_HEIGHT, **kwargs):
        """Show user input window.

        Args:
            context (any): window context element(s)
            title (str): window title
            width (int): window width
            height (int): window height
            **kwargs (any): other arguments to be passed to window
        """
        dlg = cls(context, title, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response


class TemplateListItem(Reactive):
    """Base class for checkbox option wrapping another object."""

    def __init__(self, orig_item,
                 checked=False, checkable=True, name_attr=None):
        """Initialize the checkbox option and wrap given obj.

        Args:
            orig_item (any): Object to wrap (must have name property
                             or be convertable to string with str()
            checkable (bool): Use checkbox for items
            name_attr (str): Get this attribute of wrapped object as name
        """
        super(TemplateListItem, self).__init__()
        self.item = orig_item
        self.state = checked
        self._nameattr = name_attr
        self._checkable = checkable

    def __nonzero__(self):
        return self.state

    def __str__(self):
        return self.name or str(self.item)

    def __contains__(self, value):
        return value in self.name

    def __getattr__(self, param_name):
        return getattr(self.item, param_name)

    @property
    def name(self):
        """Name property."""
        # get custom attr, or name or just str repr
        if self._nameattr:
            return safe_strtype(getattr(self.item, self._nameattr))
        elif hasattr(self.item, 'name'):
            return getattr(self.item, 'name', '')
        else:
            return safe_strtype(self.item)

    def unwrap(self):
        """Unwrap and return wrapped object."""
        return self.item

    @reactive
    def checked(self):
        """Id checked"""
        return self.state

    @checked.setter
    def checked(self, value):
        self.state = value

    @property
    def checkable(self):
        """List Item CheckBox Visibility."""
        return WPF_VISIBLE if self._checkable \
            else WPF_COLLAPSED

    @checkable.setter
    def checkable(self, value):
        self._checkable = value


class SelectFromList(TemplateUserInputWindow):
    """Standard form to select from a list of items.

    Any object can be passed in a list to the ``context`` argument. This class
    wraps the objects passed to context, in :obj:`TemplateListItem`.
    This class provides the necessary mechanism to make this form work both
    for selecting items from a list, and from a list of checkboxes. See the
    list of arguments below for additional options and features.

    Args:
        context (list[str] or dict[list[str]]):
            list of items to be selected from
            OR
            dict of list of items to be selected from.
            use dict when input items need to be grouped
            e.g. List of sheets grouped by sheet set.
        title (str, optional): window title. see super class for defaults.
        width (int, optional): window width. see super class for defaults.
        height (int, optional): window height. see super class for defaults.
        button_name (str, optional):
            name of select button. defaults to 'Select'
        name_attr (str, optional):
            object attribute that should be read as item name.
        multiselect (bool, optional):
            allow multi-selection (uses check boxes). defaults to False
        info_panel (bool, optional):
            show information panel and fill with .description property of item
        return_all (bool, optional):
            return all items. This is handly when some input items have states
            and the script needs to check the state changes on all items.
            This options works in multiselect mode only. defaults to False
        filterfunc (function):
            filter function to be applied to context items.
        resetfunc (function):
            reset function to be called when user clicks on Reset button
        group_selector_title (str):
            title for list group selector. defaults to 'List Group'
        default_group (str): name of defautl group to be selected


    Example:
        >>> from pyrevit import forms
        >>> items = ['item1', 'item2', 'item3']
        >>> forms.SelectFromList.show(items, button_name='Select Item')
        >>> ['item1']

        >>> from pyrevit import forms
        >>> ops = [viewsheet1, viewsheet2, viewsheet3]
        >>> res = forms.SelectFromList.show(ops,
        ...                                 multiselect=False,
        ...                                 name_attr='Name',
        ...                                 button_name='Select Sheet')

        >>> from pyrevit import forms
        >>> ops = {'Sheet Set A': [viewsheet1, viewsheet2, viewsheet3],
        ...        'Sheet Set B': [viewsheet4, viewsheet5, viewsheet6]}
        >>> res = forms.SelectFromList.show(ops,
        ...                                 multiselect=True,
        ...                                 name_attr='Name',
        ...                                 group_selector_title='Sheet Sets',
        ...                                 button_name='Select Sheets')

        This module also provides a wrapper base class :obj:`TemplateListItem`
        for when the checkbox option is wrapping another element,
        e.g. a Revit ViewSheet. Derive from this base class and define the
        name property to customize how the checkbox is named on the dialog.

        >>> from pyrevit import forms
        >>> class MyOption(forms.TemplateListItem):
        ...    @property
        ...    def name(self):
        ...        return '{} - {}{}'.format(self.item.SheetNumber,
        ...                                  self.item.SheetNumber)
        >>> ops = [MyOption('op1'), MyOption('op2', True), MyOption('op3')]
        >>> res = forms.SelectFromList.show(ops,
        ...                                 multiselect=True,
        ...                                 button_name='Select Item')
        >>> [bool(x) for x in res]  # or [x.state for x in res]
        [True, False, True]

    """

    xaml_source = 'SelectFromList.xaml'

    @property
    def use_regex(self):
        """Is using regex?"""
        return self.regexToggle_b.IsChecked

    def _setup(self, **kwargs):
        # custom button name?
        button_name = kwargs.get('button_name', 'Select')
        if button_name:
            self.select_b.Content = button_name

        # attribute to use as name?
        self._nameattr = kwargs.get('name_attr', None)

        # multiselect?
        if kwargs.get('multiselect', False):
            self.multiselect = True
            self.list_lb.SelectionMode = Controls.SelectionMode.Extended
            self.show_element(self.checkboxbuttons_g)
        else:
            self.multiselect = False
            self.list_lb.SelectionMode = Controls.SelectionMode.Single
            self.hide_element(self.checkboxbuttons_g)

        # info panel?
        self.info_panel = kwargs.get('info_panel', False)

        # return checked items only?
        self.return_all = kwargs.get('return_all', False)

        # filter function?
        self.filter_func = kwargs.get('filterfunc', None)

        # reset function?
        self.reset_func = kwargs.get('resetfunc', None)
        if self.reset_func:
            self.show_element(self.reset_b)

        # context group title?
        self.ctx_groups_title = \
            kwargs.get('group_selector_title', 'List Group')
        self.ctx_groups_title_tb.Text = self.ctx_groups_title

        self.ctx_groups_active = kwargs.get('default_group', None)

        # check for custom templates
        items_panel_template = kwargs.get('items_panel_template', None)
        if items_panel_template:
            self.Resources["ItemsPanelTemplate"] = items_panel_template

        item_container_template = kwargs.get('item_container_template', None)
        if item_container_template:
            self.Resources["ItemContainerTemplate"] = item_container_template

        item_template = kwargs.get('item_template', None)
        if item_template:
            self.Resources["ItemTemplate"] = \
                item_template

        # nicely wrap and prepare context for presentation, then present
        self._prepare_context()

        # setup search and filter fields
        self.hide_element(self.clrsearch_b)

        # active event listeners
        self.search_tb.TextChanged += self.search_txt_changed
        self.ctx_groups_selector_cb.SelectionChanged += self.selection_changed

        self.clear_search(None, None)

    def _prepare_context_items(self, ctx_items):
        new_ctx = []
        # filter context if necessary
        if self.filter_func:
            ctx_items = filter(self.filter_func, ctx_items)

        for item in ctx_items:
            if isinstance(item, TemplateListItem):
                item.checkable = self.multiselect
                new_ctx.append(item)
            else:
                new_ctx.append(
                    TemplateListItem(item,
                                     checkable=self.multiselect,
                                     name_attr=self._nameattr)
                    )

        return new_ctx

    def _prepare_context(self):
        if isinstance(self._context, dict) and self._context.keys():
            self._update_ctx_groups(sorted(self._context.keys()))
            new_ctx = {}
            for ctx_grp, ctx_items in self._context.items():
                new_ctx[ctx_grp] = self._prepare_context_items(ctx_items)
            self._context = new_ctx
        else:
            self._context = self._prepare_context_items(self._context)

    def _update_ctx_groups(self, ctx_group_names):
        self.show_element(self.ctx_groups_dock)
        self.ctx_groups_selector_cb.ItemsSource = ctx_group_names
        if self.ctx_groups_active in ctx_group_names:
            self.ctx_groups_selector_cb.SelectedIndex = \
                ctx_group_names.index(self.ctx_groups_active)
        else:
            self.ctx_groups_selector_cb.SelectedIndex = 0

    def _get_active_ctx_group(self):
        return self.ctx_groups_selector_cb.SelectedItem

    def _get_active_ctx(self):
        if isinstance(self._context, dict):
            return self._context[self._get_active_ctx_group()]
        else:
            return self._context

    def _list_options(self, option_filter=None):
        if option_filter:
            self.checkall_b.Content = 'Check'
            self.uncheckall_b.Content = 'Uncheck'
            self.toggleall_b.Content = 'Toggle'
            # get a match score for every item and sort high to low
            fuzzy_matches = sorted(
                [(x,
                  coreutils.fuzzy_search_ratio(
                      target_string=x.name,
                      sfilter=option_filter,
                      regex=self.use_regex))
                 for x in self._get_active_ctx()],
                key=lambda x: x[1],
                reverse=True
                )
            # filter out any match with score less than 80
            self.list_lb.ItemsSource = \
                ObservableCollection[TemplateListItem](
                    [x[0] for x in fuzzy_matches if x[1] >= 80]
                    )
        else:
            self.checkall_b.Content = 'Check All'
            self.uncheckall_b.Content = 'Uncheck All'
            self.toggleall_b.Content = 'Toggle All'
            self.list_lb.ItemsSource = \
                ObservableCollection[TemplateListItem](self._get_active_ctx())

    @staticmethod
    def _unwrap_options(options):
        unwrapped = []
        for optn in options:
            if isinstance(optn, TemplateListItem):
                unwrapped.append(optn.unwrap())
            else:
                unwrapped.append(optn)
        return unwrapped

    def _get_options(self):
        if self.multiselect:
            if self.return_all:
                return [x for x in self._get_active_ctx()]
            else:
                return self._unwrap_options(
                    [x for x in self._get_active_ctx()
                     if x.state or x in self.list_lb.SelectedItems]
                    )
        else:
            return self._unwrap_options([self.list_lb.SelectedItem])[0]

    def _set_states(self, state=True, flip=False, selected=False):
        if selected:
            current_list = self.list_lb.SelectedItems
        else:
            current_list = self.list_lb.ItemsSource
        for checkbox in current_list:
            # using .checked to push ui update
            if flip:
                checkbox.checked = not checkbox.checked
            else:
                checkbox.checked = state

    def _toggle_info_panel(self, state=True):
        if state:
            # enable the info panel
            self.splitterCol.Width = System.Windows.GridLength(8)
            self.infoCol.Width = System.Windows.GridLength(self.Width/2)
            self.show_element(self.infoSplitter)
            self.show_element(self.infoPanel)
        else:
            self.splitterCol.Width = self.infoCol.Width = \
                System.Windows.GridLength.Auto
            self.hide_element(self.infoSplitter)
            self.hide_element(self.infoPanel)

    def toggle_all(self, sender, args):    #pylint: disable=W0613
        """Handle toggle all button to toggle state of all check boxes."""
        self._set_states(flip=True)

    def check_all(self, sender, args):    #pylint: disable=W0613
        """Handle check all button to mark all check boxes as checked."""
        self._set_states(state=True)

    def uncheck_all(self, sender, args):    #pylint: disable=W0613
        """Handle uncheck all button to mark all check boxes as un-checked."""
        self._set_states(state=False)

    def check_selected(self, sender, args):    #pylint: disable=W0613
        """Mark selected checkboxes as checked."""
        self._set_states(state=True, selected=True)

    def uncheck_selected(self, sender, args):    #pylint: disable=W0613
        """Mark selected checkboxes as unchecked."""
        self._set_states(state=False, selected=True)

    def button_reset(self, sender, args):#pylint: disable=W0613
        if self.reset_func:
            all_items = self.list_lb.ItemsSource
            self.reset_func(all_items)

    def button_select(self, sender, args):    #pylint: disable=W0613
        """Handle select button click."""
        self.response = self._get_options()
        self.Close()

    def search_txt_changed(self, sender, args):    #pylint: disable=W0613
        """Handle text change in search box."""
        if self.info_panel:
            self._toggle_info_panel(state=False)

        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(option_filter=self.search_tb.Text)

    def selection_changed(self, sender, args):
        if self.info_panel:
            self._toggle_info_panel(state=False)

        self._list_options(option_filter=self.search_tb.Text)

    def selected_item_changed(self, sender, args):
        if self.info_panel and self.list_lb.SelectedItem is not None:
            self._toggle_info_panel(state=True)
            self.infoData.Text = \
                getattr(self.list_lb.SelectedItem, 'description', '')

    def toggle_regex(self, sender, args):
        """Activate regex in search"""
        self.regexToggle_b.Content = \
            self.Resources['regexIcon'] if self.use_regex \
                else self.Resources['filterIcon']
        self.search_txt_changed(sender, args)
        self.search_tb.Focus()

    def clear_search(self, sender, args):    #pylint: disable=W0613
        """Clear search box."""
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.search_tb.Focus()


class CommandSwitchWindow(TemplateUserInputWindow):
    """Standard form to select from a list of command options.

    Args:
        context (list[str]): list of command options to choose from
        switches (list[str]): list of on/off switches
        message (str): window title message
        config (dict): dictionary of config dicts for options or switches
        recognize_access_key (bool): recognize '_' as mark of access key

    Returns:
        str: name of selected option

    Returns:
        tuple(str, dict): if ``switches`` option is used, returns a tuple
        of selection option name and dict of switches

    Example:
        This is an example with series of command options:

        >>> from pyrevit import forms
        >>> ops = ['option1', 'option2', 'option3', 'option4']
        >>> forms.CommandSwitchWindow.show(ops, message='Select Option')
        'option2'

        A more advanced example of combining command options, on/off switches,
        and option or switch configuration options:

        >>> from pyrevit import forms
        >>> ops = ['option1', 'option2', 'option3', 'option4']
        >>> switches = ['switch1', 'switch2']
        >>> cfgs = {'option1': { 'background': '0xFF55FF'}}
        >>> rops, rswitches = forms.CommandSwitchWindow.show(
        ...     ops,
        ...     switches=switches
        ...     message='Select Option',
        ...     config=cfgs,
        ...     recognize_access_key=False
        ...     )
        >>> rops
        'option2'
        >>> rswitches
        {'switch1': False, 'switch2': True}
    """

    xaml_source = 'CommandSwitchWindow.xaml'

    def _setup(self, **kwargs):
        self.selected_switch = ''
        self.Width = DEFAULT_CMDSWITCHWND_WIDTH
        self.Title = 'Command Options'

        message = kwargs.get('message', None)
        self._switches = kwargs.get('switches', [])
        if not isinstance(self._switches, dict):
            self._switches = dict.fromkeys(self._switches)

        configs = kwargs.get('config', None)

        self.message_label.Content = \
            message if message else 'Pick a command option:'

        self.Resources['pyRevitRecognizesAccessKey'] = \
            kwargs.get('recognize_access_key', DEFAULT_RECOGNIZE_ACCESS_KEY)

        # creates the switches first
        for switch, state in self._switches.items():
            my_togglebutton = framework.Controls.Primitives.ToggleButton()
            my_togglebutton.Content = switch
            my_togglebutton.IsChecked = state if state else False
            if configs and switch in configs:
                self._set_config(my_togglebutton, configs[switch])
            self.button_list.Children.Add(my_togglebutton)

        for option in self._context:
            my_button = framework.Controls.Button()
            my_button.Content = option
            my_button.Click += self.process_option
            if configs and option in configs:
                self._set_config(my_button, configs[option])
            self.button_list.Children.Add(my_button)

        self._setup_response()
        self.search_tb.Focus()
        self._filter_options()

    @staticmethod
    def _set_config(item, config_dict):
        bg = config_dict.get('background', None)
        if bg:
            bg = bg.replace('0x', '#')
            item.Background = Media.BrushConverter().ConvertFrom(bg)

    def _setup_response(self, response=None):
        if self._switches:
            switches = [x for x in self.button_list.Children
                        if hasattr(x, 'IsChecked')]
            self.response = response, {x.Content: x.IsChecked
                                       for x in switches}
        else:
            self.response = response

    def _filter_options(self, option_filter=None):
        if option_filter:
            self.search_tb.Tag = ''
            option_filter = option_filter.lower()
            for button in self.button_list.Children:
                if option_filter not in button.Content.lower():
                    button.Visibility = WPF_COLLAPSED
                else:
                    button.Visibility = WPF_VISIBLE
        else:
            self.search_tb.Tag = \
                'Type to Filter / Tab to Select / Enter or Click to Run'
            for button in self.button_list.Children:
                button.Visibility = WPF_VISIBLE

    def _get_active_button(self):
        buttons = []
        for button in self.button_list.Children:
            if button.Visibility == WPF_VISIBLE:
                buttons.append(button)
        if len(buttons) == 1:
            return buttons[0]
        else:
            for x in buttons:
                if x.IsFocused:
                    return x

    def handle_click(self, sender, args):    #pylint: disable=W0613
        """Handle mouse click."""
        self.Close()

    def handle_input_key(self, sender, args):
        """Handle keyboard inputs."""
        if args.Key == Input.Key.Escape:
            if self.search_tb.Text:
                self.search_tb.Text = ''
            else:
                self.Close()
        elif args.Key == Input.Key.Enter:
            active_button = self._get_active_button()
            if active_button:
                self.process_option(active_button, None)
                args.Handled = True
        elif args.Key != Input.Key.Tab \
                and args.Key != Input.Key.Space\
                and args.Key != Input.Key.LeftShift\
                and args.Key != Input.Key.RightShift:
            self.search_tb.Focus()

    def search_txt_changed(self, sender, args):    #pylint: disable=W0613
        """Handle text change in search box."""
        self._filter_options(option_filter=self.search_tb.Text)

    def process_option(self, sender, args):    #pylint: disable=W0613
        """Handle click on command option button."""
        self.Close()
        if sender:
            self._setup_response(response=sender.Content)


class GetValueWindow(TemplateUserInputWindow):
    """Standard form to get simple values from user.

    Args:


    Example:
        >>> from pyrevit import forms
        >>> items = ['item1', 'item2', 'item3']
        >>> forms.SelectFromList.show(items, button_name='Select Item')
        >>> ['item1']
    """

    xaml_source = 'GetValueWindow.xaml'

    def _setup(self, **kwargs):
        self.Width = 400
        # determine value type
        self.value_type = kwargs.get('value_type', 'string')
        value_prompt = kwargs.get('prompt', None)
        value_default = kwargs.get('default', None)
        self.reserved_values = kwargs.get('reserved_values', [])

        # customize window based on type
        if self.value_type == 'string':
            self.show_element(self.stringPanel_dp)
            self.stringValue_tb.Text = value_default if value_default else ''
            self.stringValue_tb.Focus()
            self.stringValue_tb.SelectAll()
            self.stringPrompt.Text = \
                value_prompt if value_prompt else 'Enter string:'
            if self.reserved_values:
                self.string_value_changed(None, None)
        elif self.value_type == 'dropdown':
            self.show_element(self.dropdownPanel_db)
            self.dropdownPrompt.Text = \
                value_prompt if value_prompt else 'Pick one value:'
            self.dropdown_cb.ItemsSource = self._context
            if value_default:
                self.dropdown_cb.SelectedItem = value_default
        elif self.value_type == 'date':
            self.show_element(self.datePanel_dp)
            self.datePrompt.Text = \
                value_prompt if value_prompt else 'Pick date:'
        elif self.value_type == 'slider':
            self.show_element(self.sliderPanel_sp)
            self.sliderPrompt.Text = value_prompt
            self.numberPicker.Minimum = kwargs.get('min', 0)
            self.numberPicker.Maximum = kwargs.get('max', 100)
            self.numberPicker.Value = \
                value_default if isinstance(value_default, float) \
                    else self.numberPicker.Minimum

    def string_value_changed(self, sender, args): #pylint: disable=unused-argument
        """Handle string vlaue update event."""
        filtered_rvalues = \
            sorted([x for x in self.reserved_values
                    if self.stringValue_tb.Text == str(x)])
        similar_rvalues = \
            sorted([x for x in self.reserved_values
                    if self.stringValue_tb.Text in str(x)],
                   reverse=True)
        filtered_rvalues.extend(similar_rvalues)
        if filtered_rvalues:
            self.reservedValuesList.ItemsSource = filtered_rvalues
            self.show_element(self.reservedValuesListPanel)
            self.okayButton.IsEnabled = \
                self.stringValue_tb.Text not in filtered_rvalues
        else:
            self.reservedValuesList.ItemsSource = []
            self.hide_element(self.reservedValuesListPanel)
            self.okayButton.IsEnabled = True

    def select(self, sender, args):    #pylint: disable=W0613
        """Process input data and set the response."""
        self.Close()
        if self.value_type == 'string':
            self.response = self.stringValue_tb.Text
        elif self.value_type == 'dropdown':
            self.response = self.dropdown_cb.SelectedItem
        elif self.value_type == 'date':
            if self.datePicker.SelectedDate:
                datestr = self.datePicker.SelectedDate.ToString("MM/dd/yyyy")
                self.response = datetime.datetime.strptime(datestr, r'%m/%d/%Y')
            else:
                self.response = None
        elif self.value_type == 'slider':
            self.response = self.numberPicker.Value


class TemplatePromptBar(WPFWindow):
    """Template context-manager class for creating prompt bars.

    Prompt bars are show at the top of the active Revit window and are
    designed for better prompt visibility.

    Args:
        height (int): window height
        **kwargs: other arguments to be passed to :func:`_setup`
    """

    xaml_source = 'TemplatePromptBar.xaml'

    def __init__(self, height=32, **kwargs):
        """Initialize user prompt window."""
        WPFWindow.__init__(self,
                           op.join(XAML_FILES_DIR, self.xaml_source))

        self.user_height = height
        self.update_window()
        self._setup(**kwargs)

    def update_window(self):
        """Update the prompt bar to match Revit window."""
        screen_area = HOST_APP.proc_screen_workarea
        scale_factor = 1.0 / HOST_APP.proc_screen_scalefactor
        top = left = width = height = 0

        window_rect = revit.ui.get_window_rectangle()

        # set width and height
        width = window_rect.Right - window_rect.Left
        height = self.user_height

        top = window_rect.Top
        # in maximized window, the top might be off the active screen
        # due to windows thicker window frames
        # lets cut the height and re-adjust the top
        top_diff = abs(screen_area.Top - top)
        if 10 > top_diff > 0 and top_diff < height:
            height -= top_diff
            top = screen_area.Top

        left = window_rect.Left
        # in maximized window, Left also might be off the active screen
        # due to windows thicker window frames
        # let's fix the width to accomodate the extra pixels as well
        left_diff = abs(screen_area.Left - left)
        if 10 > left_diff > 0 and left_diff < width:
            # deduct two times the left negative offset since this extra
            # offset happens on both left and right side
            width -= left_diff * 2
            left = screen_area.Left

        self.Top = top * scale_factor
        self.Left = left * scale_factor
        self.Width = width * scale_factor
        self.Height = height

    def _setup(self, **kwargs):
        """Private method to be overriden by subclasses for prompt setup."""
        pass

    def _prepare(self):
        pass

    def _cleanup(self):
        pass

    def __enter__(self):
        self._prepare()
        self.Show()
        return self

    def __exit__(self, exception, exception_value, traceback):
        self._cleanup()
        self.Close()


class WarningBar(TemplatePromptBar):
    """Show warning bar at the top of Revit window.

    Args:
        title (string): warning bar text

    Example:
        >>> with WarningBar(title='my warning'):
        ...    # do stuff
    """

    xaml_source = 'WarningBar.xaml'

    def _setup(self, **kwargs):
        self.message_tb.Text = kwargs.get('title', '')


class ProgressBar(TemplatePromptBar):
    """Show progress bar at the top of Revit window.

    Args:
        title (string): progress bar text, defaults to 0/100 progress format
        indeterminate (bool): create indeterminate progress bar
        cancellable (bool): add cancel button to progress bar
        step (int): update progress intervals

    Example:
        >>> from pyrevit import forms
        >>> count = 1
        >>> with forms.ProgressBar(title='my command progress message') as pb:
        ...    # do stuff
        ...    pb.update_progress(count, 100)
        ...    count += 1

        Progress bar title could also be customized to show the current and
        total progress values. In example below, the progress bar message
        will be in format "0 of 100"

        >>> with forms.ProgressBar(title='{value} of {max_value}') as pb:

        By default progress bar updates the progress every time the
        .update_progress method is called. For operations with a large number
        of max steps, the gui update process time will have a significate
        effect on the overall execution time of the command. In these cases,
        set the value of step argument to something larger than 1. In example
        below, the progress bar updates once per every 10 units of progress.

        >>> with forms.ProgressBar(title='message', steps=10):

        Progress bar could also be set to indeterminate for operations of
        unknown length. In this case, the progress bar will show an infinitely
        running ribbon:

        >>> with forms.ProgressBar(title='message', indeterminate=True):

        if cancellable is set on the object, a cancel button will show on the
        progress bar and .cancelled attribute will be set on the ProgressBar
        instance if users clicks on cancel button:

        >>> with forms.ProgressBar(title='message',
        ...                        cancellable=True) as pb:
        ...    # do stuff
        ...    if pb.cancelled:
        ...        # wrap up and cancel operation
    """

    xaml_source = 'ProgressBar.xaml'

    def _setup(self, **kwargs):
        self.max_value = 1
        self.new_value = 0
        self.step = kwargs.get('step', 0)

        self.cancelled = False
        has_cancel = kwargs.get('cancellable', False)
        if has_cancel:
            self.show_element(self.cancel_b)

        self.pbar.IsIndeterminate = kwargs.get('indeterminate', False)
        self._title = kwargs.get('title', '{value}/{max_value}')
        self._hostwnd = None
        self._host_task_pbar = None

    def _prepare(self):
        self._hostwnd = revit.ui.get_mainwindow()
        if self._hostwnd:
            self._host_task_pbar = System.Windows.Shell.TaskbarItemInfo()
            self._hostwnd.TaskbarItemInfo = self._host_task_pbar

    def _cleanup(self):
        if self._hostwnd:
            self._hostwnd.TaskbarItemInfo = None

    def _update_task_pbar(self):
        if self._host_task_pbar is not None:
            if self.indeterminate:
                self._host_task_pbar.ProgressState = \
                    System.Windows.Shell.TaskbarItemProgressState.Indeterminate
            else:
                self._host_task_pbar.ProgressState = \
                    System.Windows.Shell.TaskbarItemProgressState.Normal
                self._host_task_pbar.ProgressValue = \
                    (self.new_value / float(self.max_value))

    def _update_pbar(self):
        self.update_window()
        self.pbar.Maximum = self.max_value
        self.pbar.Value = self.new_value

        # updating title
        title_text = \
            string.Formatter().vformat(self._title,
                                       (),
                                       coreutils.SafeDict(
                                           {'value': self.new_value,
                                            'max_value': self.max_value}
                                           ))

        self.pbar_text.Text = title_text

    def _donothing(self):
        pass

    def _dispatch_updater(self):
        # ask WPF dispatcher for gui update
        self.pbar.Dispatcher.Invoke(System.Action(self._update_pbar),
                                    Threading.DispatcherPriority.Background)
        # ask WPF dispatcher for gui update
        self.pbar.Dispatcher.Invoke(System.Action(self._update_task_pbar),
                                    Threading.DispatcherPriority.Background)
        # give it a little free time to update ui
        self.pbar.Dispatcher.Invoke(System.Action(self._donothing),
                                    Threading.DispatcherPriority.Background)

    @property
    def title(self):
        """Progress bar title."""
        return self._title

    @title.setter
    def title(self, value):
        if isinstance(value, str):
            self._title = value    #pylint: disable=W0201

    @property
    def indeterminate(self):
        """Progress bar indeterminate state."""
        return self.pbar.IsIndeterminate

    @indeterminate.setter
    def indeterminate(self, value):
        self.pbar.IsIndeterminate = value

    def clicked_cancel(self, sender, args):    #pylint: disable=W0613
        """Handler for cancel button clicked event."""
        self.cancel_b.Content = 'Cancelling...'
        self.cancelled = True    #pylint: disable=W0201

    def reset(self):
        """Reset progress value to 0."""
        self.update_progress(0, 1)

    def update_progress(self, new_value, max_value=1):
        """Update progress bar state with given min, max values.

        Args:
            new_value (float): current progress value
            max_value (float): total progress value
        """
        self.max_value = max_value    #pylint: disable=W0201
        self.new_value = new_value    #pylint: disable=W0201
        if self.new_value == 0:
            self._dispatch_updater()
        elif self.step > 0:
            if self.new_value % self.step == 0:
                self._dispatch_updater()
        else:
            self._dispatch_updater()


class SearchPrompt(WPFWindow):
    """Standard prompt for pyRevit search.

    Args:
        search_db (list): list of possible search targets
        search_tip (str): text to show in grayscale when search box is empty
        switches (str): list of switches
        width (int): width of search prompt window
        height (int): height of search prompt window

    Returns:
        str, dict: matched strings, and dict of switches if provided
        str: matched string if switches are not provided.

    Example:
        >>> from pyrevit import forms
        >>> # assume search input of '/switch1 target1'
        >>> matched_str, args, switches = forms.SearchPrompt.show(
        ...     search_db=['target1', 'target2', 'target3', 'target4'],
        ...     switches=['/switch1', '/switch2'],
        ...     search_tip='pyRevit Search'
        ...     )
        ... matched_str
        'target1'
        ... args
        ['--help', '--branch', 'branchname']
        ... switches
        {'/switch1': True, '/switch2': False}
    """
    def __init__(self, search_db, width, height, **kwargs):
        """Initialize search prompt window."""
        WPFWindow.__init__(self,
                           op.join(XAML_FILES_DIR, 'SearchPrompt.xaml'))
        self.Width = width
        self.MinWidth = self.Width
        self.Height = height

        self.search_tip = kwargs.get('search_tip', '')

        if isinstance(search_db, list):
            self._search_db = None
            self._search_db_keys = search_db
        elif isinstance(search_db, dict):
            self._search_db = search_db
            self._search_db_keys = sorted(self._search_db.keys())
        else:
            raise PyRevitException("Unknown search database type")

        self._search_res = None
        self._switches = kwargs.get('switches', [])
        self._setup_response()

        self.search_tb.Focus()
        self.hide_element(self.tab_icon)
        self.hide_element(self.return_icon)
        self.search_tb.Text = ''
        self.set_search_results()

    def _setup_response(self, response=None):
        switch_dict = dict.fromkeys(self._switches)
        for switch in self.search_term_switches:
            switch_dict[switch] = True
        arguments = self.search_term_args
        # remove first arg which is command name
        if len(arguments) >= 1:
            arguments = arguments[1:]

        self.response = response, arguments, switch_dict

    @property
    def search_input(self):
        """Current search input."""
        return self.search_tb.Text

    @search_input.setter
    def search_input(self, value):
        self.search_tb.Text = value
        self.search_tb.CaretIndex = len(value)

    @property
    def search_input_parts(self):
        """Current cleaned up search term."""
        return self.search_input.strip().split()

    @property
    def search_term(self):
        """Current cleaned up search term."""
        return self.search_input.lower().strip()

    @property
    def search_term_switches(self):
        """Find matching switches in search term."""
        switches = set()
        for stpart in self.search_input_parts:
            if stpart.lower() in self._switches:
                switches.add(stpart)
        return switches

    @property
    def search_term_args(self):
        """Find arguments in search term."""
        args = []
        switches = self.search_term_switches
        for spart in self.search_input_parts:
            if spart.lower() not in switches:
                args.append(spart)
        return args

    @property
    def search_term_main(self):
        """Current cleaned up search term without the listed switches."""
        if len(self.search_term_args) >= 1:
            return self.search_term_args[0]
        else:
            return ''

    @property
    def search_matches(self):
        """List of matches for the given search term."""
        # remove duplicates while keeping order
        # results = list(set(self._search_results))
        return OrderedDict.fromkeys(self._search_results).keys()

    def update_results_display(self, fill_match=False):
        """Update search prompt results based on current input text."""
        self.directmatch_tb.Text = ''
        self.wordsmatch_tb.Text = ''

        results = self.search_matches
        res_cout = len(results)

        mlogger.debug('unique results count: %s', res_cout)
        mlogger.debug('unique results: %s', results)

        if res_cout > 1:
            self.show_element(self.tab_icon)
            self.hide_element(self.return_icon)
        elif res_cout == 1:
            self.hide_element(self.tab_icon)
            self.show_element(self.return_icon)
        else:
            self.hide_element(self.tab_icon)
            self.hide_element(self.return_icon)

        if self._result_index >= res_cout:
            self._result_index = 0   #pylint: disable=W0201

        if self._result_index < 0:
            self._result_index = res_cout - 1   #pylint: disable=W0201

        if not self.search_input:
            self.directmatch_tb.Text = self.search_tip
            return

        if results:
            input_term = self.search_term
            cur_res = results[self._result_index]
            mlogger.debug('current result: %s', cur_res)
            if fill_match:
                self.search_input = cur_res
            else:
                if cur_res.lower().startswith(input_term):
                    self.directmatch_tb.Text = \
                        self.search_input + cur_res[len(input_term):]
                    mlogger.debug('directmatch_tb.Text: %s',
                                  self.directmatch_tb.Text)
                else:
                    self.wordsmatch_tb.Text = '- {}'.format(cur_res)
                    mlogger.debug('wordsmatch_tb.Text: %s',
                                  self.wordsmatch_tb.Text)
            tooltip = self._search_db.get(cur_res, None)
            if tooltip:
                self.tooltip_tb.Text = tooltip
                self.show_element(self.tooltip_tb)
            else:
                self.hide_element(self.tooltip_tb)
            self._search_res = cur_res
            return True
        return False

    def set_search_results(self, *args):
        """Set search results for returning."""
        self._result_index = 0
        self._search_results = []

        mlogger.debug('search input: %s', self.search_input)
        mlogger.debug('search term: %s', self.search_term)
        mlogger.debug('search term (main): %s', self.search_term_main)
        mlogger.debug('search term (parts): %s', self.search_input_parts)
        mlogger.debug('search term (args): %s', self.search_term_args)
        mlogger.debug('search term (switches): %s', self.search_term_switches)

        for resultset in args:
            mlogger.debug('result set: %s}', resultset)
            self._search_results.extend(sorted(resultset))

        mlogger.debug('results: %s', self._search_results)

    def find_direct_match(self, input_text):
        """Find direct text matches in search term."""
        results = []
        if input_text:
            for cmd_name in self._search_db_keys:
                if cmd_name.lower().startswith(input_text):
                    results.append(cmd_name)

        return results

    def find_word_match(self, input_text):
        """Find direct word matches in search term."""
        results = []
        if input_text:
            cur_words = input_text.split(' ')
            for cmd_name in self._search_db_keys:
                if all([x in cmd_name.lower() for x in cur_words]):
                    results.append(cmd_name)

        return results

    def search_txt_changed(self, sender, args):    #pylint: disable=W0613
        """Handle text changed event."""
        input_term = self.search_term_main
        dmresults = self.find_direct_match(input_term)
        wordresults = self.find_word_match(input_term)
        self.set_search_results(dmresults, wordresults)
        self.update_results_display()

    def handle_kb_key(self, sender, args):    #pylint: disable=W0613
        """Handle keyboard input event."""
        shiftdown = Input.Keyboard.IsKeyDown(Input.Key.LeftShift) \
            or Input.Keyboard.IsKeyDown(Input.Key.RightShift)
        # Escape: set response to none and close
        if args.Key == Input.Key.Escape:
            self._setup_response()
            self.Close()
        # Enter: close, returns matched response automatically
        elif args.Key == Input.Key.Enter:
            if self.search_tb.Text != '':
                self._setup_response(response=self._search_res)
                args.Handled = True
                self.Close()
        # Shift+Tab, Tab: Cycle through matches
        elif args.Key == Input.Key.Tab and shiftdown:
            self._result_index -= 1
            self.update_results_display()
        elif args.Key == Input.Key.Tab:
            self._result_index += 1
            self.update_results_display()
        # Up, Down: Cycle through matches
        elif args.Key == Input.Key.Up:
            self._result_index -= 1
            self.update_results_display()
        elif args.Key == Input.Key.Down:
            self._result_index += 1
            self.update_results_display()
        # Right, End: Autocomplete with displayed match
        elif args.Key in [Input.Key.Right,
                          Input.Key.End]:
            self.update_results_display(fill_match=True)

    @classmethod
    def show(cls, search_db,    #pylint: disable=W0221
             width=DEFAULT_SEARCHWND_WIDTH,
             height=DEFAULT_SEARCHWND_HEIGHT, **kwargs):
        """Show search prompt."""
        dlg = cls(search_db, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response


class RevisionOption(TemplateListItem):
    """Revision wrapper for :func:`select_revisions`."""
    def __init__(self, revision_element):
        super(RevisionOption, self).__init__(revision_element)

    @property
    def name(self):
        """Revision name (description)."""
        revnum = self.item.SequenceNumber
        if hasattr(self.item, 'RevisionNumber'):
            revnum = self.item.RevisionNumber
        return '{}-{}-{}'.format(revnum,
                                 self.item.Description,
                                 self.item.RevisionDate)


class SheetOption(TemplateListItem):
    """Sheet wrapper for :func:`select_sheets`."""
    def __init__(self, sheet_element):
        super(SheetOption, self).__init__(sheet_element)

    @property
    def name(self):
        """Sheet name."""
        return '{} - {}{}' \
            .format(self.item.SheetNumber,
                    self.item.Name,
                    ' (placeholder)' if self.item.IsPlaceholder else '')

    @property
    def number(self):
        """Sheet number."""
        return self.item.SheetNumber


class ViewOption(TemplateListItem):
    """View wrapper for :func:`select_views`."""
    def __init__(self, view_element):
        super(ViewOption, self).__init__(view_element)

    @property
    def name(self):
        """View name."""
        return '{} ({})'.format(revit.query.get_name(self.item),
                                self.item.ViewType)


class LevelOption(TemplateListItem):
    """Level wrapper for :func:`select_levels`."""
    def __init__(self, level_element):
        super(LevelOption, self).__init__(level_element)

    @property
    def name(self):
        """Level name."""
        return revit.query.get_name(self.item)


class FamilyParamOption(TemplateListItem):
    """Level wrapper for :func:`select_family_parameters`."""
    def __init__(self, fparam, builtin=False, labeled=False):
        super(FamilyParamOption, self).__init__(fparam)
        self.isbuiltin = builtin
        self.islabeled = labeled

    @property
    def name(self):
        """Family Parameter name."""
        return self.item.Definition.Name

    @property
    def istype(self):
        """Is type parameter."""
        return not self.item.IsInstance


def select_revisions(title='Select Revision',
                     button_name='Select',
                     width=DEFAULT_INPUTWINDOW_WIDTH,
                     multiple=True,
                     filterfunc=None,
                     doc=None):
    """Standard form for selecting revisions.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiselect (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for revisions; defaults to active document

    Returns:
        list[DB.Revision]: list of selected revisions

    Example:
        >>> from pyrevit import forms
        >>> forms.select_revisions()
        ... [<Autodesk.Revit.DB.Revision object>,
        ...  <Autodesk.Revit.DB.Revision object>]
    """
    doc = doc or DOCS.doc
    revisions = sorted(revit.query.get_revisions(doc=doc),
                       key=lambda x: x.SequenceNumber)

    if filterfunc:
        revisions = filter(filterfunc, revisions)

    # ask user for revisions
    selected_revs = SelectFromList.show(
        [RevisionOption(x) for x in revisions],
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True
        )

    return selected_revs


def select_sheets(title='Select Sheets',
                  button_name='Select',
                  width=DEFAULT_INPUTWINDOW_WIDTH,
                  multiple=True,
                  filterfunc=None,
                  doc=None,
                  include_placeholder=True,
                  use_selection=False):
    """Standard form for selecting sheets.

    Sheets are grouped into sheet sets and sheet set can be selected from
    a drop down box at the top of window.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for sheets; defaults to active document
        use_selection (bool, optional):
            ask if user wants to use currently selected sheets.
    Returns:
        list[DB.ViewSheet]: list of selected sheets

    Example:
        >>> from pyrevit import forms
        >>> forms.select_sheets()
        ... [<Autodesk.Revit.DB.ViewSheet object>,
        ...  <Autodesk.Revit.DB.ViewSheet object>]
    """
    doc = doc or DOCS.doc

    # check for previously selected sheets
    if use_selection:
        current_selected_sheets = revit.get_selection() \
                                       .include(DB.ViewSheet) \
                                       .elements
        if filterfunc:
            current_selected_sheets = \
                filter(filterfunc, current_selected_sheets)

        if not include_placeholder:
            current_selected_sheets = \
                [x for x in current_selected_sheets if not x.IsPlaceholder]

        if current_selected_sheets \
                and ask_to_use_selected("sheets",
                                        count=len(current_selected_sheets),
                                        multiple=multiple):
            return current_selected_sheets \
                if multiple else current_selected_sheets[0]

    # otherwise get all sheets and prompt for selection
    all_ops = {}
    all_sheets = DB.FilteredElementCollector(doc) \
                   .OfClass(DB.ViewSheet) \
                   .WhereElementIsNotElementType() \
                   .ToElements()

    if filterfunc:
        all_sheets = filter(filterfunc, all_sheets)

    if not include_placeholder:
        all_sheets = [x for x in all_sheets if not x.IsPlaceholder]

    all_sheets_ops = sorted([SheetOption(x) for x in all_sheets],
                            key=lambda x: x.number)
    all_ops['All Sheets'] = all_sheets_ops

    sheetsets = revit.query.get_sheet_sets(doc)
    for sheetset in sheetsets:
        sheetset_sheets = \
            [x for x in sheetset.Views if isinstance(x, DB.ViewSheet)]
        if filterfunc:
            sheetset_sheets = filter(filterfunc, sheetset_sheets)
        sheetset_ops = sorted([SheetOption(x) for x in sheetset_sheets],
                              key=lambda x: x.number)
        all_ops[sheetset.Name] = sheetset_ops

    # ask user for multiple sheets
    selected_sheets = SelectFromList.show(
        all_ops,
        title=title,
        group_selector_title='Sheet Sets:',
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True,
        default_group='All Sheets'
        )

    return selected_sheets


def select_views(title='Select Views',
                 button_name='Select',
                 width=DEFAULT_INPUTWINDOW_WIDTH,
                 multiple=True,
                 filterfunc=None,
                 doc=None,
                 use_selection=False):
    """Standard form for selecting views.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for views; defaults to active document
        use_selection (bool, optional):
            ask if user wants to use currently selected views.
    Returns:
        list[DB.View]: list of selected views

    Example:
        >>> from pyrevit import forms
        >>> forms.select_views()
        ... [<Autodesk.Revit.DB.View object>,
        ...  <Autodesk.Revit.DB.View object>]
    """
    doc = doc or DOCS.doc

    # check for previously selected sheets
    if use_selection:
        current_selected_views = revit.get_selection() \
                                      .include(DB.View) \
                                      .elements
        if filterfunc:
            current_selected_views = \
                filter(filterfunc, current_selected_views)

        if current_selected_views \
                and ask_to_use_selected("views",
                                        count=len(current_selected_views),
                                        multiple=multiple):
            return current_selected_views \
                if multiple else current_selected_views[0]

    # otherwise get all sheets and prompt for selection
    all_graphviews = revit.query.get_all_views(doc=doc)

    if filterfunc:
        all_graphviews = filter(filterfunc, all_graphviews)

    selected_views = SelectFromList.show(
        sorted([ViewOption(x) for x in all_graphviews],
               key=lambda x: x.name),
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True
        )

    return selected_views


def select_levels(title='Select Levels',
                  button_name='Select',
                  width=DEFAULT_INPUTWINDOW_WIDTH,
                  multiple=True,
                  filterfunc=None,
                  doc=None,
                  use_selection=False):
    """Standard form for selecting levels.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for levels; defaults to active document
        use_selection (bool, optional):
            ask if user wants to use currently selected levels.
    Returns:
        list[DB.Level]: list of selected levels

    Example:
        >>> from pyrevit import forms
        >>> forms.select_levels()
        ... [<Autodesk.Revit.DB.Level object>,
        ...  <Autodesk.Revit.DB.Level object>]
    """
    doc = doc or DOCS.doc

    # check for previously selected sheets
    if use_selection:
        current_selected_levels = revit.get_selection() \
                                       .include(DB.Level) \
                                       .elements

        if filterfunc:
            current_selected_levels = \
                filter(filterfunc, current_selected_levels)

        if current_selected_levels \
                and ask_to_use_selected("levels",
                                        count=len(current_selected_levels),
                                        multiple=multiple):
            return current_selected_levels \
                if multiple else current_selected_levels[0]

    all_levels = \
        revit.query.get_elements_by_categories(
            [DB.BuiltInCategory.OST_Levels],
            doc=doc
            )

    if filterfunc:
        all_levels = filter(filterfunc, all_levels)

    selected_levels = SelectFromList.show(
        sorted([LevelOption(x) for x in all_levels],
               key=lambda x: x.Elevation),
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True,
        )
    return selected_levels


def select_viewtemplates(title='Select View Templates',
                         button_name='Select',
                         width=DEFAULT_INPUTWINDOW_WIDTH,
                         multiple=True,
                         filterfunc=None,
                         doc=None):
    """Standard form for selecting view templates.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiselect (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for views; defaults to active document

    Returns:
        list[DB.View]: list of selected view templates

    Example:
        >>> from pyrevit import forms
        >>> forms.select_viewtemplates()
        ... [<Autodesk.Revit.DB.View object>,
        ...  <Autodesk.Revit.DB.View object>]
    """
    doc = doc or DOCS.doc
    all_viewtemplates = revit.query.get_all_view_templates(doc=doc)

    if filterfunc:
        all_viewtemplates = filter(filterfunc, all_viewtemplates)

    selected_viewtemplates = SelectFromList.show(
        sorted([ViewOption(x) for x in all_viewtemplates],
               key=lambda x: x.name),
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True
        )

    return selected_viewtemplates


def select_schedules(title='Select Schedules',
                     button_name='Select',
                     width=DEFAULT_INPUTWINDOW_WIDTH,
                     multiple=True,
                     filterfunc=None,
                     doc=None):
    """Standard form for selecting schedules.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiselect (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for views; defaults to active document

    Returns:
        list[DB.ViewSchedule]: list of selected schedules

    Example:
        >>> from pyrevit import forms
        >>> forms.select_schedules()
        ... [<Autodesk.Revit.DB.ViewSchedule object>,
        ...  <Autodesk.Revit.DB.ViewSchedule object>]
    """
    doc = doc or DOCS.doc
    all_schedules = revit.query.get_all_schedules(doc=doc)

    if filterfunc:
        all_schedules = filter(filterfunc, all_schedules)

    selected_schedules = \
        SelectFromList.show(
            sorted([ViewOption(x) for x in all_schedules],
                   key=lambda x: x.name),
            title=title,
            button_name=button_name,
            width=width,
            multiselect=multiple,
            checked_only=True
        )

    return selected_schedules


def select_open_docs(title='Select Open Documents',
                     button_name='OK',
                     width=DEFAULT_INPUTWINDOW_WIDTH,    #pylint: disable=W0613
                     multiple=True,
                     check_more_than_one=True,
                     filterfunc=None):
    """Standard form for selecting open documents.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiselect (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.

    Returns:
        list[DB.Document]: list of selected documents

    Example:
        >>> from pyrevit import forms
        >>> forms.select_open_docs()
        ... [<Autodesk.Revit.DB.Document object>,
        ...  <Autodesk.Revit.DB.Document object>]
    """
    # find open documents other than the active doc
    open_docs = [d for d in revit.docs if not d.IsLinked]    #pylint: disable=E1101
    if check_more_than_one:
        open_docs.remove(revit.doc)    #pylint: disable=E1101

    if not open_docs:
        alert('Only one active document is found. '
              'At least two documents must be open. '
              'Operation cancelled.')
        return

    return SelectFromList.show(
        open_docs,
        name_attr='Title',
        multiselect=multiple,
        title=title,
        button_name=button_name,
        filterfunc=filterfunc
        )


def select_titleblocks(title='Select Titleblock',
                       button_name='Select',
                       no_tb_option='No Title Block',
                       width=DEFAULT_INPUTWINDOW_WIDTH,
                       multiple=False,
                       filterfunc=None,
                       doc=None):
    """Standard form for selecting a titleblock.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        no_tb_option (str, optional): name of option for no title block
        width (int, optional): width of list window
        multiselect (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for titleblocks; defaults to active document

    Returns:
        DB.ElementId: selected titleblock id.

    Example:
        >>> from pyrevit import forms
        >>> forms.select_titleblocks()
        ... <Autodesk.Revit.DB.ElementId object>
    """
    doc = doc or DOCS.doc
    titleblocks = DB.FilteredElementCollector(doc)\
                    .OfCategory(DB.BuiltInCategory.OST_TitleBlocks)\
                    .WhereElementIsElementType()\
                    .ToElements()

    tblock_dict = {'{}: {}'.format(tb.FamilyName,
                                   revit.query.get_name(tb)): tb.Id
                   for tb in titleblocks}
    tblock_dict[no_tb_option] = DB.ElementId.InvalidElementId
    selected_titleblocks = SelectFromList.show(sorted(tblock_dict.keys()),
                                               title=title,
                                               button_name=button_name,
                                               width=width,
                                               multiselect=multiple,
                                               filterfunc=filterfunc)
    if selected_titleblocks:
        if multiple:
            return [tblock_dict[x] for x in selected_titleblocks]
        else:
            return tblock_dict[selected_titleblocks]


def select_swatch(title='Select Color Swatch', button_name='Select'):
    """Standard form for selecting a color swatch.

    Args:
        title (str, optional): swatch list window title
        button_name (str, optional): swatch list window button caption

    Returns:
        pyrevit.coreutils.colors.RGB: rgb color

    Example:
        >>> from pyrevit import forms
        >>> forms.select_swatch(title="Select Text Color")
        ... <RGB #CD8800>
    """
    itemplate = utils.load_ctrl_template(
        os.path.join(XAML_FILES_DIR, "SwatchContainerStyle.xaml")
        )
    swatch = SelectFromList.show(
        colors.COLORS.values(),
        title=title,
        button_name=button_name,
        width=300,
        multiselect=False,
        item_template=itemplate
        )

    return swatch


def select_image(images, title='Select Image', button_name='Select'):
    """Standard form for selecting an image.

    Args:
        images (list[str] | list[framework.Imaging.BitmapImage]):
            list of image file paths or bitmaps
        title (str, optional): swatch list window title
        button_name (str, optional): swatch list window button caption

    Returns:
        str : path of the selected image

    Example:
        >>> from pyrevit import forms
        >>> forms.select_image(['C:/path/to/image1.png',
                                'C:/path/to/image2.png'],
                                title="Select Variation")
        ... 'C:/path/to/image1.png'
    """
    ptemplate = utils.load_itemspanel_template(
        os.path.join(XAML_FILES_DIR, "ImageListPanelStyle.xaml")
        )

    itemplate = utils.load_ctrl_template(
        os.path.join(XAML_FILES_DIR, "ImageListContainerStyle.xaml")
        )

    bitmap_images = {}
    for imageobj in images:
        if isinstance(imageobj, str):
            img = utils.bitmap_from_file(imageobj)
            if img:
                bitmap_images[img] = imageobj
        elif isinstance(imageobj, framework.Imaging.BitmapImage):
            bitmap_images[imageobj] = imageobj

    selected_image = SelectFromList.show(
        sorted(bitmap_images.keys(), key=lambda x: x.UriSource.AbsolutePath),
        title=title,
        button_name=button_name,
        width=500,
        multiselect=False,
        item_template=itemplate,
        items_panel_template=ptemplate
        )

    return bitmap_images.get(selected_image, None)


def select_parameters(src_element,
                      title='Select Parameters',
                      button_name='Select',
                      multiple=True,
                      filterfunc=None,
                      include_instance=True,
                      include_type=True,
                      exclude_readonly=True):
    """Standard form for selecting parameters from given element.

    Args:
        src_element (DB.Element): source element
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        multiselect (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        include_instance (bool, optional): list instance parameters
        include_type (bool, optional): list type parameters
        exclude_readonly (bool, optional): only shows parameters that are editable

    Returns:
        list[:obj:`ParamDef`]: list of paramdef objects

    Example:
        >>> forms.select_parameter(
        ...     src_element,
        ...     title='Select Parameters',
        ...     multiple=True,
        ...     include_instance=True,
        ...     include_type=True
        ... )
        ... [<ParamDef >, <ParamDef >]
    """
    param_defs = []
    non_storage_type = coreutils.get_enum_none(DB.StorageType)
    if include_instance:
        # collect instance parameters
        param_defs.extend(
            [ParamDef(name=x.Definition.Name,
                      istype=False,
                      definition=x.Definition,
                      isreadonly=x.IsReadOnly)
             for x in src_element.Parameters
             if x.StorageType != non_storage_type]
        )

    if include_type:
        # collect type parameters
        src_type = revit.query.get_type(src_element)
        param_defs.extend(
            [ParamDef(name=x.Definition.Name,
                      istype=True,
                      definition=x.Definition,
                      isreadonly=x.IsReadOnly)
             for x in src_type.Parameters
             if x.StorageType != non_storage_type]
        )

    if exclude_readonly:
        param_defs = filter(lambda x: not x.isreadonly, param_defs)

    if filterfunc:
        param_defs = filter(filterfunc, param_defs)

    param_defs.sort(key=lambda x: x.name)

    itemplate = utils.load_ctrl_template(
        os.path.join(XAML_FILES_DIR, "ParameterItemStyle.xaml")
        )
    selected_params = SelectFromList.show(
        param_defs,
        title=title,
        button_name=button_name,
        width=450,
        multiselect=multiple,
        item_template=itemplate
        )

    return selected_params


def select_family_parameters(family_doc,
                             title='Select Parameters',
                             button_name='Select',
                             multiple=True,
                             filterfunc=None,
                             include_instance=True,
                             include_type=True,
                             include_builtin=True,
                             include_labeled=True):
    """Standard form for selecting parameters from given family document.

    Args:
        family_doc (DB.Document): source family document
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        multiselect (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        include_instance (bool, optional): list instance parameters
        include_type (bool, optional): list type parameters
        include_builtin (bool, optional): list builtin parameters
        include_labeled (bool, optional): list parameters used as labels

    Returns:
        list[:obj:`DB.FamilyParameter`]: list of family parameter objects

    Example:
        >>> forms.select_family_parameters(
        ...     family_doc,
        ...     title='Select Parameters',
        ...     multiple=True,
        ...     include_instance=True,
        ...     include_type=True
        ... )
        ... [<DB.FamilyParameter >, <DB.FamilyParameter >]
    """
    family_doc = family_doc or DOCS.doc
    family_params = revit.query.get_family_parameters(family_doc)
    # get all params used in labeles
    label_param_ids = \
        [x.Id for x in revit.query.get_family_label_parameters(family_doc)]

    if filterfunc:
        family_params = filter(filterfunc, family_params)

    param_defs = []
    for family_param in family_params:
        if not include_instance and family_param.IsInstance:
            continue
        if not include_type and not family_param.IsInstance:
            continue
        if not include_builtin and family_param.Id.IntegerValue < 0:
            continue
        if not include_labeled and family_param.Id in label_param_ids:
            continue

        param_defs.append(
            FamilyParamOption(family_param,
                              builtin=family_param.Id.IntegerValue < 0,
                              labeled=family_param.Id in label_param_ids)
            )

    param_defs.sort(key=lambda x: x.name)

    itemplate = utils.load_ctrl_template(
        os.path.join(XAML_FILES_DIR, "FamilyParameterItemStyle.xaml")
        )
    selected_params = SelectFromList.show(
        {
            'All Parameters': param_defs,
            'Type Parameters': [x for x in param_defs if x.istype],
            'Built-in Parameters': [x for x in param_defs if x.isbuiltin],
            'Used as Label': [x for x in param_defs if x.islabeled],
        },
        title=title,
        button_name=button_name,
        group_selector_title='Parameter Filters:',
        width=450,
        multiselect=multiple,
        item_template=itemplate
        )

    return selected_params


def alert(msg, title=None, sub_msg=None, expanded=None, footer='',
          ok=True, cancel=False, yes=False, no=False, retry=False,
          warn_icon=True, options=None, exitscript=False):
    """Show a task dialog with given message.

    Args:
        msg (str): message to be displayed
        title (str, optional): task dialog title
        sub_msg (str, optional): sub message
        expanded (str, optional): expanded area message
        ok (bool, optional): show OK button, defaults to True
        cancel (bool, optional): show Cancel button, defaults to False
        yes (bool, optional): show Yes button, defaults to False
        no (bool, optional): show NO button, defaults to False
        retry (bool, optional): show Retry button, defaults to False
        options(list[str], optional): list of command link titles in order
        exitscript (bool, optional): exit if cancel or no, defaults to False

    Returns:
        bool: True if okay, yes, or retry, otherwise False

    Example:
        >>> from pyrevit import forms
        >>> forms.alert('Are you sure?',
        ...              ok=False, yes=True, no=True, exitscript=True)
    """
    # BUILD DIALOG
    cmd_name = EXEC_PARAMS.command_name
    if not title:
        title = cmd_name if cmd_name else 'pyRevit'
    tdlg = UI.TaskDialog(title)

    # process input types
    just_ok = ok and not any([cancel, yes, no, retry])

    options = options or []
    # add command links if any
    if options:
        clinks = coreutils.get_enum_values(UI.TaskDialogCommandLinkId)
        max_clinks = len(clinks)
        for idx, cmd in enumerate(options):
            if idx < max_clinks:
                tdlg.AddCommandLink(clinks[idx], cmd)
    # otherwise add buttons
    else:
        buttons = coreutils.get_enum_none(UI.TaskDialogCommonButtons)
        if yes:
            buttons |= UI.TaskDialogCommonButtons.Yes
        elif ok:
            buttons |= UI.TaskDialogCommonButtons.Ok

        if cancel:
            buttons |= UI.TaskDialogCommonButtons.Cancel
        if no:
            buttons |= UI.TaskDialogCommonButtons.No
        if retry:
            buttons |= UI.TaskDialogCommonButtons.Retry
        tdlg.CommonButtons = buttons

    # set texts
    tdlg.MainInstruction = msg
    tdlg.MainContent = sub_msg
    tdlg.ExpandedContent = expanded
    if footer:
        footer = footer.strip() + '\n'
    tdlg.FooterText = footer + 'pyRevit {}'.format(
        versionmgr.get_pyrevit_version().get_formatted()
        )
    tdlg.TitleAutoPrefix = False

    # set icon
    tdlg.MainIcon = \
        UI.TaskDialogIcon.TaskDialogIconWarning \
        if warn_icon else UI.TaskDialogIcon.TaskDialogIconNone

    # tdlg.VerificationText = 'verif'

    # SHOW DIALOG
    res = tdlg.Show()

    # PROCESS REPONSES
    # positive response
    mlogger.debug('alert result: %s', res)
    if res == UI.TaskDialogResult.Ok \
            or res == UI.TaskDialogResult.Yes \
            or res == UI.TaskDialogResult.Retry:
        if just_ok and exitscript:
            sys.exit()
        return True
    # negative response
    elif res == coreutils.get_enum_none(UI.TaskDialogResult) \
            or res == UI.TaskDialogResult.Cancel \
            or res == UI.TaskDialogResult.No:
        if exitscript:
            sys.exit()
        else:
            return False

    # command link response
    elif 'CommandLink' in str(res):
        tdresults = sorted(
            [x for x in coreutils.get_enum_values(UI.TaskDialogResult)
             if 'CommandLink' in str(x)]
            )
        residx = tdresults.index(res)
        return options[residx]
    elif exitscript:
        sys.exit()
    else:
        return False


def alert_ifnot(condition, msg, *args, **kwargs):
    """Show a task dialog with given message if condition is NOT met.

    Args:
        condition (bool): condition to test
        msg (str): message to be displayed
        title (str, optional): task dialog title
        ok (bool, optional): show OK button, defaults to True
        cancel (bool, optional): show Cancel button, defaults to False
        yes (bool, optional): show Yes button, defaults to False
        no (bool, optional): show NO button, defaults to False
        retry (bool, optional): show Retry button, defaults to False
        exitscript (bool, optional): exit if cancel or no, defaults to False

    Returns:
        bool: True if okay, yes, or retry, otherwise False

    Example:
        >>> from pyrevit import forms
        >>> forms.alert_ifnot(value > 12,
        ...                   'Are you sure?',
        ...                    ok=False, yes=True, no=True, exitscript=True)
    """
    if not condition:
        return alert(msg, *args, **kwargs)


def pick_folder(title=None, owner=None):
    """Show standard windows pick folder dialog.

    Args:
        title (str, optional): title for the window

    Returns:
        str: folder path
    """
    if CPDialogs:
        fb_dlg = CPDialogs.CommonOpenFileDialog()
        fb_dlg.IsFolderPicker = True
        if title:
            fb_dlg.Title = title

        res = CPDialogs.CommonFileDialogResult.Cancel
        if owner:
            res = fb_dlg.ShowDialog(owner)
        else:
            res = fb_dlg.ShowDialog()

        if res == CPDialogs.CommonFileDialogResult.Ok:
            return fb_dlg.FileName
    else:
        fb_dlg = Forms.FolderBrowserDialog()
        if title:
            fb_dlg.Description = title
        if fb_dlg.ShowDialog() == Forms.DialogResult.OK:
            return fb_dlg.SelectedPath


def pick_file(file_ext='*', files_filter='', init_dir='',
              restore_dir=True, multi_file=False, unc_paths=False, title=None):
    r"""Pick file dialog to select a destination file.

    Args:
        file_ext (str): file extension
        files_filter (str): file filter
        init_dir (str): initial directory
        restore_dir (bool): restore last directory
        multi_file (bool): allow select multiple files
        unc_paths (bool): return unc paths
        title (str): text to show in the title bar

    Returns:
        str or list[str]: file path or list of file paths if multi_file=True

    Example:
        >>> from pyrevit import forms
        >>> forms.pick_file(file_ext='csv')
        ... r'C:\output\somefile.csv'

        >>> forms.pick_file(file_ext='csv', multi_file=True)
        ... [r'C:\output\somefile1.csv', r'C:\output\somefile2.csv']

        >>> forms.pick_file(files_filter='All Files (*.*)|*.*|'
                                         'Excel Workbook (*.xlsx)|*.xlsx|'
                                         'Excel 97-2003 Workbook|*.xls',
                            multi_file=True)
        ... [r'C:\output\somefile1.xlsx', r'C:\output\somefile2.xls']
    """
    of_dlg = Forms.OpenFileDialog()
    if files_filter:
        of_dlg.Filter = files_filter
    else:
        of_dlg.Filter = '|*.{}'.format(file_ext)
    of_dlg.RestoreDirectory = restore_dir
    of_dlg.Multiselect = multi_file
    if init_dir:
        of_dlg.InitialDirectory = init_dir
    if title:
        of_dlg.Title = title
    if of_dlg.ShowDialog() == Forms.DialogResult.OK:
        if multi_file:
            if unc_paths:
                return [coreutils.dletter_to_unc(x)
                        for x in of_dlg.FileNames]
            return of_dlg.FileNames
        else:
            if unc_paths:
                return coreutils.dletter_to_unc(of_dlg.FileName)
            return of_dlg.FileName


def save_file(file_ext='', files_filter='', init_dir='', default_name='',
              restore_dir=True, unc_paths=False, title=None):
    r"""Save file dialog to select a destination file for data.

    Args:
        file_ext (str): file extension
        files_filter (str): file filter
        init_dir (str): initial directory
        default_name (str): default file name
        restore_dir (bool): restore last directory
        unc_paths (bool): return unc paths
        title (str): text to show in the title bar

    Returns:
        str: file path

    Example:
        >>> from pyrevit import forms
        >>> forms.save_file(file_ext='csv')
        ... r'C:\output\somefile.csv'
    """
    sf_dlg = Forms.SaveFileDialog()
    if files_filter:
        sf_dlg.Filter = files_filter
    else:
        sf_dlg.Filter = '|*.{}'.format(file_ext)
    sf_dlg.RestoreDirectory = restore_dir
    if init_dir:
        sf_dlg.InitialDirectory = init_dir
    if title:
        sf_dlg.Title = title

    # setting default filename
    sf_dlg.FileName = default_name

    if sf_dlg.ShowDialog() == Forms.DialogResult.OK:
        if unc_paths:
            return coreutils.dletter_to_unc(sf_dlg.FileName)
        return sf_dlg.FileName


def pick_excel_file(save=False, title=None):
    """File pick/save dialog for an excel file.

    Args:
        save (bool): show file save dialog, instead of file pick dialog
        title (str): text to show in the title bar

    Returns:
        str: file path
    """
    if save:
        return save_file(file_ext='xlsx')
    return pick_file(files_filter='Excel Workbook (*.xlsx)|*.xlsx|'
                                  'Excel 97-2003 Workbook|*.xls',
                     title=title)


def save_excel_file(title=None):
    """File save dialog for an excel file.

    Args:
        title (str): text to show in the title bar

    Returns:
        str: file path
    """
    return pick_excel_file(save=True, title=title)


def check_workshared(doc=None, message='Model is not workshared.'):
    """Verify if model is workshared and notify user if not.

    Args:
        doc (DB.Document): target document, current of not provided
        message (str): prompt message if returning False

    Returns:
        bool: True if doc is workshared
    """
    doc = doc or DOCS.doc
    if not doc.IsWorkshared:
        alert(message, warn_icon=True)
        return False
    return True


def check_selection(exitscript=False,
                    message='At least one element must be selected.'):
    """Verify if selection is not empty notify user if it is.

    Args:
        exitscript (bool): exit script if returning False
        message (str): prompt message if returning False

    Returns:
        bool: True if selection has at least one item
    """
    if revit.get_selection().is_empty:
        alert(message, exitscript=exitscript)
        return False
    return True


def check_familydoc(doc=None, family_cat=None, exitscript=False):
    """Verify document is a Family and notify user if not.

    Args:
        doc (DB.Document): target document, current of not provided
        family_cat (str): family category name
        exitscript (bool): exit script if returning False

    Returns:
        bool: True if doc is a Family and of provided category

    Example:
        >>> from pyrevit import forms
        >>> forms.check_familydoc(doc=revit.doc, family_cat='Data Devices')
        ... True
    """
    doc = doc or DOCS.doc
    family_cat = revit.query.get_category(family_cat)
    if doc.IsFamilyDocument and family_cat:
        if doc.OwnerFamily.FamilyCategory.Id == family_cat.Id:
            return True
    elif doc.IsFamilyDocument and not family_cat:
        return True

    family_type_msg = ' of type {}'\
                      .format(family_cat.Name) if family_cat else''
    alert('Active document must be a Family document{}.'
          .format(family_type_msg), exitscript=exitscript)
    return False


def check_modeldoc(doc=None, exitscript=False):
    """Verify document is a not a Model and notify user if not.

    Args:
        doc (DB.Document): target document, current of not provided
        exitscript (bool): exit script if returning False

    Returns:
        bool: True if doc is a Model

    Example:
        >>> from pyrevit import forms
        >>> forms.check_modeldoc(doc=revit.doc)
        ... True
    """
    doc = doc or DOCS.doc
    if not doc.IsFamilyDocument:
        return True

    alert('Active document must be a Revit model (not a Family).',
          exitscript=exitscript)
    return False


def check_modelview(view, exitscript=False):
    """Verify target view is a model view.

    Args:
        view (DB.View): target view
        exitscript (bool): exit script if returning False

    Returns:
        bool: True if view is model view

    Example:
        >>> from pyrevit import forms
        >>> forms.check_modelview(view=revit.active_view)
        ... True
    """
    if not isinstance(view, (DB.View3D, DB.ViewPlan, DB.ViewSection)):
        alert("Active view must be a model view.", exitscript=exitscript)
        return False
    return True


def check_viewtype(view, view_type, exitscript=False):
    """Verify target view is of given type

    Args:
        view (DB.View): target view
        view_type (DB.ViewType): type of view
        exitscript (bool): exit script if returning False

    Returns:
        bool: True if view is of given type

    Example:
        >>> from pyrevit import forms
        >>> forms.check_viewtype(revit.active_view, DB.ViewType.DrawingSheet)
        ... True
    """
    if view.ViewType != view_type:
        alert(
            "Active view must be a {}.".format(
                ' '.join(coreutils.split_words(str(view_type)))),
            exitscript=exitscript
            )
        return False
    return True


def check_graphicalview(view, exitscript=False):
    """Verify target view is a graphical view

    Args:
        view (DB.View): target view
        exitscript (bool): exit script if returning False

    Returns:
        bool: True if view is a graphical view

    Example:
        >>> from pyrevit import forms
        >>> forms.check_graphicalview(revit.active_view)
        ... True
    """
    if not view.Category:
        alert(
            "Active view must be a grahical view.",
            exitscript=exitscript
            )
        return False
    return True


def toast(message, title='pyRevit', appid='pyRevit',
          icon=None, click=None, actions=None):
    """Show a Windows 10 notification.

    Args:
        message (str): notification message
        title (str): notification title
        appid (str): app name (will show under message)
        icon (str): file path to icon .ico file (defaults to pyRevit icon)
        click (str): click action commands string
        actions (dict): dictionary of button names and action strings

    Example:
        >>> script.toast("Hello World!",
        ...              title="My Script",
        ...              appid="MyAPP",
        ...              click="https://eirannejad.github.io/pyRevit/",
        ...              actions={
        ...                  "Open Google":"https://google.com",
        ...                  "Open Toast64":"https://github.com/go-toast/toast"
        ...                  })
    """
    toaster.send_toast(
        message,
        title=title,
        appid=appid,
        icon=icon,
        click=click,
        actions=actions)


def ask_for_string(default=None, prompt=None, title=None, **kwargs):
    """Ask user to select a string value.

    This is a shortcut function that configures :obj:`GetValueWindow` for
    string data types. kwargs can be used to pass on other arguments.

    Args:
        default (str): default unique string. must not be in reserved_values
        prompt (str): prompt message
        title (str): title message
        kwargs (type): other arguments to be passed to :obj:`GetValueWindow`

    Returns:
        str: selected string value

    Example:
        >>> forms.ask_for_string(
        ...     default='some-tag',
        ...     prompt='Enter new tag name:',
        ...     title='Tag Manager')
        ... 'new-tag'
    """
    return GetValueWindow.show(
        None,
        value_type='string',
        default=default,
        prompt=prompt,
        title=title,
        **kwargs
        )


def ask_for_unique_string(reserved_values,
                          default=None, prompt=None, title=None, **kwargs):
    """Ask user to select a unique string value.

    This is a shortcut function that configures :obj:`GetValueWindow` for
    unique string data types. kwargs can be used to pass on other arguments.

    Args:
        reserved_values (list[str]): list of reserved (forbidden) values
        default (str): default unique string. must not be in reserved_values
        prompt (str): prompt message
        title (str): title message
        kwargs (type): other arguments to be passed to :obj:`GetValueWindow`

    Returns:
        str: selected unique string

    Example:
        >>> forms.ask_for_unique_string(
        ...     prompt='Enter a Unique Name',
        ...     title=self.Title,
        ...     reserved_values=['Ehsan', 'Gui', 'Guido'],
        ...     owner=self)
        ... 'unique string'

        In example above, owner argument is provided to be passed to underlying
        :obj:`GetValueWindow`.

    """
    return GetValueWindow.show(
        None,
        value_type='string',
        default=default,
        prompt=prompt,
        title=title,
        reserved_values=reserved_values,
        **kwargs
        )


def ask_for_one_item(items, default=None, prompt=None, title=None, **kwargs):
    """Ask user to select an item from a list of items.

    This is a shortcut function that configures :obj:`GetValueWindow` for
    'single-select' data types. kwargs can be used to pass on other arguments.

    Args:
        items (list[str]): list of items to choose from
        default (str): default selected item
        prompt (str): prompt message
        title (str): title message
        kwargs (type): other arguments to be passed to :obj:`GetValueWindow`

    Returns:
        str: selected item

    Example:
        >>> forms.ask_for_one_item(
        ...     ['test item 1', 'test item 2', 'test item 3'],
        ...     default='test item 2',
        ...     prompt='test prompt',
        ...     title='test title'
        ... )
        ... 'test item 1'
    """
    return GetValueWindow.show(
        items,
        value_type='dropdown',
        default=default,
        prompt=prompt,
        title=title,
        **kwargs
        )


def ask_for_date(default=None, prompt=None, title=None, **kwargs):
    """Ask user to select a date value.

    This is a shortcut function that configures :obj:`GetValueWindow` for
    date data types. kwargs can be used to pass on other arguments.

    Args:
        default (datetime.datetime): default selected date value
        prompt (str): prompt message
        title (str): title message
        kwargs (type): other arguments to be passed to :obj:`GetValueWindow`

    Returns:
        datetime.datetime: selected date

    Example:
        >>> forms.ask_for_date(default="", title="Enter deadline:")
        ... datetime.datetime(2019, 5, 17, 0, 0)
    """
    # FIXME: window does not set default value
    return GetValueWindow.show(
        None,
        value_type='date',
        default=default,
        prompt=prompt,
        title=title,
        **kwargs
        )


def ask_for_number_slider(default=None, prompt=None, title=None, **kwargs):
    """Ask user to select a number value.

    This is a shortcut function that configures :obj:`GetValueWindow` for
    numbers. kwargs can be used to pass on other arguments.

    Args:
        default (str): default unique string. must not be in reserved_values
        prompt (str): prompt message
        title (str): title message
        kwargs (type): other arguments to be passed to :obj:`GetValueWindow`

    Returns:
        str: selected string value

    Example:
        >>> forms.ask_for_string(
        ...     default=50,
        ...     min = 0
        ...     max = 100
        ...     prompt='Select a number:',
        ...     title='test title')
        ... '50'
    """
    return GetValueWindow.show(
        None,
        value_type='slider',
        default=default,
        prompt=prompt,
        title=title,
        **kwargs
        )


def ask_to_use_selected(type_name, count=None, multiple=True):
    """Ask user if wants to use currently selected elements.

    Args:
        type_name (str): Element type of expected selected elements
        count (int): Number of selected items
        multiple (bool): Whether multiple selected items are allowed
    """
    report = type_name.lower()
    # multiple = True
    message = \
        "You currently have %s selected. Do you want to proceed with "\
        "currently selected item(s)?"
    # check is selecting multiple is allowd
    if not multiple:
        # multiple = False
        message = \
            "You currently have %s selected and only one is required. "\
            "Do you want to use the first selected item?"

    # check if count is provided
    if count is not None:
        report = '{} {}'.format(count, report)
    return alert(message % report, yes=True, no=True)


def ask_for_color(default=None):
    """Show system color picker and ask for color

    Args:
        default (str): default color in HEX ARGB e.g. #ff808080
        val (type): desc

    Returns:
        str: selected color in HEX ARGB e.g. #ff808080, or None if cancelled

    Example:
        >>> forms.ask_for_color()
        ... '#ff808080'
    """
    # colorDlg.Color
    color_picker = Forms.ColorDialog()
    if default:
        default = default.replace('#', '')
        color_picker.Color = System.Drawing.Color.FromArgb(
            int(default[:2], 16),
            int(default[2:4], 16),
            int(default[4:6], 16),
            int(default[6:8], 16)
        )
    color_picker.FullOpen = True
    if color_picker.ShowDialog() == Forms.DialogResult.OK:
        c = color_picker.Color
        c_hex = ''.join('{:02X}'.format(int(x)) for x in [c.A, c.R, c.G, c.B])
        return '#' + c_hex


def inform_wip():
    """Show work-in-progress prompt to user and exit script.

    Example:
        >>> forms.inform_wip()
    """
    alert("Work in progress.", exitscript=True)
