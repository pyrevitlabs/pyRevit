from .uielements import *

# dot net imports
import clr
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')
from System import *
from System.IO import *
from System.Reflection import *
from System.Reflection.Emit import *
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
from System.Diagnostics import Process

# revit api imports
from Autodesk.Revit.UI import *
from Autodesk.Revit.Attributes import *


class PyRevitUI:
    def __init__(self, cmd_tree, dll_location, assembly_name):
        # setting up UI
        logger.debug('Creating pyRevit UI.')
        self.cmd_tree = cmd_tree
        self.dll_location = dll_location
        self.assembly_name = assembly_name

    def _create_or_find_pyrevit_panels(self):
        logger.debug('Searching for existing pyRevit panels...')
        for scriptTab in self.cmd_tree.pyRevitScriptTabs:
            # creates pyrevitribbonpanels for existing or newly created panels
            pyrevitribbonpanels = dict()
            if scriptTab.hascommands():
                try:
                    #try creating the ribbon tab
                    logger.debug('Creating {0} ribbon tab...'.format(scriptTab.tabName))
                    __revit__.CreateRibbonTab(scriptTab.tabName)
                except:
                    #if fails, the tab already exits so let's gather panel info
                    logger.debug('{0} ribbon tab already created...'.format(scriptTab.tabName))
                    pyrevitribbonpanels = {p.Name: p for p in __revit__.GetRibbonPanels(scriptTab.tabName)}

                #by this point the ribbon tab has either been created or found if existing.
                logger.debug('Searching for panels...')
                for panel in scriptTab.get_sorted_scriptpanels():
                    if panel.panelName in pyrevitribbonpanels.keys():
                        logger.debug('Existing panel found: {0}'.format(panel.panelName))
                        scriptTab.pyRevitUIPanels[panel.panelName] = pyrevitribbonpanels[panel.panelName]
                        scriptTab.pyRevitUIButtons[panel.panelName] = list(pyrevitribbonpanels[panel.panelName].GetItems())
                    else:
                        logger.debug('Creating panel: {0}'.format(panel.panelName))
                        newpanel = __revit__.CreateRibbonPanel(scriptTab.tabName, panel.panelName)
                        scriptTab.pyRevitUIPanels[panel.panelName] = newpanel
                        scriptTab.pyRevitUIButtons[panel.panelName] = []
            else:
                logger.debug('{0} ribbon tab found but does not include any scripts. ' \
                        'Skipping this tab.'.format(scriptTab.tabName))

    def _create_ui(self):
        newbuttoncount = updatedbuttoncount = 0
        for scriptTab in self.cmd_tree.pyRevitScriptTabs:
            for scriptPanel in scriptTab.get_sorted_scriptpanels():
                pyrevitribbonpanel = scriptTab.pyRevitUIPanels[scriptPanel.panelName]
                pyrevitribbonitemsdict = {b.Name: b for b in scriptTab.pyRevitUIButtons[scriptPanel.panelName]}
                logger.debug('Creating\\Updating ribbon items for panel: {0}'.format(scriptPanel.panelName))
                for scriptGroup in scriptPanel.get_sorted_scriptgroups():
                    # PulldownButton or SplitButton
                    groupispulldownbutton = (scriptGroup.groupType == cfg.PULLDOWN_BUTTON_TYPE_NAME)
                    groupissplitbutton = (scriptGroup.groupType == cfg.STACKTWO_BUTTON_TYPE_NAME or \
                                          scriptGroup.groupType == cfg.SPLITPUSH_BUTTON_TYPE_NAME )
                    if groupispulldownbutton or groupissplitbutton:
                        # PulldownButton
                        if scriptGroup.groupType == cfg.PULLDOWN_BUTTON_TYPE_NAME:
                            if scriptGroup.groupName not in pyrevitribbonitemsdict:
                                logger.debug('Creating pulldown button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    PulldownButtonData(scriptGroup.groupName, scriptGroup.groupName))
                            else:
                                logger.debug('Updating pulldown button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)

                        # SplitButton
                        elif scriptGroup.groupType == cfg.STACKTWO_BUTTON_TYPE_NAME:
                            if scriptGroup.groupName not in pyrevitribbonitemsdict.keys():
                                logger.debug('Creating split button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    SplitButtonData(scriptGroup.groupName, scriptGroup.groupName))
                            else:
                                logger.debug('Updating split button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)

                        # SplitPushButton
                        elif scriptGroup.groupType == cfg.SPLITPUSH_BUTTON_TYPE_NAME:
                            if scriptGroup.groupName not in pyrevitribbonitemsdict.keys():
                                logger.debug('Creating split button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    SplitButtonData(scriptGroup.groupName, scriptGroup.groupName))
                            else:
                                logger.debug('Updating split button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)
                            ribbonitem.IsSynchronizedWithCurrentItem = False

                        ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                        ribbonitem.LargeImage = scriptGroup.buttonIcons.largeBitmap
                        existingribbonitempushbuttonsdict = {b.ClassName: b for b in ribbonitem.GetItems()}

                        for cmd in scriptGroup.scriptCommands:
                            if cmd.className not in existingribbonitempushbuttonsdict:
                                logger.debug('Creating push button: {0}'.format(cmd.className))
                                buttondata = PushButtonData(cmd.className, cmd.cmdName, self.dll_location,
                                                            cmd.className)
                                buttondata.ToolTip = cmd.tooltip
                                ldesc = 'Class Name:\n{0}\n\nAssembly Name:\n{1}'.format(cmd.className,
                                                                                         self.assembly_name)
                                buttondata.LongDescription = ldesc
                                if cmd.buttonIcons:
                                    if groupissplitbutton:
                                        buttondata.LargeImage = cmd.buttonIcons.largeBitmap
                                    else:
                                        buttondata.LargeImage = cmd.buttonIcons.mediumBitmap
                                else:
                                    if groupissplitbutton:
                                        buttondata.LargeImage = scriptGroup.buttonIcons.largeBitmap
                                    else:
                                        buttondata.LargeImage = scriptGroup.buttonIcons.mediumBitmap
                                ribbonitem.AddPushButton(buttondata)
                                newbuttoncount += 1
                            else:
                                logger.debug('Updating push button: {0}'.format(cmd.className))
                                pushbutton = existingribbonitempushbuttonsdict.pop(cmd.className)
                                pushbutton.ToolTip = cmd.tooltip
                                ldesc = 'Class Name:\n{0}\n\nAssembly Name:\n{1}'.format(cmd.className,
                                                                                         self.assembly_name)
                                pushbutton.LongDescription = ldesc
                                pushbutton.Enabled = True
                                if cfg.RELOAD_SCRIPTS_OVERRIDE_SCRIPT_NAME not in pushbutton.Name:
                                    pushbutton.AssemblyName = self.dll_location
                                if cmd.buttonIcons:
                                    if groupissplitbutton:
                                        pushbutton.LargeImage = cmd.buttonIcons.largeBitmap
                                    else:
                                        pushbutton.LargeImage = cmd.buttonIcons.mediumBitmap
                                else:
                                    if groupissplitbutton:
                                        pushbutton.LargeImage = scriptGroup.buttonIcons.largeBitmap
                                    else:
                                        pushbutton.LargeImage = scriptGroup.buttonIcons.mediumBitmap
                                updatedbuttoncount += 1
                        for orphanedButtonName, orphanedButton in existingribbonitempushbuttonsdict.items():
                            logger.debug('Disabling orphaned button: {0}'.format(orphanedButtonName))
                            orphanedButton.Enabled = False

                    # StackedButtons
                    elif scriptGroup.groupType == cfg.STACKTHREE_BUTTON_TYPE_NAME:
                        logger.debug('Creating\\Updating 3 stacked buttons: {0}'.format(scriptGroup.groupType))
                        stackcommands = []
                        for cmd in scriptGroup.scriptCommands:
                            if cmd.className not in pyrevitribbonitemsdict:
                                logger.debug('Creating stacked button: {0}'.format(cmd.className))
                                buttondata = PushButtonData(cmd.className, cmd.cmdName, self.dll_location,
                                                            cmd.className)
                                buttondata.ToolTip = cmd.tooltip
                                ldesc = 'Class Name:\n{0}\n\nAssembly Name:\n{1}'.format(cmd.className,
                                                                                         self.assembly_name)
                                buttondata.LongDescription = ldesc
                                if cmd.buttonIcons:
                                    buttondata.Image = cmd.buttonIcons.smallBitmap
                                else:
                                    buttondata.Image = scriptGroup.buttonIcons.smallBitmap
                                stackcommands.append(buttondata)
                                newbuttoncount += 1
                            else:
                                logger.debug('Updating stacked button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonitemsdict.pop(cmd.className)
                                ribbonitem.AssemblyName = self.dll_location
                                ribbonitem.ClassName = cmd.className
                                ribbonitem.Enabled = True
                                updatedbuttoncount += 1
                                if cmd.buttonIcons:
                                    ribbonitem.Image = cmd.buttonIcons.smallBitmap
                                else:
                                    ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                        if len(stackcommands) == 3:
                            pyrevitribbonpanel.AddStackedItems(*stackcommands)

                    # PushButton
                    elif scriptGroup.groupType == cfg.PUSH_BUTTON_TYPE_NAME and not scriptGroup.islinkbutton():
                        try:
                            cmd = scriptGroup.scriptCommands.pop()
                            if cmd.className not in pyrevitribbonitemsdict:
                                logger.debug('Creating push button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    PushButtonData(cmd.className, scriptGroup.groupName, self.dll_location,
                                                   cmd.className))
                                newbuttoncount += 1
                            else:
                                logger.debug('Updating push button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonitemsdict.pop(cmd.className)
                                ribbonitem.AssemblyName = self.dll_location
                                ribbonitem.ClassName = cmd.className
                                ribbonitem.Enabled = True
                                updatedbuttoncount += 1
                            ribbonitem.ToolTip = cmd.tooltip
                            ldesc = 'Class Name:\n{0}\n\nAssembly Name:\n{1}'.format(cmd.className,
                                                                                     self.assembly_name)
                            ribbonitem.LongDescription = ldesc
                            ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                            ribbonitem.LargeImage = scriptGroup.buttonIcons.largeBitmap
                        except:
                            logger.debug('Pushbutton has no associated scripts. Skipping {0}'.format(scriptGroup.sourceFile))
                            continue

                    # SmartButton
                    elif scriptGroup.groupType == cfg.SMART_BUTTON_TYPE_NAME \
                    and not scriptGroup.islinkbutton():
                        try:
                            cmd = scriptGroup.scriptCommands.pop()
                            if cmd.className not in pyrevitribbonitemsdict:
                                logger.debug('Creating smart button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    PushButtonData(cmd.className, scriptGroup.groupName, self.dll_location,
                                                   cmd.className))
                                logger.debug('Smart button created.')
                                newbuttoncount += 1
                            else:
                                logger.debug('Updating push button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonitemsdict.pop(cmd.className)
                                ribbonitem.AssemblyName = self.dll_location
                                ribbonitem.ClassName = cmd.className
                                ribbonitem.Enabled = True
                                updatedbuttoncount += 1
                            ribbonitem.ToolTip = cmd.tooltip
                            ldesc = 'Class Name:\n{0}\n\nAssembly Name:\n{1}'.format(cmd.className,
                                                                                     self.assembly_name)
                            ribbonitem.LongDescription = ldesc
                            importedscript = __import__(cmd.getscriptbasename())
                            importedscript.selfInit(__revit__, cmd.getfullscriptaddress(), ribbonitem)
                            logger.debug('Smart button initialized.')
                        except:
                            logger.debug('Smart button has no associated scripts. Skipping {0}'.format(scriptGroup.sourceFile))
                            continue

                    # LinkButton
                    elif scriptGroup.groupType == cfg.LINK_BUTTON_TYPE_NAME and scriptGroup.islinkbutton():
                        if scriptGroup.groupName not in pyrevitribbonitemsdict:
                            logger.debug('Creating push button link to other assembly: {0}'.format(scriptGroup.groupName))
                            ribbonitem = pyrevitribbonpanel.AddItem(
                                PushButtonData(scriptGroup.groupName, scriptGroup.groupName,
                                               scriptGroup.assemblyLocation,
                                               scriptGroup.assemblyName + '.' + scriptGroup.assemblyClassName))
                            newbuttoncount += 1
                        else:
                            logger.debug('Updating push button link to other assembly: {0}'.format(scriptGroup.groupName))
                            ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)
                            ribbonitem.AssemblyName = scriptGroup.assemblyLocation
                            ribbonitem.ClassName = scriptGroup.assemblyName + '.' + scriptGroup.assemblyClassName
                            ribbonitem.Enabled = True
                            updatedbuttoncount += 1
                        ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                        ribbonitem.LargeImage = scriptGroup.buttonIcons.largeBitmap

                # now disable all orphaned buttons in this panel
                for orphanedRibbonItemName, orphanedRibbonItem in pyrevitribbonitemsdict.items():
                    logger.debug('Disabling orphaned ribbon item: {0}'.format(orphanedRibbonItemName))
                    orphanedRibbonItem.Enabled = False

        # final report
        logger.debug('{0} buttons created... {1} buttons updated...'.format(newbuttoncount, updatedbuttoncount))

    def create_ui(self):
        logger.debug('Now setting up ribbon, panels, and buttons...')
        self._create_or_find_pyrevit_panels()
        logger.debug('Ribbon tab and panels are ready. Creating script groups and command buttons...')
        self._create_ui()
        logger.debug('All UI items have been added...')

    def update_ui(self):
        pass
