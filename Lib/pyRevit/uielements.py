"""
Revit UI Element wrappers

"""

import clr
from collections import OrderedDict

clr.AddReference('System')
clr.AddReference('PresentationCore')
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

clr.AddReference('AdWindows')
from Autodesk.Windows import ComponentManager

from Autodesk.Revit.UI import PushButtonData, PulldownButtonData
from Autodesk.Revit.Exceptions import ApplicationException, ArgumentException

from loader.logger import logger
from loader.exceptions import PyRevitException
from loader.config import SCRIPTS_DIR, SCRIPTS_DLL_BASENAME


class Ribbon(object):
    """
    Ribbon Wrapper.
    Usage:
    ribbon = Ribbon()

    Atributes:
    :ribbon.tabs dict: {'tabname2': Tab(), 'tabname2': Tab(), ... }
    :ribbon.revit_panel = UIFramework.RevitRibbonControl [AdWindows.dll]

    Methods:
    :ribbon.create():

    Attributes:
    :ribbon.commands: List of all nested commands in ribbon.
    :ribbon.dll_path: File path fo assembly puttons will reference
    :is_reloading: flag: ribbon is reloading (triggers purge and enable)

    Internal Methods:
    :ribbon._purge_tabs():
    :ribbon._enable_all_tabs():

    """

    def __init__(self):
        self.tabs = OrderedDict()
        self.revit_ribbon = None
        logger.debug('Session instantiated.')

    def create(self, dll_path, is_reloading=False):
        """ Creates UI Objects.
        :param dll_path: Full path to scrips DLL
        """
        self.revit_ribbon = ComponentManager.Ribbon
        self.dll_path = dll_path
        self.is_reloading = is_reloading

        logger.info('Creating UI...')
        for tab in self.tabs.values():
            tab.create()

        if self.is_reloading:
            logger.info('Cleaning Up Ribbon...')
            self._purge_tabs()
            self._enable_all_tabs()

    def _enable_all_tabs(self):
        "Enables all tabs in Ribbon().tabs"
        logger.debug('Enabling all tabs')
        for tab in self.tabs.values():
            tab.enable()
            logger.debug('Tab Enabled: {}'.format(tab.name))

    def _purge_tabs(self):
        """Disable all tabs that are not in session.
        Description field is used to store a variable, allowing
        loader to identify if tab was created by script"""
        logger.debug('Purging unused tabs')
        for revit_tab in self.revit_ribbon.Tabs:
            if revit_tab.Description == SCRIPTS_DLL_BASENAME and \
               revit_tab.Title not in self.tabs.keys():
                    Tab.disable_unreferenced_tab(revit_tab)

    @property
    def commands(self):
        """ List of Commands added to session.
        This gathers all commands within all
        Tabs, Panels, and Ribbon Items.
        This is to create all the classes in the dll assembly
        :returns: list of Commands objects. Used to create DLL from commands.
        """
        commands = []
        logger.debug('Gathering all Session commands...')
        for tab in self.tabs.values():
            for panel in tab.panels.values():
                logger.debug('Getting Commands from Panel: {}'.format(panel))
                commands.extend(panel.commands)
        return commands

    def __repr__(self):
        return '<RIBBON: tabs:{}>'.format(self.tabs.keys())


