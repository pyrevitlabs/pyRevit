import re
import hashlib

# pyrevit module imports
import pyRevit.config as cfg
from pyRevit.exceptions import *
from pyRevit.logger import logger

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


# todo rename this module to a better name. These aren't the UI objects really. UI objects are used from RevitAPI and there is no need to recreate them. These elements are database classes that represent data that is associated with each UI element.
# utility classes
class ButtonIcons:
    def __init__(self, filedir, filename):
        self.imagefile_dir = filedir
        self.imagefile_name = filename
        uri = Uri(op.join(filedir, filename))
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

    def get_clean_dict(self):
        d = self.__dict__.copy()
        for key in ['smallBitmap', 'mediumBitmap', 'largeBitmap']:
            if key in d.keys():
                d.pop(key)
        return d


class ScriptFileContents:
    def __init__(self, fileaddress):
        self.filecontents = ''
        with open(fileaddress, 'r') as f:
            self.filecontents = f.readlines()

    def extractparameter(self, param):
        paramstringfound = False
        paramstring = ''
        paramfinder = re.compile(param + '\s*=\s*[\'\"](.*)[\'\"]', flags=re.IGNORECASE)
        paramfinderex = re.compile('^\s*[\'\"](.*)[\'\"]', flags=re.IGNORECASE)
        for thisline in self.filecontents:
            if not paramstringfound:
                values = paramfinder.findall(thisline)
                if values:
                    paramstring = values[0]
                    paramstringfound = True
                continue
            elif paramstringfound:
                values = paramfinderex.findall(thisline)
                if values:
                    paramstring += values[0]
                    continue
                break
        return paramstring.replace('\\\'', '\'').replace('\\"', '\"').replace('\\n', '\n').replace('\\t', '\t')


# ribbon item wrapper classes
class ScriptTab:
    def __init__(self, tname, tfolder):
        self.tabName = tname.replace(cfg.TAB_POSTFIX, '')
        self.tabDirName = tname
        self.tabFolder = tfolder
        self.scriptPanels = []
        self.pyRevitUIPanels = {}
        self.pyRevitUIButtons = {}
        self.loaded_from_cache = False
        self.tabHash = self.calculate_hash()

    def adopt_panels(self, pyrevitscriptpanels):
        already_adopted_panels = [x.panelName for x in self.scriptPanels]
        for panel in pyrevitscriptpanels:
            if panel.tabName == self.tabName and panel.panelName not in already_adopted_panels:
                logger.debug('contains: {0}'.format(panel.panelName))
                self.scriptPanels.append(panel)

    def get_sorted_scriptpanels(self):
        return sorted(self.scriptPanels, key=lambda x: x.panelOrder)

    def hascommands(self):
        for p in self.scriptPanels:
            for g in p.scriptGroups:
                if len(g.scriptCommands) > 0:
                    return True
        return False

    def calculate_hash(self):
        """Creates a unique hash # to represent state of directory."""
        # logger.info('Generating Hash of directory')
        # search does not include png files:
        #   if png files are added the parent folder mtime gets affected
        #   cache only saves the png address and not the contents so they'll get loaded everytime
        # todo: improve speed by pruning dir: dirs[:] = [d for d in dirs if d not in excludes]
        #       see http://stackoverflow.com/a/5141710/2350244
        pat = r'(\.panel)|(\.tab)'
        patfile = r'(\.py)'
        mtime_sum = 0
        for root, dirs, files in os.walk(self.tabFolder):
            if re.search(pat, root, flags=re.IGNORECASE):
                mtime_sum += op.getmtime(root)
                for filename in files:
                    if re.search(patfile, filename, flags=re.IGNORECASE):
                        modtime = op.getmtime(op.join(root, filename))
                        mtime_sum += modtime
        return hashlib.md5(str(mtime_sum)).hexdigest()

    def get_clean_dict(self):
        d = self.__dict__.copy()
        for key in ['pyRevitUIPanels', 'pyRevitUIButtons']:
            if key in d.keys():
                d.pop(key)
        return d

    def load_from_cache(self, cached_dict):
        for k, v in cached_dict.items():
            if "scriptPanels" == k:
                for cached_panel_dict in v:
                    logger.debug('Cache: Loading script panel: {}'.format(cached_panel_dict['panelName']))
                    self.scriptPanels.append(ScriptPanel('', '', '', '', cached_panel_dict))
            else:
                self.__dict__[k] = v
        self.loaded_from_cache = True


