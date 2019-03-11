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
        public string baked_alternateScriptSource = null;
        public string baked_syspaths = null;
        public string baked_helpSource = null;
        public string baked_cmdName = null;
        public string baked_cmdBundle = null;
        public string baked_cmdExtension = null;
        public string baked_cmdUniqueName = null;
        public bool baked_needsCleanEngine = false;
        public bool baked_needsFullFrameEngine = false;

        // unlike fullframe or clean engine modes, the alternate script mode is determined at
        // script execution by using a shortcut key combination. This parameter is created to
        // trigger the alternate script mode when executing a command from a program and not
        // from the Revit user interface.
        public bool altScriptModeOverride = false;

        // this is true by default since commands are normally executed from ui.
        // pyrevit module will set this to false, when manually executing a
        // pyrevit command from python code. (e.g when executing reload after update)
        public bool executedFromUI = true;

        // list of string arguments to be passed to executor.
        // executor then sets the sys.argv with these arguments
        public string[] argumentList = null;


        public PyRevitCommand(string scriptSource,
                              string alternateScriptSource,
                              string syspaths,
                              string helpSource,
                              string cmdName,
                              string cmdBundle,
                              string cmdExtension,
                              string cmdUniqueName,
                              int needsCleanEngine,
                              int needsFullFrameEngine) {
            baked_scriptSource = scriptSource;
            baked_alternateScriptSource = alternateScriptSource;
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
            bool _altScriptMode = false;
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

                // menu item to copy alternate script path to clipboard, if exists
                if (baked_alternateScriptSource != null && baked_alternateScriptSource != "") {
                    MenuItem copyAltScriptPath = new MenuItem();
                    copyAltScriptPath.Header = "Copy Alternate Script Path";
                    copyAltScriptPath.ToolTip = baked_alternateScriptSource;
                    copyAltScriptPath.Click += delegate { System.Windows.Forms.Clipboard.SetText(baked_alternateScriptSource); };
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
                copySysPaths.Click += delegate { System.Windows.Forms.Clipboard.SetText(baked_syspaths.Replace(";", "\r\n")); };
                pyRevitCmdContextMenu.Items.Add(copySysPaths);

                // menu item to copy help url
                MenuItem copyHelpSource = new MenuItem();
                copyHelpSource.Header = "Copy Help Url";
                copyHelpSource.ToolTip = baked_helpSource;
                copyHelpSource.Click += delegate { System.Windows.Forms.Clipboard.SetText(baked_helpSource.Replace(";", "\r\n")); };
                pyRevitCmdContextMenu.Items.Add(copyHelpSource);
                if (baked_helpSource == null || baked_helpSource == string.Empty)
                    copyHelpSource.IsEnabled = false;

                // open the menu
                pyRevitCmdContextMenu.IsOpen = true;

                return Result.Succeeded;
            }

            // If Ctrl+Shift clicking on button, run the script in debug mode and run config script instead.
            else if (CTRL && (SHIFT || altScriptModeOverride)) {
                _script = baked_alternateScriptSource;
                _altScriptMode = true;
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
            else if (SHIFT || altScriptModeOverride) {
                _script = baked_alternateScriptSource;
                _altScriptMode = true;
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
                                                            alternateScriptSource: baked_alternateScriptSource,
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
                                                            altScriptMode: _altScriptMode,
                                                            executedFromUI: executedFromUI);
            #endregion

            // 3: ---------------------------------------------------------------------------------------------------------------------------------------------
            #region Execute and log results
            // Executing the script and logging the results

            // Get script executor and Execute the script
            var executor = new ScriptExecutor();
            pyrvtCmdRuntime.ExecutionResult = executor.ExecuteScript(ref pyrvtCmdRuntime);

            // Log results
            ScriptUsageLogger.LogUsage(pyrvtCmdRuntime.MakeLogEntry());

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
        private string originalContextString;
        private bool selectionRequired = false;                                 // is any selection required?
        private HashSet<ViewType> activeViewTypes = new HashSet<ViewType>();    // list of acceptable view types
        private string _contextCatNameCompareString = null;                     // category comparison string (e.g. wallsdoors)

        public PyRevitCommandExtendedAvail(string contextString) {
            // keep a backup
            originalContextString = contextString;

            // get the tokens out of the string (it could only have one token)
            List<string> contextTokens = new List<string>();
            foreach (string catName in contextString.Split(';'))
                contextTokens.Add(catName.ToLower());

            // go thru the tokens and extract the custom (non-element-category) tokens
            List<string> contextTokensCopy = new List<string>(contextTokens);
            foreach (string token in contextTokensCopy) {
                switch (token.ToLower()) {
                    case "selection":
                        selectionRequired = true;
                        contextTokens.Remove(token); break;
                    case "active-drafting-view":
                        activeViewTypes.Add(ViewType.DraftingView);
                        contextTokens.Remove(token); break;
                    case "active-detail-view":
                        activeViewTypes.Add(ViewType.Detail);
                        contextTokens.Remove(token); break;
                    case "active-plan-view":
                        activeViewTypes.Add(ViewType.FloorPlan);
                        activeViewTypes.Add(ViewType.CeilingPlan);
                        activeViewTypes.Add(ViewType.AreaPlan);
                        activeViewTypes.Add(ViewType.EngineeringPlan);
                        contextTokens.Remove(token); break;
                    case "active-floor-plan":
                        activeViewTypes.Add(ViewType.FloorPlan);
                        contextTokens.Remove(token); break;
                    case "active-rcp-plan":
                        activeViewTypes.Add(ViewType.CeilingPlan);
                        contextTokens.Remove(token); break;
                    case "active-structural-plan":
                        activeViewTypes.Add(ViewType.EngineeringPlan);
                        contextTokens.Remove(token); break;
                    case "active-area-plan":
                        activeViewTypes.Add(ViewType.AreaPlan);
                        contextTokens.Remove(token); break;
                    case "active-elevation-view":
                        activeViewTypes.Add(ViewType.Elevation);
                        contextTokens.Remove(token); break;
                    case "active-section-view":
                        activeViewTypes.Add(ViewType.Section);
                        contextTokens.Remove(token); break;
                    case "active-3d-view":
                        activeViewTypes.Add(ViewType.ThreeD);
                        contextTokens.Remove(token); break;
                    case "active-sheet":
                        activeViewTypes.Add(ViewType.DrawingSheet);
                        contextTokens.Remove(token); break;
                    case "active-legend":
                        activeViewTypes.Add(ViewType.Legend);
                        contextTokens.Remove(token); break;
                    case "active-schedule":
                        activeViewTypes.Add(ViewType.PanelSchedule);
                        activeViewTypes.Add(ViewType.ColumnSchedule);
                        activeViewTypes.Add(ViewType.Schedule);
                        contextTokens.Remove(token); break;
                    case "active-panel-schedule":
                        activeViewTypes.Add(ViewType.PanelSchedule);
                        contextTokens.Remove(token); break;
                    case "active-column-schedule":
                        activeViewTypes.Add(ViewType.ColumnSchedule);
                        contextTokens.Remove(token); break;
                }
            }

            // assume that the remaining tokens are category names and create a comparison string
            if(contextTokens.Count > 0) {
                contextTokens.Sort();
                _contextCatNameCompareString = string.Join("", contextTokens);
            }
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories) {
            // check selection
            if (selectionRequired && selectedCategories.IsEmpty)
                return false;

            // check active views
            if (activeViewTypes.Count > 0) {
                if (uiApp != null && uiApp.ActiveUIDocument != null
                    && !activeViewTypes.Contains(uiApp.ActiveUIDocument.ActiveGraphicalView.ViewType))
                    return false;
            }

            // check element categories
            if (_contextCatNameCompareString != null) {
                if (selectedCategories.IsEmpty)
                    return false;

                try {
                    var selectedCategoryNames = new List<string>();
                    foreach (Category rvt_cat in selectedCategories)
                        selectedCategoryNames.Add(rvt_cat.Name.ToLower());

                    selectedCategoryNames.Sort();
                    string selectedCatNameCompareString = string.Join("", selectedCategoryNames);

                    if (selectedCatNameCompareString != _contextCatNameCompareString)
                        return false;
                }
                catch (Exception) {
                    return false;
                }
            }

            return true;
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