class Tab(object):
    """Revit UI Tab Object."""

    identifier = '.tab'

    def __init__(self, ribbon=None, tab_name=None):
        """
        Usage:
        tab = Tab(ribbon, tab_name)
        :ribbon Ribbon(): Ribbon object Tab belongs to.
        :tab_name string: name of the tab. Revit uses "Title"

        Atributes:
        tab.panels = {'Panel1': Panel(), 'Panel2': Panel(), ... }
        tab.revit_tab = UIFramework.RvtRibbonTab [AdWindows.dll]

        Methods:
        tab.create(): Creates tab in parent Ribbon
        tab.enable(): sets Visible and Enable to True
        tab.disable(): sets Visible and Enable to True

        """
        if not isinstance(ribbon, Ribbon) and not isinstance(tab_name, str):
            raise PyRevitException("Wrong arg types to Tab(): {},{}".format(
                                   type(ribbon), type(tab_name)))
        self.ribbon = ribbon
        self.name = tab_name

        self.panels = OrderedDict()
        self.revit_tab = None

        logger.debug('Tab instantiated: {}'.format(self.name))

    def create(self):
        try:
            __revit__.CreateRibbonTab(self.name)
        except ArgumentException:
            logger.debug('Tab already exists: {}'.format(self.name))
        self._set_revit_tab()

        for panel in self.panels.values():
            panel.create()

        if self.ribbon.is_reloading:
            self._purge_panels()
            self._enable_all_panels()

    def _set_revit_tab(self):
        "CreateRibbonTab does not return intance, so must be found manually."
        for revit_tab in self.ribbon.revit_ribbon.Tabs:
            if revit_tab.Title == self.name:
                self.revit_tab = revit_tab
                revit_tab.Description = SCRIPTS_DLL_BASENAME
                break
        else:
            logger.warning('Failed to get Revit Tab Object: {}'.format(self.name))

    def _enable_all_panels(self):
        logger.debug('Enabling all Panels')
        for panel in self.panels.values():
            if panel.ribbon_buttons:
                panel.enable()
                logger.debug('Panel Re-Enabled: {}'.format(panel.name))

    def _purge_panels(self):
        "Hides empty panels"
        revit_panels = __revit__.GetRibbonPanels(self.name)
        for revit_panel in revit_panels:
            buttons_in_panel = revit_panel.GetItems()
            if revit_panel.Name not in self.panels.keys():
                Panel.disable_unreferenced_panel(revit_panel)
                logger.info('Panel Disabled: [{}] (No Folder)'.format(self.name))
                continue
            elif not any([True if Button.Visible else False for Button in buttons_in_panel]):
                Panel.disable_unreferenced_panel(revit_panel)
                logger.info('Panel Disabled: [{}] (No Buttons)'.format(self.name))

    def enable(self):
        self.revit_tab.IsVisible = True
        self.revit_tab.IsEnabled = True

    def disable(self):
        self.revit_tab.IsVisible = False
        self.revit_tab.IsEnabled = False

    @staticmethod
    def disable_unreferenced_tab(revit_tab):
        "This Method used to apply disabled settings directly to revit Objects"
        revit_tab.IsVisible = False
        revit_tab.IsEnabled = False

    def __repr__(self):
        return '<TAB: {}>'.format(self.name)