class ScriptPanel:
    def __init__(self, tabdir, fullpanelfilename, tabname, bundledpanel, cache=None):
        self.panelOrder = 0
        self.panelName = ''
        self.scriptGroups = []
        self.tabName = tabname
        self.tabDir = tabdir
        self.isBundled = bundledpanel

        if not cache:
            if self.isBundled:
                self.panelName = fullpanelfilename.replace(cfg.PANEL_BUNDLE_POSTFIX, '')
            else:
                fname, fext = op.splitext(op.basename(fullpanelfilename))
                if ScriptPanel.isdescriptorfile(fname, fext):
                    namepieces = fname.rsplit('_')
                    namepieceslength = len(namepieces)
                    if namepieceslength == 4 or namepieceslength == 6:
                        self.panelOrder, self.panelName = namepieces[0:2]
                        self.panelOrder = int(self.panelOrder[:2])
                        logger.debug('Panel found: Type: {0}'.format(self.panelName.ljust(20)))
                    else:
                        raise PyRevitUnknownFileNameFormatError()
                else:
                    raise PyRevitUnknownFileNameFormatError()
        else:
            self.load_from_cache(cache)

    @staticmethod
    def isdescriptorfile(fname, fext):
        return cfg.ICON_FILE_FORMAT == fext.lower() and fname[0:3].isdigit()

    def adoptgroups(self, pyrevitscriptgroups):
        already_adopted_groups = [x.groupName for x in self.scriptGroups]
        for group in pyrevitscriptgroups:
            if group.panelName == self.panelName \
                    and group.tabName == self.tabName \
                    and group.groupName not in already_adopted_groups:
                logger.debug('contains: {0}'.format(group.groupName))
                self.scriptGroups.append(group)

    def get_sorted_scriptgroups(self):
        return sorted(self.scriptGroups, key=lambda x: x.groupOrder)

    def get_clean_dict(self):
        return self.__dict__.copy()

    def load_from_cache(self, cached_dict):
        for k, v in cached_dict.items():
            if "scriptGroups" == k:
                for cached_group_dict in v:
                    logger.debug('Cache: Loading script group: {}'.format(cached_group_dict['groupName']))
                    self.scriptGroups.append(ScriptGroup('', '', '', '', cached_group_dict))
            else:
                self.__dict__[k] = v


class ScriptGroup:
    def __init__(self, filedir, f, tabname, bundledPanelName, cache = None):
        self.scriptCommands= []
        self.sourceDir = ''
        self.sourceFile = ''
        self.sourceFileName = ''
        self.sourceFileExt = cfg.ICON_FILE_FORMAT
        self.groupOrder = 0
        self.panelName = bundledPanelName
        self.groupType = None
        self.groupName = ''
        self.buttonIcons = None
        self.assemblyName = None
        self.assemblyClassName = None
        self.assemblyLocation = None
        self.tabName = tabname

        if not cache:
            fname, fext = op.splitext(op.basename(f))
            if ScriptGroup.isdescriptorfile(fname, fext):
                self.sourceDir = filedir
                self.sourceFile = f
                self.sourceFileName = fname
                self.sourceFileExt = fext
                namepieces = fname.rsplit('_')
                namepieceslength = len(namepieces)
                if namepieces[0].isdigit():
                    if namepieceslength == 4 or namepieceslength == 6:
                        self.groupOrder, self.panelName, self.groupType, self.groupName = namepieces[0:4]
                        self.groupOrder = int(self.groupOrder[2:])
                        logger.debug('Script group found: Type: {0} Name: {1} Parent Panel: {2}'.format(self.groupType.ljust(20),
                                                                                                   self.groupName.ljust(20),
                                                                                                   self.panelName))
                        self.buttonIcons = ButtonIcons(filedir, f)
                    elif namepieceslength == 3:
                        self.groupOrder, self.groupType, self.groupName = namepieces
                        self.groupOrder = int(self.groupOrder)
                        logger.debug('Script group found: Type: {0} Name: {1} Parent Panel: {2}'.format(self.groupType.ljust(20),
                                                                                                   self.groupName.ljust(20),
                                                                                                   self.panelName))
                        self.buttonIcons = ButtonIcons(filedir, f)

                    # check to see if name has assembly information
                    if namepieceslength == 6:
                        self.assemblyName, self.assemblyClassName = namepieces[4:]
                        try:
                            self.assemblyName = ScriptGroup.findassembly(self.assemblyName).GetName().Name
                            self.assemblyLocation = ScriptGroup.findassembly(self.assemblyName).Location
                            logger.debug('Assembly.Class: {0}.{1}'.format(self.assemblyName, self.assemblyClassName))
                        except PyRevitUnknownAssemblyError:
                            raise
            else:
                raise PyRevitUnknownFileNameFormatError()
        else:
            self.load_from_cache(cache)

    def adoptcommands(self, pyrevitscriptcommands, MASTER_TAB_NAME):
        already_adopted_commands = [x.fileName for x in self.scriptCommands]
        for cmd in pyrevitscriptcommands:
            if cmd.scriptGroupName == self.groupName \
            and (cmd.tabName == self.tabName or cmd.tabName == MASTER_TAB_NAME) \
            and cmd.fileName not in already_adopted_commands:
                    logger.debug('contains: {0}'.format(cmd.fileName))
                    self.scriptCommands.append(cmd)

    def islinkbutton(self):
        return self.assemblyName is not None

    @staticmethod
    def isdescriptorfile(fname, fext):
        return cfg.ICON_FILE_FORMAT == fext.lower() and fname[0:2].isdigit()

    @staticmethod
    def findassembly(assemblyname):
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if assemblyname in loadedAssembly.FullName:
                return loadedAssembly
        raise PyRevitUnknownAssemblyError()

    def get_clean_dict(self):
        return self.__dict__.copy()

    def load_from_cache(self, cached_dict):
        for k,v in cached_dict.items():
            if "scriptCommands" == k:
                for cached_cmd_dict in v:
                    logger.debug('Cache: Loading script command: {}'.format(cached_cmd_dict['cmdName']))
                    self.scriptCommands.append(ScriptCommand('','','',cached_cmd_dict))
            elif "buttonIcons" == k:
                if v:
                    self.buttonIcons = ButtonIcons(v["imagefile_dir"], v["imagefile_name"])
            else:
                self.__dict__[k] = v


