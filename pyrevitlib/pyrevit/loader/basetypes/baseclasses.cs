using System;
using System.Collections.Generic;
using System.IO;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.Attributes;
using System.Windows.Input;
using System.Windows.Controls;

namespace PyRevitBaseClasses {
    public enum ExtendedAvailabilityTypes {
        ZeroDocuments,
        ActiveView,
        Selection,
    }


    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public abstract class PyRevitCommand : IExternalCommand {
        public string baked_scriptSource = null;
        public string baked_configScriptSource = null;
        public string baked_syspaths = null;
        public string baked_helpSource = null;
        public string baked_cmdName = null;
        public string baked_cmdBundle = null;
        public string baked_cmdExtension = null;
        public string baked_cmdUniqueName = null;
        public bool baked_needsCleanEngine = false;
        public bool baked_needsFullFrameEngine = false;

        // unlike fullframe or clean engine modes, the config script mode is determined at
        // script execution by using a shortcut key combination. This parameter is created to
        // trigger the config script mode when executing a command from a program and not
        // from the Revit user interface.
        public bool ConfigScriptMode = false;

        // this is true by default since commands are normally executed from ui.
        // pyrevit module will set this to false, when manually executing a
        // pyrevit command from python code. (e.g when executing reload after update)
        public bool ExecutedFromUI = true;

        // list of string arguments to be passed to executor.
        // executor then sets the sys.argv with these arguments
        public string[] argumentList = null;


        public PyRevitCommand(string scriptSource,
                              string configScriptSource,
                              string syspaths,
                              string helpSource,
                              string cmdName,
                              string cmdBundle,
                              string cmdExtension,
                              string cmdUniqueName,
                              int needsCleanEngine,
                              int needsFullFrameEngine) {
            baked_scriptSource = scriptSource;
            baked_configScriptSource = configScriptSource;
            baked_syspaths = syspaths;
            baked_helpSource = helpSource;
            baked_cmdName = cmdName;
            baked_cmdBundle = cmdBundle;
            baked_cmdExtension = cmdExtension;
            baked_cmdUniqueName = cmdUniqueName;
            baked_needsCleanEngine = Convert.ToBoolean(needsCleanEngine);
            baked_needsFullFrameEngine = Convert.ToBoolean(needsFullFrameEngine);
        }


        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements) {
            // 1: ---------------------------------------------------------------------------------------------------------------------------------------------
            #region Processing modifier keys
            // Processing modifier keys
            // Default script is the main script unless it is changed by modifier buttons
            var _script = baked_scriptSource;

            bool _refreshEngine = false;
            bool _configScriptMode = false;
            bool _forcedDebugMode = false;

            bool ALT = Keyboard.IsKeyDown(Key.LeftAlt) || Keyboard.IsKeyDown(Key.RightAlt);
            bool SHIFT = Keyboard.IsKeyDown(Key.LeftShift) || Keyboard.IsKeyDown(Key.RightShift);
            bool CTRL = Keyboard.IsKeyDown(Key.LeftCtrl) || Keyboard.IsKeyDown(Key.RightCtrl);
            bool WIN = Keyboard.IsKeyDown(Key.LWin) || Keyboard.IsKeyDown(Key.RWin);


            // If Ctrl+Alt+Shift clicking on the tool run in clean engine
            if (CTRL && ALT && SHIFT) {
                _refreshEngine = true;
            }

            // If Alt+Shift clicking on button, open the context menu with options.
            else if (SHIFT && WIN) {
                // start creating context menu
                ContextMenu pyRevitCmdContextMenu = new ContextMenu();

                // menu item to open help url if exists
                if (baked_helpSource != null && baked_helpSource != "") {
                    MenuItem openHelpSource = new MenuItem();
                    openHelpSource.Header = "Open Help";
                    openHelpSource.ToolTip = baked_helpSource;
                    openHelpSource.Click += delegate { System.Diagnostics.Process.Start(baked_helpSource); };
                    pyRevitCmdContextMenu.Items.Add(openHelpSource);
                }

                // use a disabled menu item to show if the command requires clean engine
                MenuItem cleanEngineStatus = new MenuItem();
                cleanEngineStatus.Header = string.Format("Requests Clean Engine: {0}", baked_needsCleanEngine ? "Yes" : "No");
                cleanEngineStatus.IsEnabled = false;
                pyRevitCmdContextMenu.Items.Add(cleanEngineStatus);

                // use a disabled menu item to show if the command requires full frame engine
                MenuItem fullFrameEngineStatus = new MenuItem();
                fullFrameEngineStatus.Header = string.Format("Requests FullFrame Engine: {0}", baked_needsFullFrameEngine ? "Yes" : "No");
                fullFrameEngineStatus.IsEnabled = false;
                pyRevitCmdContextMenu.Items.Add(fullFrameEngineStatus);

                // menu item to copy script path to clipboard
                MenuItem copyScriptPath = new MenuItem();
                copyScriptPath.Header = "Copy Script Path";
                copyScriptPath.ToolTip = _script;
                copyScriptPath.Click += delegate { System.Windows.Forms.Clipboard.SetText(_script); };
                pyRevitCmdContextMenu.Items.Add(copyScriptPath);

                // menu item to copy config script path to clipboard, if exists
                if (baked_configScriptSource != null && baked_configScriptSource != "") {
                    MenuItem copyAltScriptPath = new MenuItem();
                    copyAltScriptPath.Header = "Copy Config Script Path";
                    copyAltScriptPath.ToolTip = baked_configScriptSource;
                    copyAltScriptPath.Click += delegate { System.Windows.Forms.Clipboard.SetText(baked_configScriptSource); };
                    pyRevitCmdContextMenu.Items.Add(copyAltScriptPath);
                }

                // menu item to copy bundle path to clipboard
                var bundlePath = Path.GetDirectoryName(_script);
                MenuItem copyBundlePath = new MenuItem();
                copyBundlePath.Header = "Copy Bundle Path";
                copyBundlePath.ToolTip = bundlePath;
                copyBundlePath.Click += delegate { System.Windows.Forms.Clipboard.SetText(bundlePath); };
                pyRevitCmdContextMenu.Items.Add(copyBundlePath);

                // menu item to copy command unique name (assigned by pyRevit) to clipboard
                MenuItem copyUniqueName = new MenuItem();
                copyUniqueName.Header = string.Format("Copy Unique Id ({0})", baked_cmdUniqueName);
                copyUniqueName.Click += delegate { System.Windows.Forms.Clipboard.SetText(baked_cmdUniqueName); };
                pyRevitCmdContextMenu.Items.Add(copyUniqueName);

                // menu item to copy ;-separated sys paths to clipboard
                // Example: "path1;path2;path3"
                MenuItem copySysPaths = new MenuItem();
                copySysPaths.Header = "Copy Sys Paths";
                copySysPaths.Click += delegate { System.Windows.Forms.Clipboard.SetText(baked_syspaths.Replace(new string(ExternalConfig.defaultsep, 1), "\r\n")); };
                pyRevitCmdContextMenu.Items.Add(copySysPaths);

                // menu item to copy help url
                MenuItem copyHelpSource = new MenuItem();
                copyHelpSource.Header = "Copy Help Url";
                copyHelpSource.ToolTip = baked_helpSource;
                copyHelpSource.Click += delegate { System.Windows.Forms.Clipboard.SetText(baked_helpSource.Replace(new string(ExternalConfig.defaultsep, 1), "\r\n")); };
                pyRevitCmdContextMenu.Items.Add(copyHelpSource);
                if (baked_helpSource == null || baked_helpSource == string.Empty)
                    copyHelpSource.IsEnabled = false;

                // open the menu
                pyRevitCmdContextMenu.IsOpen = true;

                return Result.Succeeded;
            }

            // If Ctrl+Shift clicking on button, run the script in debug mode and run config script instead.
            else if (CTRL && (SHIFT || ConfigScriptMode)) {
                _script = baked_configScriptSource;
                _configScriptMode = true;
                _forcedDebugMode = true;
            }

            // If Alt clicking on button, open the script in explorer and return.
            else if (ALT) {
                // combine the arguments together
                // it doesn't matter if there is a space after ','
                string argument = "/select, \"" + _script + "\"";

                System.Diagnostics.Process.Start("explorer.exe", argument);
                return Result.Succeeded;
            }

            // If Shift clicking on button, run config script instead
            else if (SHIFT || ConfigScriptMode) {
                _script = baked_configScriptSource;
                _configScriptMode = true;
            }

            // If Ctrl clicking on button, set forced debug mode.
            else if (CTRL) {
                _forcedDebugMode = true;
            }
            #endregion

            // 2: ---------------------------------------------------------------------------------------------------------------------------------------------
            #region Setup pyRevit Command Runtime
            var pyrvtCmdRuntime = new PyRevitCommandRuntime(cmdData: commandData,
                                                            elements: elements,
                                                            scriptSource: baked_scriptSource,
                                                            configScriptSource: baked_configScriptSource,
                                                            syspaths: baked_syspaths,
                                                            arguments: argumentList,
                                                            helpSource: baked_helpSource,
                                                            cmdName: baked_cmdName,
                                                            cmdBundle: baked_cmdBundle,
                                                            cmdExtension: baked_cmdExtension,
                                                            cmdUniqueName: baked_cmdUniqueName,
                                                            needsCleanEngine: baked_needsCleanEngine,
                                                            needsFullFrameEngine: baked_needsFullFrameEngine,
                                                            refreshEngine: _refreshEngine,
                                                            forcedDebugMode: _forcedDebugMode,
                                                            configScriptMode: _configScriptMode,
                                                            executedFromUI: ExecutedFromUI);
            #endregion

            // 3: ---------------------------------------------------------------------------------------------------------------------------------------------
            #region Execute and log results
            // Executing the script and logging the results
            // Get script executor and Execute the script
            pyrvtCmdRuntime.ExecutionResult = ScriptExecutor.ExecuteScript(ref pyrvtCmdRuntime);

            // Log results
            ScriptTelemetry.LogTelemetryRecord(pyrvtCmdRuntime.MakeTelemetryRecord());

            // GC cleanups
            var re = pyrvtCmdRuntime.ExecutionResult;
            pyrvtCmdRuntime.Dispose();
            pyrvtCmdRuntime = null;

            // Return results to Revit. Don't report errors since we don't want Revit popup with error results
            if (re == 0)
                return Result.Succeeded;
            else
                return Result.Cancelled;
            #endregion
        }
    }


    public abstract class PyRevitCommandExtendedAvail : IExternalCommandAvailability {
        // category name separator for comparisons
        const string SEP = "|";

        // is any selection required?
        private bool selectionRequired = false;

        // list of acceptable view types
        private HashSet<ViewType> _activeViewTypes = new HashSet<ViewType>();

        // category comparison string (e.g. wallsdoors)
        private string _contextCatNameHash = null;
        // builtin category comparison list
        private HashSet<int> _contextCatIdsHash = new HashSet<int>();

        public PyRevitCommandExtendedAvail(string contextString) {
            // NOTE:
            // docs have builtin categories
            // docs might have custom categories with non-english names
            // the compare mechanism is providing methods to cover both conditions
            // compare mechanism stores integer ids for builtin categories
            // compare mechanism stores strings for custom category names
            //   avail methods don't have access to doc object so the category names must be stored as string

            // get the tokens out of the string (it could only have one token)
            // contextString in a ;-separated list of tokens
            List<string> contextTokens = new List<string>();
            foreach (string contextToken in contextString.Split(ExternalConfig.defaultsep))
                contextTokens.Add(contextToken.ToLower());
            // keep them sorted for comparison
            contextTokens.Sort();

            // first process the tokens for custom directives
            // remove processed tokens and move to next step
            foreach (string token in new List<string>(contextTokens)) {
                switch (token.ToLower()) {
                    // selection token requires selected elements
                    case "selection":
                        selectionRequired = true;
                        contextTokens.Remove(token); break;
                    // active-* tokens require a certain type of active view
                    case "active-drafting-view":
                        _activeViewTypes.Add(ViewType.DraftingView);
                        contextTokens.Remove(token); break;
                    case "active-detail-view":
                        _activeViewTypes.Add(ViewType.Detail);
                        contextTokens.Remove(token); break;
                    case "active-plan-view":
                        _activeViewTypes.Add(ViewType.FloorPlan);
                        _activeViewTypes.Add(ViewType.CeilingPlan);
                        _activeViewTypes.Add(ViewType.AreaPlan);
                        _activeViewTypes.Add(ViewType.EngineeringPlan);
                        contextTokens.Remove(token); break;
                    case "active-floor-plan":
                        _activeViewTypes.Add(ViewType.FloorPlan);
                        contextTokens.Remove(token); break;
                    case "active-rcp-plan":
                        _activeViewTypes.Add(ViewType.CeilingPlan);
                        contextTokens.Remove(token); break;
                    case "active-structural-plan":
                        _activeViewTypes.Add(ViewType.EngineeringPlan);
                        contextTokens.Remove(token); break;
                    case "active-area-plan":
                        _activeViewTypes.Add(ViewType.AreaPlan);
                        contextTokens.Remove(token); break;
                    case "active-elevation-view":
                        _activeViewTypes.Add(ViewType.Elevation);
                        contextTokens.Remove(token); break;
                    case "active-section-view":
                        _activeViewTypes.Add(ViewType.Section);
                        contextTokens.Remove(token); break;
                    case "active-3d-view":
                        _activeViewTypes.Add(ViewType.ThreeD);
                        contextTokens.Remove(token); break;
                    case "active-sheet":
                        _activeViewTypes.Add(ViewType.DrawingSheet);
                        contextTokens.Remove(token); break;
                    case "active-legend":
                        _activeViewTypes.Add(ViewType.Legend);
                        contextTokens.Remove(token); break;
                    case "active-schedule":
                        _activeViewTypes.Add(ViewType.PanelSchedule);
                        _activeViewTypes.Add(ViewType.ColumnSchedule);
                        _activeViewTypes.Add(ViewType.Schedule);
                        contextTokens.Remove(token); break;
                    case "active-panel-schedule":
                        _activeViewTypes.Add(ViewType.PanelSchedule);
                        contextTokens.Remove(token); break;
                    case "active-column-schedule":
                        _activeViewTypes.Add(ViewType.ColumnSchedule);
                        contextTokens.Remove(token); break;
                }
            }

            // first pass processed and removed the processed tokens
            // second, process tokens for builtin categories
            // if any tokens left
            foreach (string token in new List<string>(contextTokens)) {
                BuiltInCategory bic = BuiltInCategory.INVALID;
                if (Enum.TryParse(token, true, out bic) && bic != 0 && bic != BuiltInCategory.INVALID) {
                    _contextCatIdsHash.Add((int)bic);
                    contextTokens.Remove(token);
                }
            }

            // assume that the remaining tokens are category names and create a comparison string
            _contextCatNameHash = string.Join(SEP, contextTokens);
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories) {
            // check selection
            if (selectionRequired && selectedCategories.IsEmpty)
                return false;

            try {
#if (REVIT2013 || REVIT2014)
                // check active views
                if (_activeViewTypes.Count > 0) {
                    if (uiApp != null && uiApp.ActiveUIDocument != null
                        && !_activeViewTypes.Contains(uiApp.ActiveUIDocument.ActiveView.ViewType))
                        return false;
                }
#else
                // check active views
                if (_activeViewTypes.Count > 0) {
                    if (uiApp != null && uiApp.ActiveUIDocument != null
                        && !_activeViewTypes.Contains(uiApp.ActiveUIDocument.ActiveGraphicalView.ViewType))
                        return false;
                }
#endif


                // the rest are category comparisons so if no categories are selected return false
                if (selectedCategories.IsEmpty)
                    return false;

                // make a hash of selected category ids
                var selectedCatIdsHash = new HashSet<int>();
                foreach (Category rvt_cat in selectedCategories)
                    selectedCatIdsHash.Add(rvt_cat.Id.IntegerValue);

                // make a hash of selected category names
                var selectedCategoryNames = new List<string>();
                foreach (Category rvt_cat in selectedCategories)
                    selectedCategoryNames.Add(rvt_cat.Name.ToLower());
                selectedCategoryNames.Sort();
                string selectedCatNameHash = string.Join(SEP, selectedCategoryNames);

                // user might have added a combination of category names and builtin categories
                // test each possibility
                // if both builtin categories and category names are specified
                if (_contextCatIdsHash.Count > 0 && _contextCatNameHash != null) {
                    // test select inclusion in context (test selected is not bigger than context)
                    foreach(Category rvt_cat in selectedCategories) {
                        if (!_contextCatIdsHash.Contains(rvt_cat.Id.IntegerValue)
                                && !_contextCatNameHash.Contains(rvt_cat.Name.ToLower()))
                            return false;
                    }

                    // test context inclusion in selected (test context is not bigger than selected)
                    foreach (int catId in _contextCatIdsHash)
                        if (!selectedCatIdsHash.Contains(catId))
                            return false;
                    foreach (string catName in _contextCatNameHash.Split(SEP.ToCharArray()))
                        if (!selectedCatNameHash.Contains(catName))
                            return false;
                }
                // if only builtin categories
                else if (_contextCatIdsHash.Count > 0 && _contextCatNameHash == null) {
                    if (!_contextCatIdsHash.SetEquals(selectedCatIdsHash))
                        return false;
                }
                // if only category names
                else if (_contextCatIdsHash.Count == 0 && _contextCatNameHash != null) {
                    if (selectedCatNameHash != _contextCatNameHash)
                        return false;
                }

                return true;
            }
            // say no if any errors occured, otherwise Revit will not call this method again if exceptions
            // are bubbled up
            catch { return false; }
        }
    }


    public abstract class PyRevitCommandSelectionAvail : IExternalCommandAvailability {
        private string _categoryName = "";

        public PyRevitCommandSelectionAvail(string contextString) {
            _categoryName = contextString;
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories) {
            if (selectedCategories.IsEmpty)
                return false;

            return true;
        }
    }


    public abstract class PyRevitCommandDefaultAvail : IExternalCommandAvailability {
        public PyRevitCommandDefaultAvail() {
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories) {
            return true;
        }
    }

}