class Panel(object):
    """
    Panel Wrapper
    Usage:
    panel = Panel(tab, panel_name)
    :tab Tab(): Tab object panel belongs to.
    :panel_name string: name of the panel. Same as visible to user

    Atributes:
    :panel.name string: name of panel
    :panel.revit_panel = Autodesk.Revit.UI.RibbonPanel Object

    Methods:
    """

    identifier = '.panel'

    def __init__(self, tab=None, panel_name=None):
        """
        :param tab: Tab panel will belong to.
        :type tab: Tab()
        :param panel_name: Name of the panel.
        :type tab: string
        """
        if not isinstance(tab, Tab) and not isinstance(panel_name, str):
            raise PyRevitException("Malformed Panel(): {},{}".format(
                                   type(tab), type(panel_name)))

        self.tab = tab
        self.name = panel_name

        self.ribbon_buttons = []
        self.revit_panel = None
        logger.debug('Panel instantiated: {}:{}'.format(tab.name, panel_name))

    def create(self):
        "Creates panel"
        try:
            #  Returns Revit Instance
            self.revit_panel = __revit__.CreateRibbonPanel(self.tab.name,
                                                           self.name)
        except ArgumentException:
            logger.debug('Panel already exists: {}'.format(self.name))
            #  Because creation failed, manually acquire revit instance
            self._set_revit_panel()

        for ribbon_button in self.ribbon_buttons:
            self._add_button(ribbon_button)

        if self.tab.ribbon.is_reloading:
            self._purge_buttons()

    def _add_button(self, ribbon_button):
        """ Adds button to panel.
        :param ribbon_button: Data required to create RibbonButton
        :param type: PushButtonData, or equivalent
        Tries creating first, if it fails, will try to retrieve existing panel.
        """

        # PUSH BUTTON AND PULL DOWN AT ROOT RIBBON LEVEL #
        dll_path = self.tab.ribbon.dll_path
        try:
            ribbon_button.revit_button = self.revit_panel.AddItem(ribbon_button.data(dll_path))
        except ArgumentException as errmsg:
            if 'already exists' in errmsg.Message:
                logger.debug('Button already exists: {}'.format(ribbon_button.name))
                ribbon_button.set_revit_button()
                self._ensure_enabled(ribbon_button)
            else:
                raise Exception(errmsg.Message)
        ribbon_button.set_icon()

        # IF PULL DOWN BUTTON, ITERATE THROUGH CHILD PUSH BUTTONS #
        if isinstance(ribbon_button, PullDown):
            pulldown_button = ribbon_button
            for push_button in pulldown_button.push_buttons:
                try:
                    push_button.revit_button = ribbon_button.revit_button.AddPushButton(push_button.data(dll_path))
                except ArgumentException as errmsg:
                    if 'already exists' in errmsg.Message:
                        logger.debug('Pulldown Push already exists: {}'.format(ribbon_button.name))
                        push_button.set_revit_button()
                    else:
                        raise Exception(errmsg.Message)
                push_button.set_icon()

    def _purge_buttons(self):
        """ Hides a Button that is no longed in Ribbon """
        logger.debug('Purging Unused Buttons from panel: {}'.format(self.name))
        ribbon_buttons = self.ribbon_buttons
        for revit_button in self.revit_panel.GetItems():
            if revit_button.Name not in [button.name for button in ribbon_buttons]:
                RibbonButton.disable_unreferenced_panel(revit_button)
                logger.info('[{}] revit_button removed.'.format(revit_button.Name))

            # Since it's iterating over revit object, this is a hacky method
            # to check if it's a pulldown.
            if hasattr(revit_button, 'AddPushButton'):
                for revit_pushbutton in revit_button.GetItems():
                    if revit_pushbutton.ClassName not in [cmd.class_name for cmd in self.commands]:
                        RibbonButton.disable_unreferenced_panel(revit_pushbutton)
                        logger.info('[{}] pullpush removed.'.format(revit_pushbutton.Name))


    def _ensure_enabled(self, button):
        """ If button exists, and it's being added, ensure it's enabled """
        button.enable()
        if isinstance(button, PullDown):
            for pushbutton in button.push_buttons:
                pushbutton.set_revit_button()
                self._ensure_enabled(pushbutton)
        else:
            try:
                button.revit_button.AssemblyName = self.tab.ribbon.dll_path
                button.revit_button.ClassName = button.class_name
            except Exception as errmsg:
                logger.warning('Could not Reload: {}'.format(button.name))
            logger.debug('Reactivated Button: {}'.format(button.name))

    def _set_revit_panel(self):
        """"Used to retrieve the panel object if it's already been created.
        :returns: the actual RibbonPanel object from Revit.
        """
        if self.revit_panel:
            return
        else:
            revit_panels = __revit__.GetRibbonPanels(self.tab.name)
        for revit_panel in revit_panels:
            if self.name == revit_panel.Name:
                self.revit_panel = revit_panel
                break
        else:
            logger.warning('Could not get panel: {}'.format(self.name))

    def enable(self):
        self.revit_panel.Visible = True
        self.revit_panel.Enabled = True

    def disable(self):
        self.revit_panel.Visible = False
        self.revit_panel.Enabled = False

    @staticmethod
    def disable_unreferenced_panel(revit_panel):
        revit_panel.Visible = False
        revit_panel.Enabled = False

    @property
    def commands(self):
        """:returns: All commands in ribbon items"""
        commands = []
        for ribbon_button in self.ribbon_buttons:
            if isinstance(ribbon_button, PushButton):
                commands.append(ribbon_button.command)
            if isinstance(ribbon_button, PullDown):
                commands.extend(ribbon_button.commands)
        return commands

    def __repr__(self):
        return '<PANEL: {}>'.format(self.name)