class ScriptCommand:
    def __init__(self, filedir, f, tabname, cache = None):
        self.filePath = ''
        self.fileName = ''
        self.tooltip = ''
        self.cmdName = ''
        self.scriptGroupName = ''
        self.className = ''
        self.iconFileName = ''
        self.buttonIcons = None
        self.tabName = tabname
        self.search_paths = self.filePath

        if not cache:
            fname, fext = op.splitext(op.basename(f))

            # custom name adjustments
            if cfg.PYREVIT_INIT_SCRIPT_NAME.lower() in fname.lower() and tabname == cfg.MASTER_TAB_NAME:
                fname = cfg.RELOAD_SCRIPTS_OVERRIDE_GROUP_NAME + '_' + cfg.RELOAD_SCRIPTS_OVERRIDE_SCRIPT_NAME

            if not fname.startswith('_') and '.py' == fext.lower():
                self.filePath = filedir
                self.fileName = f

                namepieces = fname.rsplit('_')
                namepieceslength = len(namepieces)
                if namepieceslength == 2:
                    self.scriptGroupName, self.cmdName = namepieces
                    self.className = tabname + self.scriptGroupName + self.cmdName
                    for char, repl in cfg.SPECIAL_CHARS.items():
                        self.className = self.className.replace(char, repl)
                    logger.debug('Script found: {0} Group: {1} CommandName: {2}'.format(f.ljust(50),
                                                                                   self.scriptGroupName.ljust(20),
                                                                                   self.cmdName))
                    if op.exists(op.join(filedir, fname + cfg.ICON_FILE_FORMAT)):
                        self.iconFileName = fname + cfg.ICON_FILE_FORMAT
                        self.buttonIcons = ButtonIcons(filedir, self.iconFileName)
                    else:
                        self.iconFileName = None
                        self.buttonIcons = None
                else:
                    raise PyRevitUnknownFileNameFormatError()

                script_contents = ScriptFileContents(self.getfullscriptaddress())
                docstring = script_contents.extractparameter(cfg.TOOLTIP_PARAM)
                author = script_contents.extractparameter(cfg.AUTHOR_PARAM)
                if docstring is not None:
                    self.tooltip = '{0}'.format(docstring)
                else:
                    self.tooltip = ''
                self.tooltip += '\n\nScript Name:\n{0}'.format(fname + ' ' + fext.lower())
                if author is not None and author != '':
                    self.tooltip += '\n\nAuthor:\n{0}'.format(author)
            else:
                raise PyRevitUnknownFileNameFormatError()
        else:
            self.load_from_cache(cache)

    def getfullscriptaddress(self):
        return op.join(self.filePath, self.fileName)

    def getscriptbasename(self):
        return self.scriptGroupName + '_' + self.cmdName

    def get_clean_dict(self):
        return self.__dict__.copy()

    def load_from_cache(self, cached_dict):
        for k,v in cached_dict.items():
            if "buttonIcons" == k:
                if v:
                    self.buttonIcons = ButtonIcons(v["imagefile_dir"], v["imagefile_name"])
            else:
                self.__dict__[k] = v