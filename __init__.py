import clr
import sys
import os
import re
import os.path as op
from datetime import datetime
# import random as rnd
# import pickle as pl
# import time

clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')

from System import *
from System.IO import *
from System.Reflection import *
from System.Reflection.Emit import *
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

from Autodesk.Revit.UI import *
from Autodesk.Revit.Attributes import *
from System.Diagnostics import Process

verbose = True


def report(message, title=False):
    if title:
        print('-' * 100 + '\n' + message + '\n' + '-' * 100)
    else:
        print(message)


def reportv(message, title=False):
    global verbose
    if verbose:
        report(message, title)
        # else:
        # time.sleep(.01)


def find_home_directory():
    # getting home directory from __file__ provided by RPL
    folder = os.path.dirname(__file__)
    if folder.lower().endswith('.dll'):
        # nope - RplAddin
        folder = os.path.dirname(folder)
    sys.path.append(folder)
    return folder


def find_user_temp_directory():
    tempfolder = os.getenv('Temp')
    return tempfolder


# EXCEPTIONS
class PyRevitException(Exception):
    pass


class UnknownAssembly(PyRevitException):
    pass


class UnknownFileNameFormat(PyRevitException):
    pass


# SOOP CLASSES
class PyRevitUISettings:
    pyRevitAssemblyName = 'pyRevit'
    linkButtonTypeName = 'PushButton'
    pushButtonTypeName = 'PushButton'
    smartButtonTypeName = 'SmartButton'
    pulldownButtonTypeName = 'PulldownButton'
    stackedThreeTypeName = 'Stack3'
    splitButtonTypeName = 'SplitButton'
    tooltipParameter = '__doc__'
    userSetupKeyword = '__init__'
    reloadScriptsOverrideName = 'Settings_reloadScripts'
    masterTabName = 'master'

    def __init__(self):
        """Loads settings from settigns file."""
        pass


class ButtonIcons:
    def __init__(self, filedir, filename):
        uri = Uri(op.join(filedir, filename))
        self.smallBitmap = BitmapImage()
        self.smallBitmap.BeginInit()
        self.smallBitmap.UriSource = uri
        self.smallBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.smallBitmap.DecodePixelHeight = 16
        self.smallBitmap.DecodePixelWidth = 16
        self.smallBitmap.EndInit()
        self.largeBitmap = BitmapImage()
        self.largeBitmap.BeginInit()
        self.largeBitmap.UriSource = uri
        self.largeBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.largeBitmap.EndInit()


class ScriptTab:
    def __init__(self, tname, tfolder):
        self.tabName = tname
        self.tabFolder = tfolder
        self.scriptPanels = []
        self.pyRevitUIPanels = {}
        self.pyRevitUIButtons = {}

    def adoptpanels(self, pyrevitscriptpanels):
        for panel in pyrevitscriptpanels:
            if panel.tabName == self.tabName:
                reportv('\tcontains: {0}'.format(panel.panelName))
                self.scriptPanels.append(panel)

    def getsortedscriptpanels(self):
        return sorted(self.scriptPanels, key=lambda x: x.panelOrder)

    def hascommands(self):
        hascmds = False
        for p in self.scriptPanels:
            for g in p.scriptGroups:
                if len(g.commands) > 0:
                    hascmds = True
        return hascmds


class ScriptPanel:
    def __init__(self, filedir, f, tabname):
        self.panelOrder = 0
        self.panelName = ''
        self.scriptGroups = []
        self.tabName = tabname
        self.fileDir = filedir

        fname, fext = op.splitext(op.basename(f))
        if ScriptPanel.isdescriptorfile(fname, fext):
            namepieces = fname.rsplit('_')
            namepieceslength = len(namepieces)
            if namepieceslength == 4 or namepieceslength == 6:
                self.panelOrder, self.panelName = namepieces[0:2]
                self.panelOrder = int(self.panelOrder[:2])
                reportv('Panel found: Type: {0}'.format(self.panelName.ljust(20)))
            else:
                raise UnknownFileNameFormat()
        else:
            raise UnknownFileNameFormat()

    @staticmethod
    def isdescriptorfile(fname, fext):
        return '.png' == fext.lower() and fname[0].isdigit()

    def adoptgroups(self, pyrevitscriptgroups):
        for group in pyrevitscriptgroups:
            if group.panelName == self.panelName and group.tabName == self.tabName:
                reportv('\tcontains: {0}'.format(group.groupName))
                self.scriptGroups.append(group)

    def getsortedscriptgroups(self):
        return sorted(self.scriptGroups, key=lambda x: x.groupOrder)


