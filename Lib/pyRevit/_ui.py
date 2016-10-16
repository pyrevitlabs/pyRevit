from .logger import logger
from .exceptions import RevitRibbonItemExists, RevitRibbonPanelExists, RevitRibbonTabExists

# dotnet imports
import clr
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')
from System import *
from System.IO import *
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

# revit api imports
from Autodesk.Revit.UI import *
from Autodesk.Revit.Attributes import *


class _ExistingPyRevitRibbonElement(object):
    def __init__(self):
        self.name = None
        self.children = []


class _ExistingPyRevitPanel(_ExistingPyRevitRibbonElement):
    def retrieve_ribbon_item(self, item):
        pass


class _ExistingPyRevitTab(_ExistingPyRevitRibbonElement):
    def retrieve_ribbon_panel(self, panel):
        pass


class ExistingPyRevitUI(_ExistingPyRevitRibbonElement):
    def retrieve_ribbon_tab(self, tab):
        pass


def _create_button(button, panel_item, pkg_asm_location):
    pass


def _create_ribbon_item(item, ribbon_panel, pkg_asm_location):
    pass


def _create_ribbon_panel(panel, ribbon_tab):
    pass


def _create_ribbon_tab(pkg_tab):
    """Create revit ribbon tab from pkg_tab data"""
    try:
        return __revit__.CreateRibbonTab(pkg_tab.name)
    except:
        raise RevitRibbonTabExists()


def update_revit_ui(parsed_pkg, pkg_asm_location):
    # Collect exising ui elements and update/create
    current_ui = ExistingPyRevitUI()
    for tab in parsed_pkg:
        # creates pyrevit ribbon-panels for given tab data
        # A package might contain many tabs. Some tabs might not temporarily include any commands
        # So a ui tab is create only if it includes commands
        #  Level 1: Tabs -----------------------------------------------------------------------------------------------
        if tab.has_commands():
            if current_ui.contains(tab):
                ribbon_tab = current_ui.retrieve_ribbon_tab(tab)
            else:
                ribbon_tab = _create_ribbon_tab(tab)

            # Level 2: Panels (under tabs) -----------------------------------------------------------------------------
            for panel in tab:
                if current_ui.tab(tab).contains(panel):
                    ribbon_panel = current_ui.tab(tab).retrieve_ribbon_panel(panel)
                else:
                    ribbon_panel = _create_ribbon_panel(panel, ribbon_tab)

                # Level 3: Ribbon items (simple push buttons or more complex button groups) ----------------------------
                for ribbon_item in panel:
                    if current_ui.panel(panel).contains(ribbon_item):
                        # update the ribbon button itself first (mostly to update icon)
                        current_ui.panel(panel).update_ribbon_item(ribbon_item)

                        # then update/create the sub items if any
                        # Level 4: Ribbon items that include other push buttons (e.g. PullDownButton) ------------------
                        if ribbon_item.is_group():
                            for button in ribbon_item:
                                if current_ui.ribbon_item(ribbon_item).contains(button):
                                    current_ui.ribbon_item(ribbon_item).update_button(button)
                                else:
                                    _create_button(button, ribbon_item, pkg_asm_location)
                    else:
                        _create_ribbon_item(ribbon_item, ribbon_panel, pkg_asm_location)
        else:
            logger.debug('Tab {} does not have any commands. Skipping.'.format(tab.name))

    # any existing ui elements that hasn't been updated, doesn't exist in the package anymore and
    # should be removed from revit ui.
    current_ui.cleanup_obsolete_items()