class RibbonButton(object):
    """Icon
    May need to separate icon logic and PushButton Data to enable pickling.
    """

    def register_icon(self, filepath):
        "Inherited from pyrevit loader. Not sure if all are needed"
        uri = Uri(filepath)
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

    def set_icon(self):
        self.register_icon(self.png_path)
        self.revit_button.Image = self.smallBitmap
        self.revit_button.LargeImage = self.largeBitmap

    def enable(self):
        self.revit_button.Visible = True
        self.revit_button.Enabled = True

    def disable(self):
        self.revit_button.Visible = False
        self.revit_button.Enabled = False

    @staticmethod
    def disable_unreferenced_panel(revit_button):
        revit_button.Visible = False
        revit_button.Enabled = False

    def set_revit_button(self):
        """ Helper Function to set revit_ attribute of RibbonButoon or derived
        to actual revit object. This is only used when updating.
        If it's the first time loading, button is returned byt AddButton
        """
        # It's already Set, early return
        if self.revit_button:
            return self.revit_button

        # It's a pull down, or a push button at root level of ribbon
        if not getattr(self, 'pulldown_parent', None):
            logger.debug('Setting revit_button for root: {}'.format(self.name))
            for revit_button in self.panel.revit_panel.GetItems():
                if revit_button.Name == self.name:
                    self.revit_button = revit_button
                    break
            else:
                logger.warning(revit_button)
                logger.warning(self)
                raise PyRevitException('Could Not Set Revit Button')

        # It's a pushbutton inside a pulldown
        else:
            logger.debug('Setting revit_button for pullpush: {}'.format(self.name))
            for revit_button in self.pulldown_parent.revit_button.GetItems():
                if revit_button.Name == self.name:
                    self.revit_button = revit_button
                    break
            else:
                logger.warning(revit_button)
                logger.warning('@' + str(revit_button.Name))
                logger.warning(self.name)
                raise PyRevitException('Could Not Set PushPull  Button')


class PushButton(RibbonButton):
    """PushButton Wrapper.
    Usage:
    pushbutton = PushButton(panel=Panel(), command=Command(),
                            png_path=png_path,
                            [pulldown_parent=PullDown()]
                            )
    """
    identifier = 'pushbutton'

    def __init__(self, panel=None, command=None,
                 png_path=None, pulldown_parent=None):
        if not all([panel, command, png_path]):
            raise PyRevitException('Malformed PushButton')
        self.panel = panel
        self.command = command
        self.class_name = command.class_name
        self.png_path = png_path
        self.name = command.name
        self.pulldown_parent = pulldown_parent
        # self.register_icon(png_path)

        self.revit_button = None
        logger.debug('PushButton instantiated: {}'.format(self.name))

    def data(self, dll_path):
        """ API Constructor:
        public PushButtonData(string name ,string text, string assemblyName,
                              string className)"""
        return PushButtonData(self.name, self.name, dll_path,
                              self.class_name)

    def is_in_pulldown(self):
        return bool(self.pulldown_parent)

    def __repr__(self):
        if not self.is_in_pulldown:
            return '<PUSHBUTTON_CHILD: {}-{}>'.format(self.pulldown_parent,
                                                      self.name)
        else:
            return '<PUSHBUTTON: {}>'.format(self.name)


class PullDown(RibbonButton):
    """PushButton Wrapper.
    """
    identifier = 'pulldownbutton'

    def __init__(self, panel=None, cmd_name=None, png_path=None):
        self.panel = panel
        self.png_path = png_path
        # self.register_icon(png_path)
        self.name = cmd_name
        self.push_buttons = []  # Called Manually

        self.revit_button = None
        logger.debug('PullDown instantiated: {}'.format(self.name))

    def data(self, dll_path):
        return PulldownButtonData(self.name, self.name)

    @property
    def commands(self):
        "Returns all commands embeded within pull down"
        commands = []
        for pushbutton in self.push_buttons:
            commands.append(pushbutton.command)
        return commands

    def __repr__(self):
        return '<PULLDOWN: {}>'.format(self.name)


class Command(object):
    """Revit Command Object. Could be any RibbonButton Type
    :param name: Internal Revit name
    :type name: string
    :param text: User Visible Component name
    :type text: string
    :param filepath: file path to python script the command will call
    :type filepath: string
    """

    def __init__(self, panel=None, cmd_name=None, py_filepath=None):
        self.name = cmd_name
        self.py_filepath = py_filepath
        self.panel = panel
        self.class_name = '{}{}{}'.format(panel.tab.name, panel.name, self.name)
        logger.debug('Command instantiated: {}'.format(self.name))

    def __repr__(self):
        return '<CMD: {}>'.format(self.class_name)