class ScriptGroup:
    def __init__(self, filedir, f, tabname):
        self.commands = []
        self.sourceDir = ''
        self.sourceFile = ''
        self.sourceFileName = ''
        self.sourceFileExt = '.png'
        self.groupOrder = 0
        self.panelName = ''
        self.groupType = None
        self.groupName = ''
        self.buttonIcons = None
        self.assemblyname = None
        self.assemblyClassName = None
        self.assemblyLocation = None
        self.tabName = tabname

        fname, fext = op.splitext(op.basename(f))
        if ScriptGroup.isdescriptorfile(fname, fext):
            self.sourceDir = filedir
            self.sourceFile = f
            self.sourceFileName = fname
            self.sourceFileExt = fext
            namepieces = fname.rsplit('_')
            namepieceslength = len(namepieces)
            if namepieceslength == 4 or namepieceslength == 6:
                self.groupOrder, self.panelName, self.groupType, self.groupName = namepieces[0:4]
                self.groupOrder = int(self.groupOrder[2:])
                reportv('Script group found: Type: {0}  Name: {1} Parent Panel: {2}'.format(self.groupType.ljust(20),
                                                                                            self.groupName.ljust(20),
                                                                                            self.panelName))
                self.buttonIcons = ButtonIcons(filedir, f)
            # check to see if name has assembly information
            if len(namepieces) == 6:
                self.assemblyname, self.assemblyClassName = namepieces[4:]
                try:
                    self.assemblyname = ScriptGroup.findassembly(self.assemblyname).GetName().Name
                    self.assemblyLocation = ScriptGroup.findassembly(self.assemblyname).Location
                    reportv('                    Assembly.Class: {0}.{1}'.format(self.assemblyname,
                                                                                 self.assemblyClassName))
                except UnknownAssembly:
                    raise
        else:
            raise UnknownFileNameFormat()

    def adoptcommands(self, pyrevitscriptcommands):
        settings = PyRevitUISettings()
        for cmd in pyrevitscriptcommands:
            if cmd.scriptGroupName == self.groupName:
                if cmd.tabName == self.tabName or cmd.tabName == settings.masterTabName:
                    reportv('\tcontains: {0}'.format(cmd.fileName))
                    self.commands.append(cmd)

    def islinkbutton(self):
        return self.assemblyname is not None

    @staticmethod
    def isdescriptorfile(fname, fext):
        return '.png' == fext.lower() and fname[0].isdigit()

    @staticmethod
    def findassembly(assemblyname):
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if assemblyname in loadedAssembly.FullName:
                return loadedAssembly
        raise UnknownAssembly()


class ScriptCommand:
    def __init__(self, filedir, f, tabname):
        self.filePath = ''
        self.fileName = ''
        self.tooltip = ''
        self.cmdName = ''
        self.scriptGroupName = ''
        self.className = ''
        self.iconFileName = ''
        self.buttonIcons = None
        self.tabName = tabname

        fname, fext = op.splitext(op.basename(f))
        settings = PyRevitUISettings()

        # custom name adjustments
        if settings.userSetupKeyword.lower() in fname.lower():
            fname = settings.reloadScriptsOverrideName

        if '_' != fname[0] and '.py' == fext.lower():
            self.filePath = filedir
            self.fileName = f
            self.tooltip = fname + ' ' + fext.lower()
            docstring = ScriptCommand.extractparameter(settings.tooltipParameter, self.getfullscriptaddress())
            if docstring is not None:
                self.tooltip = self.tooltip + '\n' + docstring
            namepieces = fname.rsplit('_')
            namepieceslength = len(namepieces)
            if namepieceslength == 2:
                self.scriptGroupName, self.cmdName = namepieces
                self.className = tabname + self.scriptGroupName + self.cmdName
                reportv('Script found: {0} Group: {1} CommandName: {2}'.format(f.ljust(50),
                                                                               self.scriptGroupName.ljust(20),
                                                                               self.cmdName))
                if op.exists(op.join(filedir, fname + '.png')):
                    self.iconFileName = fname + '.png'
                    self.buttonIcons = ButtonIcons(filedir, self.iconFileName)
                else:
                    self.iconFileName = None
                    self.buttonIcons = None
            else:
                raise UnknownFileNameFormat()
        else:
            raise UnknownFileNameFormat()

    def getfullscriptaddress(self):
        return op.join(self.filePath, self.fileName)

    def getscriptbasename(self):
        return self.scriptGroupName + '_' + self.cmdName

    @staticmethod
    def extractparameter(param, fileaddress):
        finder = re.compile(param + '\s*=\s*\'*\"*(.+?)[\'\"]', flags=re.DOTALL | re.IGNORECASE)
        with open(fileaddress, 'r') as f:
            values = finder.findall(f.read())
            if values:
                return values[0].replace('\\n', '\n')
            else:
                return None


