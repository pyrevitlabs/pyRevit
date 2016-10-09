import os
import os.path as op

from pyRevit.logger import logger
from pyRevit.exceptions import *
import pyRevit.config as cfg
import pyRevit.utils as prutils

from pyRevit.uielements import *
from pyRevit.cache import PyRevitCache

class PyRevitCommandsTree():
    def __init__(self):
        self.pyRevitScriptPanels = []
        self.pyRevitScriptGroups = []
        self.pyRevitScriptCommands = []
        self.pyRevitScriptTabs = []

        self.sessionCache = self._get_prev_session_cache()
        
        self._find_scripttabs(cfg.HOME_DIR)
        self._create_reload_button(cfg.LOADER_DIR)

        self.sessionCache.update_cache(self.pyRevitScriptTabs)

    def _get_prev_session_cache(self):
        return PyRevitCache()

    def _create_reload_button(self, loaderDir):
        logger.debug('Creating "Reload Scripts" button...')
        for fname in os.listdir(loaderDir):
            fulltabpath = op.join(loaderDir, fname)
            if not op.isdir(fulltabpath) and cfg.PYREVIT_INIT_SCRIPT_NAME in fname:
                try:
                    cmd = ScriptCommand(loaderDir, fname, cfg.MASTER_TAB_NAME)
                    self.pyRevitScriptCommands.append(cmd)
                    logger.debug('Reload button added.')
                except:
                    logger.debug('Could not create reload command.')
                    continue

    def _find_scriptcommands(self, searchdir, tabname):
        logger.debug('Searching tab folder for scripts...')
        files = sorted(os.listdir(searchdir))
        for fullfilename in files:
            fullfilepath = op.join(searchdir, fullfilename)
            fname, fext = op.splitext(op.basename(fullfilename))
            if not op.isdir(fullfilepath) and '.py' == fext.lower():
                try:
                    cmd = ScriptCommand(searchdir, fullfilename, tabname)
                    self.pyRevitScriptCommands.append(cmd)
                except PyRevitUnknownFileNameFormatError:
                    logger.debug('Can not recognize name pattern. skipping: {0}'.format(fullfilename))
                    continue
                except:
                    logger.debug('Something is wrong. skipping: {0}'.format(fullfilename))
                    continue

        if not len(self.pyRevitScriptCommands) > 0:
            logger.debug('No Scripts found...')

    def _find_scriptgroups(self, searchdir, tabname, bundledPanelName = ''):
        logger.debug('Searching content folder for script groups ...')
        self._find_scriptcommands(searchdir, tabname)
        files = os.listdir(searchdir)
        for fullfilename in files:
            fullfilepath = op.join(searchdir, fullfilename)
            fname, fext = op.splitext(op.basename(fullfilename))
            if not op.isdir(fullfilepath) and cfg.ICON_FILE_FORMAT == fext.lower():
                try:
                    scriptgroup = ScriptGroup(searchdir, fullfilename, tabname, bundledPanelName)
                    scriptgroup.adoptcommands(self.pyRevitScriptCommands, cfg.MASTER_TAB_NAME)
                    self.pyRevitScriptGroups.append(scriptgroup)
                except PyRevitUnknownFileNameFormatError:
                    if fullfilename in [x.iconFileName for x in self.pyRevitScriptCommands]:
                        logger.debug('Skipping script icon file: {0}'.format(fullfilename))
                        continue
                    else:
                        logger.debug('Can not recognize name pattern. skipping: {0}'.format(fullfilename))
                        continue
                except PyRevitUnknownAssemblyError:
                    logger.debug('Unknown assembly error. Skipping: {0}'.format(fullfilename))
                    continue

    def _find_scriptpanels(self, tabdir, tabname):
        logger.debug('Searching content folder for script panels ...')
        self._find_scriptgroups(tabdir, tabname)
        files = os.listdir(tabdir)
        for fullfilename in files:
            fullfilepath = op.join(tabdir, fullfilename)
            fname, fext = op.splitext(op.basename(fullfilename))
            is_panel_bundled = (op.isdir(fullfilepath) \
                              and not fullfilename.startswith(('.','_')) \
                              and fullfilename.endswith(cfg.PANEL_BUNDLE_POSTFIX))
            is_panel_defined_by_png = cfg.ICON_FILE_FORMAT == fext.lower()
            if is_panel_bundled or is_panel_defined_by_png:
                try:
                    scriptpanel = ScriptPanel(tabdir, fullfilename, tabname, is_panel_bundled)
                    if is_panel_bundled:
                        self._find_scriptgroups(fullfilepath, tabname, bundledPanelName = scriptpanel.panelName)

                    collectedscriptpanels = [(x.panelName, x.tabName) for x in self.pyRevitScriptPanels]
                    if (scriptpanel.panelName, scriptpanel.tabName) not in collectedscriptpanels:
                        scriptpanel.adoptgroups(self.pyRevitScriptGroups)
                        self.pyRevitScriptPanels.append(scriptpanel)
                    else:
                        logger.debug('panel already created and adopted groups.')
                except PyRevitUnknownFileNameFormatError:
                    if fullfilename in [x.iconFileName for x in self.pyRevitScriptCommands]:
                        logger.debug('Skipping script panel file: {0}'.format(fullfilename))
                        continue
                    else:
                        logger.debug('Can not recognize panel name pattern. skipping: {0}'.format(fullfilename))
                        continue

    def _find_scripttabs(self, HOME_DIR):
        logger.debug('Searching for tabs, panels, groups, and scripts...')
        for dirname in os.listdir(HOME_DIR):
            full_path = op.join(HOME_DIR, dirname)
            dir_is_tab = op.isdir(full_path)                                \
                         and not dirname.startswith(('.', '_'))             \
                         and dirname.endswith(cfg.TAB_POSTFIX)
            if dir_is_tab:
                logger.debug('Searching for scripts under: {0}'.format(full_path))
                discovered_tabs_names = {x.tabDirName: x for x in self.pyRevitScriptTabs}
                if dirname not in discovered_tabs_names.keys():
                    sys.path.append(full_path)
                    script_tab = ScriptTab(dirname, full_path)
                    try:
                        self.sessionCache.load_tab(script_tab)
                    except PyRevitCacheError:
                        # I am using a function outside the ScriptTab class to find the panels defined under tab folder
                        # The reason is consistency with how ScriptPanel and ScriptGroup work.
                        # I wanted to perform one file search pass over the tab directory to find all groups and scripts,
                        # and then ask each Panel or Group to adopt their associated groups and scripts respectively.
                        # Otherwise for every discovered panel or group, each class would need to look into the directory
                        # to find groups and scripts. This would increase file operation considerably.
                        # ScriptTab follows the same system for consistency although all panels under the tab folder belong
                        # to that tab. This also allows other develops to add panels to each others tabs.
                        self._find_scriptpanels(full_path, script_tab.tabName)
                        script_tab.adopt_panels(self.pyRevitScriptPanels)
                    logger.debug('Tab found: {0}'.format(script_tab.tabName))
                    self.pyRevitScriptTabs.append(script_tab)
                else:
                    sys.path.append(full_path)
                    script_tab = discovered_tabs_names[dirname]
                    self._find_scriptpanels(full_path, script_tab.tabName)
                    logger.debug('Tab extension found: {0}'.format(script_tab.tabName))
                    script_tab.adopt_panels(self.pyRevitScriptPanels)
            elif op.isdir(full_path) and not dirname.startswith(('.','_')):
                self._find_scripttabs(full_path)
            else:
                continue

