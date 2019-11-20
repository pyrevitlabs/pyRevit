using System;
using System.Collections.Generic;
using System.IO;
using System.Windows.Input;
using System.Windows.Controls;

using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.Attributes;

namespace PyRevitLabs.PyRevit.Runtime {
    public class CommandTypeExecConfigs {
        // unlike fullframe or clean engine modes, the config script mode is determined at
        // script execution by using a shortcut key combination. This parameter is created to
        // trigger the config script mode when executing a command from a program and not
        // from the Revit user interface.
        public bool UseConfigScript = false;

        // this is true by default since commands are normally executed from ui.
        // pyrevit module will set this to false, when manually executing a
        // pyrevit command from python code. (e.g when executing reload after update)
        public bool MimicExecFromUI = true;
    }


    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public abstract class ScriptCommand : IExternalCommand {
        
        public ScriptData ScriptData;
        public ScriptRuntimeConfigs ScriptRuntimeConfigs;

        public CommandTypeExecConfigs ExecConfigs = new CommandTypeExecConfigs();

        public ScriptCommand(
                string scriptSource,
                string configScriptSource,
                string searchPaths,
                string arguments,
                string helpSource,
                string tooltip,
                string cmdName,
                string cmdBundle,
                string cmdExtension,
                string cmdUniqueName,
                string cmdControlId,
                string engineCfgs) {
            ScriptData = new ScriptData {
                ScriptPath = scriptSource,
                ConfigScriptPath = configScriptSource,
                CommandUniqueId = cmdUniqueName,
                CommandControlId = cmdControlId,
                CommandName = cmdName,
                CommandBundle = cmdBundle,
                CommandExtension = cmdExtension,
                HelpSource = helpSource,
                Tooltip = tooltip,
            };

            // build search paths
            List<string> searchPathList = new List<string>();
            if (searchPaths != null && searchPaths != string.Empty)
                searchPathList = new List<string>(searchPaths.Split(Path.PathSeparator));

            // build arguments
            List<string> argumentList = new List<string>();
            if (arguments != null && arguments != string.Empty)
                argumentList = new List<string>(arguments.Split(Path.PathSeparator));

            ScriptRuntimeConfigs = new ScriptRuntimeConfigs {
                SearchPaths = searchPathList,
                Arguments = argumentList,
                EngineConfigs = engineCfgs,
            };
        }


        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements) {
            // 1: ----------------------------------------------------------------------------------------------------
            #region Processing modifier keys
            // Processing modifier keys

            bool refreshEngine = false;
            bool configScriptMode = false;
            bool forcedDebugMode = false;

            bool ALT = Keyboard.IsKeyDown(Key.LeftAlt) || Keyboard.IsKeyDown(Key.RightAlt);
            bool SHIFT = Keyboard.IsKeyDown(Key.LeftShift) || Keyboard.IsKeyDown(Key.RightShift);
            bool CTRL = Keyboard.IsKeyDown(Key.LeftCtrl) || Keyboard.IsKeyDown(Key.RightCtrl);
            bool WIN = Keyboard.IsKeyDown(Key.LWin) || Keyboard.IsKeyDown(Key.RWin);


            // If Ctrl+Alt+Shift clicking on the tool run in clean engine
            if (CTRL && ALT && SHIFT) {
                refreshEngine = true;
            }

            // If Alt+Shift clicking on button, open the context menu with options.
            else if (SHIFT && WIN) {
                // start creating context menu
                ContextMenu pyRevitCmdContextMenu = new ContextMenu();

                // menu item to open help url if exists
                if (ScriptData.HelpSource != null && ScriptData.HelpSource != "") {
                    MenuItem openHelpSource = new MenuItem();
                    openHelpSource.Header = "Open Help";
                    openHelpSource.ToolTip = ScriptData.HelpSource;
                    openHelpSource.Click += delegate { System.Diagnostics.Process.Start(ScriptData.HelpSource); };
                    pyRevitCmdContextMenu.Items.Add(openHelpSource);
                }

                // menu item to copy script path to clipboard
                MenuItem copyScriptPath = new MenuItem();
                copyScriptPath.Header = "Copy Script Path";
                copyScriptPath.ToolTip = ScriptData.ScriptPath;
                copyScriptPath.Click += delegate { System.Windows.Forms.Clipboard.SetText(ScriptData.ScriptPath); };
                pyRevitCmdContextMenu.Items.Add(copyScriptPath);

                // menu item to copy config script path to clipboard, if exists
                if (ScriptData.ConfigScriptPath != null && ScriptData.ConfigScriptPath != "") {
                    MenuItem copyAltScriptPath = new MenuItem();
                    copyAltScriptPath.Header = "Copy Config Script Path";
                    copyAltScriptPath.ToolTip = ScriptData.ConfigScriptPath;
                    copyAltScriptPath.Click += delegate { System.Windows.Forms.Clipboard.SetText(ScriptData.ConfigScriptPath); };
                    pyRevitCmdContextMenu.Items.Add(copyAltScriptPath);
                }

                // menu item to copy bundle path to clipboard
                var bundlePath = Path.GetDirectoryName(ScriptData.ScriptPath);
                MenuItem copyBundlePath = new MenuItem();
                copyBundlePath.Header = "Copy Bundle Path";
                copyBundlePath.ToolTip = bundlePath;
                copyBundlePath.Click += delegate { System.Windows.Forms.Clipboard.SetText(bundlePath); };
                pyRevitCmdContextMenu.Items.Add(copyBundlePath);

                // menu item to copy command unique name (assigned by pyRevit) to clipboard
                MenuItem copyUniqueName = new MenuItem();
                copyUniqueName.Header = "Copy Unique Id";
                copyUniqueName.ToolTip = ScriptData.CommandUniqueId;
                copyUniqueName.Click += delegate { System.Windows.Forms.Clipboard.SetText(ScriptData.CommandUniqueId); };
                pyRevitCmdContextMenu.Items.Add(copyUniqueName);

                // menu item to copy command unique name (assigned by pyRevit) to clipboard
                MenuItem copyControlIdName = new MenuItem();
                copyControlIdName.Header = "Copy Control Id";
                copyControlIdName.ToolTip = ScriptData.CommandControlId;
                copyControlIdName.Click += delegate { System.Windows.Forms.Clipboard.SetText(ScriptData.CommandControlId); };
                pyRevitCmdContextMenu.Items.Add(copyControlIdName);

                // menu item to copy ;-separated sys paths to clipboard
                // Example: "path1;path2;path3"
                MenuItem copySysPaths = new MenuItem();
                string sysPathsText = string.Join(Environment.NewLine, ScriptRuntimeConfigs.SearchPaths);
                copySysPaths.Header = "Copy Sys Paths";
                copySysPaths.ToolTip = sysPathsText;
                copySysPaths.Click += delegate { System.Windows.Forms.Clipboard.SetText(sysPathsText); };
                pyRevitCmdContextMenu.Items.Add(copySysPaths);

                // menu item to copy ;-separated arguments to clipboard
                // Example: "path1;path2;path3"
                MenuItem copyArguments = new MenuItem();
                string argumentsText = string.Join(Environment.NewLine, ScriptRuntimeConfigs.Arguments);
                copyArguments.Header = "Copy Arguments";
                copyArguments.ToolTip = argumentsText;
                copyArguments.Click += delegate { System.Windows.Forms.Clipboard.SetText(argumentsText); };
                pyRevitCmdContextMenu.Items.Add(copyArguments);
                if (argumentsText == null || argumentsText == string.Empty)
                    copyArguments.IsEnabled = false;

                // menu item to copy engine configs
                MenuItem copyEngineConfigs = new MenuItem();
                string engineCfgs = ScriptRuntimeConfigs.EngineConfigs;
                copyEngineConfigs.Header = "Copy Engine Configs";
                copyEngineConfigs.ToolTip = engineCfgs;
                copyEngineConfigs.Click += delegate { System.Windows.Forms.Clipboard.SetText(engineCfgs); };
                pyRevitCmdContextMenu.Items.Add(copyEngineConfigs);
                if (engineCfgs == null || engineCfgs == string.Empty)
                    copyEngineConfigs.IsEnabled = false;

                // menu item to copy help url
                MenuItem copyHelpSource = new MenuItem();
                copyHelpSource.Header = "Copy Help Url";
                copyHelpSource.ToolTip = ScriptData.HelpSource;
                copyHelpSource.Click += delegate { System.Windows.Forms.Clipboard.SetText(ScriptData.HelpSource); };
                pyRevitCmdContextMenu.Items.Add(copyHelpSource);
                if (ScriptData.HelpSource == null || ScriptData.HelpSource == string.Empty)
                    copyHelpSource.IsEnabled = false;

                // open the menu
                pyRevitCmdContextMenu.IsOpen = true;

                return Result.Succeeded;
            }

            // If Ctrl+Shift clicking on button, run the script in debug mode and run config script instead.
            else if (CTRL && (SHIFT || ExecConfigs.UseConfigScript)) {
                configScriptMode = true;
                forcedDebugMode = true;
            }

            // If Alt clicking on button, open the script in explorer and return.
            else if (SHIFT && ALT) {
                // combine the arguments together
                // it doesn't matter if there is a space after ','
                if (ScriptExecutor.EnsureTargetScript(ScriptData.ConfigScriptPath)) {
                    string argument = "/select, \"" + ScriptData.ConfigScriptPath + "\"";

                    System.Diagnostics.Process.Start("explorer.exe", argument);
                }
                return Result.Succeeded;
            }
     
            else if (ALT) {
                // combine the arguments together
                // it doesn't matter if there is a space after ','
                if (ScriptExecutor.EnsureTargetScript(ScriptData.ScriptPath)) {
                    string argument = "/select, \"" + ScriptData.ScriptPath + "\"";

                    System.Diagnostics.Process.Start("explorer.exe", argument);
                }
                return Result.Succeeded;
            }

            // If Shift clicking on button, run config script instead
            else if (SHIFT || ExecConfigs.UseConfigScript) {
                configScriptMode = true;
            }

            // If Ctrl clicking on button, set forced debug mode.
            else if (CTRL) {
                forcedDebugMode = true;
            }
            #endregion

            // 2: ----------------------------------------------------------------------------------------------------
            #region Setup pyRevit Command Runtime Configs
            // fill in the rest of runtime info
            ScriptRuntimeConfigs.CommandData = commandData;
            ScriptRuntimeConfigs.SelectedElements = elements;
            ScriptRuntimeConfigs.RefreshEngine = refreshEngine;
            ScriptRuntimeConfigs.ConfigMode = configScriptMode;
            ScriptRuntimeConfigs.DebugMode = forcedDebugMode;
            ScriptRuntimeConfigs.ExecutedFromUI = ExecConfigs.MimicExecFromUI;

            #endregion

            // 3: ----------------------------------------------------------------------------------------------------
            #region Execute and log results
            // Executing the script and logging the results
            // Get script executor and Execute the script
            int result = ScriptExecutor.ExecuteScript(
                ScriptData,
                ScriptRuntimeConfigs,
                new ScriptExecutorConfigs {
                    SendTelemetry = true
                }
                );

            // Return results to Revit. Don't report errors since we don't want Revit popup with error results
            if (result == 0)
                return Result.Succeeded;
            else
                return Result.Cancelled;
            #endregion
        }
    }


    public abstract class ScriptCommandExtendedAvail : IExternalCommandAvailability {
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

        public ScriptCommandExtendedAvail(string contextString) {
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
            foreach (string contextToken in contextString.Split(Path.PathSeparator))
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


    public abstract class ScriptCommandSelectionAvail : IExternalCommandAvailability {
        private string _categoryName = "";

        public ScriptCommandSelectionAvail(string contextString) {
            _categoryName = contextString;
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories) {
            if (selectedCategories.IsEmpty)
                return false;

            return true;
        }
    }


    public abstract class ScriptCommandZeroDocAvail : IExternalCommandAvailability {
        public ScriptCommandZeroDocAvail() {
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories) {
            return true;
        }
    }
}