class PyRevitUISession:
    def __init__(self, homedir, settings):
        self.loadedPyRevitScripts = []
        self.loadedPyRevitAssemblies = []
        self.pyRevitScriptPanels = []
        self.pyRevitScriptGroups = []
        self.pyRevitScriptCommands = []
        self.pyRevitScriptTabs = []
        self.homeDir = homedir
        self.userTempFolder = find_user_temp_directory()
        self.commandLoaderClass = None
        self.commandLoaderAssembly = None
        self.newAssemblyLocation = None
        self.settings = settings
        self.revitVersion = __revit__.Application.VersionNumber

        report('Home Directory is: {0}'.format(self.homeDir))

        # collect information about previously loaded assemblies
        report('Initializing python script loader...')
        res = self.findcommandloaderclass()
        if res:
            self.findloadedpyrevitassemblies()
            self.cleanup()

            # find commands, script groups and assign commands
            self.createreloadbutton(self.homeDir)
            report('Searching for tabs, panels, groups, and scripts...')
            self.findscripttabs(self.homeDir)

            # create assembly dll
            report('Building script executer assembly...')
            self.createassmebly()

            # setting up UI
            report('Executer assembly saved. Creating pyRevit UI.')
            self.createpyrevitui()
        else:
            report('pyRevit load failed...')

    def cleanup(self):
        revitinstances = list(Process.GetProcessesByName('Revit'))
        revitversionstr = self.getrevitversionstr()
        if len(revitinstances) > 1:
            reportv('Multiple Revit instance are running...Skipping DLL Cleanup')
        elif len(revitinstances) == 1 and not self.isreloading():
            reportv('Cleaning up old DLL files...')
            files = os.listdir(self.userTempFolder)
            for f in files:
                if f.startswith(self.settings.pyRevitAssemblyName + revitversionstr):
                    try:
                        os.remove(op.join(self.userTempFolder, f))
                        reportv('Existing .Dll Removed: {0}'.format(f))
                    except:
                        reportv('Error deleting .DLL file: {0}'.format(f))

    def isreloading(self):
        return len(self.loadedPyRevitAssemblies) > 0

    def getrevitversionstr(self):
        return str(self.revitVersion)

    def findcommandloaderclass(self):
        # tries to find the revitpythonloader assembly first
        reportv('Asking Revit for RevitPythonLoader Command Loader class...')
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if 'RevitPythonLoader' in loadedAssembly.FullName:
                reportv('RPL Assembly found: {0}'.format(loadedAssembly.GetName().FullName))
                self.commandLoaderClass = loadedAssembly.GetType('RevitPythonLoader.CommandLoaderBase')
                self.commandLoaderAssembly = loadedAssembly
                return True

        # if revitpythonloader doesn't exist tries to find the revitpythonshell assembly
        reportv('Can not find RevitPythonLoader. Asking Revit for RevitPythonShell Command Loader class instead...')
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if 'RevitPythonShell' in loadedAssembly.FullName:
                reportv('RPS Assembly found: {0}'.format(loadedAssembly.GetName().FullName))
                self.commandLoaderClass = loadedAssembly.GetType('RevitPythonShell.CommandLoaderBase')
                self.commandLoaderAssembly = loadedAssembly
                return True

        reportv('Can not find RevitPythonShell either. Aborting load...')
        self.commandLoaderClass = None
        self.commandLoaderAssembly = None
        return None

    def findloadedpyrevitassemblies(self):
        reportv('Asking Revit for previously loaded pyRevit assemblies...')
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if self.settings.pyRevitAssemblyName in loadedAssembly.FullName:
                reportv('Existing assembly found: {0}'.format(loadedAssembly.FullName))
                self.loadedPyRevitAssemblies.append(loadedAssembly)
                self.loadedPyRevitScripts.extend([ct.Name for ct in loadedAssembly.GetTypes()])

    def findscriptcommands(self, tabdir, tabname):
        reportv('Searching tab folder for scripts...')
        files = sorted(os.listdir(tabdir))
        for f in files:
            # creating scriptCommands
            fname, fext = op.splitext(op.basename(f))
            if '.py' == fext.lower():
                try:
                    cmd = ScriptCommand(tabdir, f, tabname)
                    self.pyRevitScriptCommands.append(cmd)
                except UnknownFileNameFormat:
                    reportv('Can not recognize name pattern. skipping: {0}'.format(f))
                    continue
                except:
                    reportv('Something is wrong. skipping: {0}'.format(f))
                    continue

        if not len(self.pyRevitScriptCommands) > 0:
            report('No Scripts found...')

    def findscriptgroups(self, tabdir, tabname):
        reportv('Searching content folder for script groups ...')
        self.findscriptcommands(tabdir, tabname)
        files = os.listdir(tabdir)
        for f in files:
            # creating ScriptGroup list and adopting ScriptCommands
            fname, fext = op.splitext(op.basename(f))
            if '.png' == fext.lower():
                try:
                    scriptgroup = ScriptGroup(tabdir, f, tabname)
                    scriptgroup.adoptcommands(self.pyRevitScriptCommands)
                    self.pyRevitScriptGroups.append(scriptgroup)
                except UnknownFileNameFormat:
                    if f in [x.iconFileName for x in self.pyRevitScriptCommands]:
                        reportv('Skipping script icon file: {0}'.format(f))
                        continue
                    else:
                        reportv('Can not recognize name pattern. skipping: {0}'.format(f))
                        continue
                except UnknownAssembly:
                    reportv('Unknown assembly error. Skipping: {0}'.format(f))
                    continue

    def findscriptpanels(self, tabdir, tabname):
        reportv('Searching content folder for script panels ...')
        self.findscriptgroups(tabdir, tabname)
        files = os.listdir(tabdir)
        for f in files:
            # creating ScriptPanel list and adopting ScriptGroups
            fname, fext = op.splitext(op.basename(f))
            if '.png' == fext.lower():
                try:
                    scriptpanel = ScriptPanel(tabdir, f, tabname)
                    collectedscriptpanels = [(x.panelName, x.tabName) for x in self.pyRevitScriptPanels]
                    if (scriptpanel.panelName, scriptpanel.tabName) not in collectedscriptpanels:
                        scriptpanel.adoptgroups(self.pyRevitScriptGroups)
                        self.pyRevitScriptPanels.append(scriptpanel)
                except UnknownFileNameFormat:
                    if f in [x.iconFileName for x in self.pyRevitScriptCommands]:
                        reportv('Skipping script icon file: {0}'.format(f))
                        continue
                    else:
                        reportv('Can not recognize name pattern. skipping: {0}'.format(f))
                        continue

    def findscripttabs(self, rootdir):
        for dirName in os.listdir(rootdir):
            fulltabpath = op.join(rootdir, dirName)
            if op.isdir(fulltabpath) and ('_' not in dirName):
                reportv('\n')
                reportv('Searching fo scripts under: {0}'.format(fulltabpath), title=True)
                tabnames = [x.tabName for x in self.pyRevitScriptTabs]
                if dirName not in tabnames:
                    scripttab = ScriptTab(dirName, fulltabpath)
                    self.findscriptpanels(fulltabpath, scripttab.tabName)
                    reportv('\nTab found: {0}'.format(scripttab.tabName))
                    scripttab.adoptpanels(self.pyRevitScriptPanels)
                    self.pyRevitScriptTabs.append(scripttab)
                    sys.path.append(fulltabpath)
                    reportv('\n')
            else:
                continue

    def createreloadbutton(self, rootdir):
        reportv('Creating "Reload Scripts" button...')
        for fname in os.listdir(rootdir):
            fulltabpath = op.join(rootdir, fname)
            if not op.isdir(fulltabpath) and self.settings.userSetupKeyword in fname:
                try:
                    cmd = ScriptCommand(rootdir, fname, self.settings.masterTabName)
                    self.pyRevitScriptCommands.append(cmd)
                    reportv('Reload button added.\n')
                except:
                    reportv('\nCould not create reload command.\n')
                    continue

    def createassmebly(self):
        # create DLL folder
        # dllfolder = Path.Combine( self.homeDir, self.settings.pyRevitAssemblyName )
        # if not os.path.exists( dllfolder ):
        # os.mkdir( dllfolder )
        dllfolder = self.userTempFolder
        # make assembly name
        generatedassemblyname = self.settings.pyRevitAssemblyName + self.getrevitversionstr() + datetime.now().strftime(
            '_%y%m%d%H%M%S')
        dllname = generatedassemblyname + '.dll'
        # create assembly
        windowsassemblyname = AssemblyName(Name=generatedassemblyname, Version=Version(1, 0, 0, 0))
        reportv('Generated assembly name for this session: {0}'.format(generatedassemblyname))
        reportv('Generated windows assembly name for this session: {0}'.format(windowsassemblyname))
        reportv('Generated DLL name for this session: {0}'.format(dllname))
        assemblybuilder = AppDomain.CurrentDomain.DefineDynamicAssembly(windowsassemblyname,
                                                                        AssemblyBuilderAccess.RunAndSave, dllfolder)
        modulebuilder = assemblybuilder.DefineDynamicModule(generatedassemblyname, dllname)

        # create command classes
        for cmd in self.pyRevitScriptCommands:
            typebuilder = modulebuilder.DefineType(cmd.className, TypeAttributes.Class | TypeAttributes.Public,
                                                   self.commandLoaderClass)

            # add RegenerationAttribute to type
            regenerationconstrutorinfo = clr.GetClrType(RegenerationAttribute).GetConstructor(
                Array[Type]((RegenerationOption,)))
            regenerationattributebuilder = CustomAttributeBuilder(regenerationconstrutorinfo,
                                                                  Array[object]((RegenerationOption.Manual,)))
            typebuilder.SetCustomAttribute(regenerationattributebuilder)

            # add TransactionAttribute to type
            transactionconstructorinfo = clr.GetClrType(TransactionAttribute).GetConstructor(
                Array[Type]((TransactionMode,)))
            transactionattributebuilder = CustomAttributeBuilder(transactionconstructorinfo,
                                                                 Array[object]((TransactionMode.Manual,)))
            typebuilder.SetCustomAttribute(transactionattributebuilder)

            # call base constructor with script path
            ci = self.commandLoaderClass.GetConstructor(Array[Type]((str,)))
            constructorbuilder = typebuilder.DefineConstructor(MethodAttributes.Public, CallingConventions.Standard,
                                                               Array[Type](()))
            gen = constructorbuilder.GetILGenerator()
            gen.Emit(OpCodes.Ldarg_0)  # Load "this" onto eval stack
            gen.Emit(OpCodes.Ldstr, cmd.getfullscriptaddress())  # Load the path to the command as a string onto stack
            gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the string)
            gen.Emit(OpCodes.Nop)  # Fill some space - this is how it is generated for equivalent C# code
            gen.Emit(OpCodes.Nop)
            gen.Emit(OpCodes.Nop)
            gen.Emit(OpCodes.Ret)
            typebuilder.CreateType()

        # save final assembly
        assemblybuilder.Save(dllname)
        self.newAssemblyLocation = Path.Combine(dllfolder, dllname)

    def createorfindpyrevitpanels(self):
        reportv('Searching for existing pyRevit panels...')
        for scriptTab in self.pyRevitScriptTabs:
            # creates pyrevitribbonpanels for existing or newly created panels
            try:
                pyrevitribbonpanels = {p.Name: p for p in __revit__.GetRibbonPanels(scriptTab.tabName)}
            except:
                if scriptTab.hascommands():
                    reportv('Creating pyRevit ribbon...')
                    __revit__.CreateRibbonTab(scriptTab.tabName)
                    pyrevitribbonpanels = {p.Name: p for p in __revit__.GetRibbonPanels(scriptTab.tabName)}
                else:
                    reportv('pyRevit ribbon found but does not include any scripts. Skipping: {0}'.format(
                        scriptTab.tabName))
            reportv('Searching for panels...')
            for panel in scriptTab.getsortedscriptpanels():
                if panel.panelName in pyrevitribbonpanels.keys():
                    reportv('Existing panel found: {0}'.format(panel.panelName))
                    scriptTab.pyRevitUIPanels[panel.panelName] = pyrevitribbonpanels[panel.panelName]
                    scriptTab.pyRevitUIButtons[panel.panelName] = list(pyrevitribbonpanels[panel.panelName].GetItems())
                else:
                    reportv('Creating scripts panel: {0}'.format(panel.panelName))
                    newpanel = __revit__.CreateRibbonPanel(scriptTab.tabName, panel.panelName)
                    scriptTab.pyRevitUIPanels[panel.panelName] = newpanel
                    scriptTab.pyRevitUIButtons[panel.panelName] = []

    def createui(self):
        newbuttoncount = updatedbuttoncount = 0
        for scriptTab in self.pyRevitScriptTabs:
            for scriptPanel in scriptTab.getsortedscriptpanels():
                pyrevitribbonpanel = scriptTab.pyRevitUIPanels[scriptPanel.panelName]
                pyrevitribbonitemsdict = {b.Name: b for b in scriptTab.pyRevitUIButtons[scriptPanel.panelName]}
                reportv('Creating\\Updating ribbon items for panel: {0}'.format(scriptPanel.panelName))
                for scriptGroup in scriptPanel.getsortedscriptgroups():
                    # PulldownButton or SplitButton
                    if scriptGroup.groupType == self.settings.pulldownButtonTypeName or scriptGroup.groupType == self.settings.splitButtonTypeName:
                        # PulldownButton
                        if scriptGroup.groupType == self.settings.pulldownButtonTypeName:
                            if scriptGroup.groupName not in pyrevitribbonitemsdict:
                                reportv('\tCreating pulldown button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    PulldownButtonData(scriptGroup.groupName, scriptGroup.groupName))
                            else:
                                reportv('\tUpdating pulldown button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)

                        # SplitButton
                        elif scriptGroup.groupType == self.settings.splitButtonTypeName:
                            if scriptGroup.groupName not in pyrevitribbonitemsdict.keys():
                                reportv('\tCreating split button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    SplitButtonData(scriptGroup.groupName, scriptGroup.groupName))
                            else:
                                reportv('\tUpdating split button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)

                        ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                        ribbonitem.LargeImage = scriptGroup.buttonIcons.largeBitmap
                        existingribbonitempushbuttonsdict = {b.ClassName: b for b in ribbonitem.GetItems()}

                        for cmd in scriptGroup.commands:
                            if cmd.className not in existingribbonitempushbuttonsdict:
                                reportv('\t\tCreating push button: {0}'.format(cmd.className))
                                buttondata = PushButtonData(cmd.className, cmd.cmdName, self.newAssemblyLocation,
                                                            cmd.className)
                                buttondata.ToolTip = cmd.tooltip
                                if cmd.buttonIcons:
                                    buttondata.LargeImage = cmd.buttonIcons.largeBitmap
                                else:
                                    buttondata.LargeImage = scriptGroup.buttonIcons.largeBitmap
                                ribbonitem.AddPushButton(buttondata)
                                newbuttoncount += 1
                            else:
                                reportv('\t\tUpdating push button: {0}'.format(cmd.className))
                                pushbutton = existingribbonitempushbuttonsdict.pop(cmd.className)
                                pushbutton.ToolTip = cmd.tooltip
                                pushbutton.Enabled = True
                                if cmd.buttonIcons:
                                    pushbutton.LargeImage = cmd.buttonIcons.largeBitmap
                                else:
                                    pushbutton.LargeImage = scriptGroup.buttonIcons.largeBitmap
                                updatedbuttoncount += 1
                        for orphanedButtonName, orphanedButton in existingribbonitempushbuttonsdict.items():
                            reportv('\tDisabling orphaned button: {0}'.format(orphanedButtonName))
                            orphanedButton.Enabled = False

                    # StackedButtons
                    elif scriptGroup.groupType == self.settings.stackedThreeTypeName:
                        reportv('\tCreating\\Updating 3 stacked buttons: {0}'.format(scriptGroup.groupType))
                        stackcommands = []
                        for cmd in scriptGroup.commands:
                            if cmd.className not in pyrevitribbonitemsdict:
                                reportv('\t\tCreating stacked button: {0}'.format(cmd.className))
                                buttondata = PushButtonData(cmd.className, cmd.cmdName, self.newAssemblyLocation,
                                                            cmd.className)
                                buttondata.ToolTip = cmd.tooltip
                                if cmd.buttonIcons:
                                    buttondata.Image = cmd.buttonIcons.smallBitmap
                                else:
                                    buttondata.Image = scriptGroup.buttonIcons.smallBitmap
                                stackcommands.append(buttondata)
                                newbuttoncount += 1
                            else:
                                reportv('\t\tUpdating stacked button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonitemsdict.pop(cmd.className)
                                ribbonitem.AssemblyName = self.newAssemblyLocation
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
                    elif scriptGroup.groupType == self.settings.pushButtonTypeName and not scriptGroup.islinkbutton():
                        try:
                            cmd = scriptGroup.commands.pop()
                            if cmd.className not in pyrevitribbonitemsdict:
                                reportv('\tCreating push button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    PushButtonData(cmd.className, scriptGroup.groupName, self.newAssemblyLocation,
                                                   cmd.className))
                                newbuttoncount += 1
                            else:
                                reportv('\tUpdating push button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonitemsdict.pop(cmd.className)
                                ribbonitem.AssemblyName = self.newAssemblyLocation
                                ribbonitem.ClassName = cmd.className
                                ribbonitem.Enabled = True
                                updatedbuttoncount += 1
                            ribbonitem.ToolTip = cmd.tooltip
                            ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                            ribbonitem.LargeImage = scriptGroup.buttonIcons.largeBitmap
                        except:
                            reportv(
                                '\tPushbutton has no associated scripts. Skipping {0}'.format(scriptGroup.sourceFile))
                            continue

                    # SmartButton
                    elif scriptGroup.groupType == self.settings.smartButtonTypeName and not scriptGroup.islinkbutton():
                        try:
                            cmd = scriptGroup.commands.pop()
                            if cmd.className not in pyrevitribbonitemsdict:
                                reportv('\tCreating push button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    PushButtonData(cmd.className, scriptGroup.groupName, self.newAssemblyLocation,
                                                   cmd.className))
                                newbuttoncount += 1
                            else:
                                reportv('\tUpdating push button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonitemsdict.pop(cmd.className)
                                ribbonitem.AssemblyName = self.newAssemblyLocation
                                ribbonitem.ClassName = cmd.className
                                ribbonitem.Enabled = True
                                updatedbuttoncount += 1
                            ribbonitem.ToolTip = cmd.tooltip
                            importedscript = __import__(cmd.getscriptbasename())
                            importedscript.selfInit(__revit__, cmd.getfullscriptaddress(), ribbonitem)
                        except:
                            reportv(
                                '\tSmart button has no associated scripts. Skipping {0}'.format(scriptGroup.sourceFile))
                            continue

                    # LinkButton
                    elif scriptGroup.groupType == self.settings.linkButtonTypeName and scriptGroup.islinkbutton():
                        if scriptGroup.groupName not in pyrevitribbonitemsdict:
                            reportv('\tCreating push button link to other assembly: {0}'.format(scriptGroup.groupName))
                            ribbonitem = pyrevitribbonpanel.AddItem(
                                PushButtonData(scriptGroup.groupName, scriptGroup.groupName,
                                               scriptGroup.assemblyLocation,
                                               scriptGroup.assemblyName + '.' + scriptGroup.assemblyClassName))
                            newbuttoncount += 1
                        else:
                            reportv('\tUpdating push button link to other assembly: {0}'.format(scriptGroup.groupName))
                            ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)
                            ribbonitem.AssemblyName = scriptGroup.assemblyLocation
                            ribbonitem.ClassName = scriptGroup.assemblyName + '.' + scriptGroup.assemblyClassName
                            ribbonitem.Enabled = True
                            updatedbuttoncount += 1
                        ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                        ribbonitem.LargeImage = scriptGroup.buttonIcons.largeBitmap

                # now disable all orphaned buttons in this panel
                for orphanedRibbonItemName, orphanedRibbonItem in pyrevitribbonitemsdict.items():
                    reportv('\tDisabling orphaned ribbon item: {0}'.format(orphanedRibbonItemName))
                    orphanedRibbonItem.Enabled = False

        # final report
        reportv('\n\n')
        report('{0} buttons created...\n{1} buttons updated...\n\n'.format(newbuttoncount, updatedbuttoncount))

    def createpyrevitui(self):
        # setting up UI
        reportv('Now setting up ribbon, panels, and buttons...')
        self.createorfindpyrevitpanels()
        reportv('Ribbon tab and panels are ready. Creating script groups and command buttons...')
        self.createui()
        reportv('All UI items have been added...')


# MAIN
__window__.Width = 1100
# find pyRevit home directory and initialize current session
thisSession = PyRevitUISession(find_home_directory(), PyRevitUISettings())
