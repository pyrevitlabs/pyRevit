from pyRevit.uielements import *
from pyRevit.cache import PyRevitCache


# todo rename db to something more appropriate. This is the module that will be imported in scripts to access script data
class PyRevitCommandsTree(object):
    def __init__(self):
        self.pyRevitScriptPanels = []
        self.pyRevitScriptGroups = []
        self.pyRevitScriptCommands = []
        self.pyRevitScriptTabs = []

        self.sessionCache = PyRevitCache()

        self._find_scripttabs(cfg.HOME_DIR)
        self._create_reload_button(cfg.LOADER_DIR)

        self.sessionCache.update_cache(self.pyRevitScriptTabs)

    def _create_reload_button(self, loader_dir):
        logger.debug('Creating "Reload Scripts" button...')
        for fname in os.listdir(loader_dir):
            fulltabpath = op.join(loader_dir, fname)
            if not op.isdir(fulltabpath) and cfg.PYREVIT_INIT_SCRIPT_NAME in fname:
                try:
                    cmd = ScriptCommand(loader_dir, fname, cfg.MASTER_TAB_NAME)
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

    def _find_scriptgroups(self, searchdir, tabname, bundled_panel_name=''):
        logger.debug('Searching content folder for script groups ...')
        self._find_scriptcommands(searchdir, tabname)
        files = os.listdir(searchdir)
        for fullfilename in files:
            fullfilepath = op.join(searchdir, fullfilename)
            fname, fext = op.splitext(op.basename(fullfilename))
            if not op.isdir(fullfilepath) and cfg.ICON_FILE_FORMAT == fext.lower():
                try:
                    scriptgroup = ScriptGroup(searchdir, fullfilename, tabname, bundled_panel_name)
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
            is_panel_bundled = (op.isdir(fullfilepath)
                                and not fullfilename.startswith(('.', '_'))
                                and fullfilename.endswith(cfg.PANEL_BUNDLE_POSTFIX))
            is_panel_defined_by_png = cfg.ICON_FILE_FORMAT == fext.lower()
            if is_panel_bundled or is_panel_defined_by_png:
                try:
                    scriptpanel = ScriptPanel(tabdir, fullfilename, tabname, is_panel_bundled)
                    if is_panel_bundled:
                        self._find_scriptgroups(fullfilepath, tabname, bundled_panel_name=scriptpanel.panelName)

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

    # todo create new ui object for pyRevit_Addin and this function should live there
    def _find_scripttabs(self, search_dir):
        logger.debug('Searching for tabs, panels, groups, and scripts...')
        # searching subdirs for .tab directories.
        for dirname in os.listdir(search_dir):
            full_path = op.join(search_dir, dirname)
            # dir is a dir, its name does not start with . or _, and ends with .tab
            dir_is_tab = (op.isdir(full_path)
                          and not dirname.startswith(('.', '_'))
                          and dirname.endswith(cfg.TAB_POSTFIX))
            if dir_is_tab:
                logger.debug('Searching for scripts under: {0}'.format(full_path))
                # creating a dict of tab name:tab object. Contents of any other tab folder that matches an already
                # discovered tab, will be added to the discovered tab to avoid duplication. This feature will also
                # allow the extension developers to add panels and scripts to other pyRevit tabs without modifying
                # their associated repositories.
                discovered_tabs_names = {x.tabDirName: x for x in self.pyRevitScriptTabs}
                # Creates a tab if tab is not already created
                if dirname not in discovered_tabs_names.keys():
                    # appends tab address to sys.path, to allow imports for SmartButtons
                    sys.path.append(full_path)
                    # creating tab object.
                    script_tab = ScriptTab(dirname, full_path)
                    # todo: section below (cache test + panel search) should be inside the tab object
                    try:
                        # asking cache to load the tab
                        self.sessionCache.load_tab(script_tab)
                    except PyRevitCacheError:
                        # if tab is not caches lets search the tab for panels
                        self._find_scriptpanels(full_path, script_tab.tabName)
                        script_tab.adopt_panels(self.pyRevitScriptPanels)
                    logger.debug('Tab found: {0}'.format(script_tab.tabName))
                    # add to list of discovered tab names.
                    self.pyRevitScriptTabs.append(script_tab)
                else:
                    sys.path.append(full_path)
                    script_tab = discovered_tabs_names[dirname]
                    self._find_scriptpanels(full_path, script_tab.tabName)
                    logger.debug('Tab extension found: {0}'.format(script_tab.tabName))
                    script_tab.adopt_panels(self.pyRevitScriptPanels)
            elif op.isdir(full_path) and not dirname.startswith(('.', '_')):
                self._find_scripttabs(full_path)
            else:
                continue
