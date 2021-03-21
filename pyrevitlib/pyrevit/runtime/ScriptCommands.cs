using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
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
                string cmdContext,
                string engineCfgs) {
            ScriptData = new ScriptData {
                ScriptPath = scriptSource,
                ConfigScriptPath = configScriptSource,
                CommandUniqueId = cmdUniqueName,
                CommandControlId = cmdControlId,
                CommandName = cmdName,
                CommandBundle = cmdBundle,
                CommandExtension = cmdExtension,
                CommandContext = cmdContext,
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

                // menu item to copy command context strings
                MenuItem copyContext = new MenuItem();
                copyContext.IsEnabled = !string.IsNullOrEmpty(ScriptData.CommandContext);
                copyContext.Header = "Copy Context Condition";
                copyContext.ToolTip = ScriptData.CommandContext;
                copyContext.Click += delegate {
                    try {
                        var contextCondition = ScriptCommandExtendedAvail.FromContextDefinition(ScriptData.CommandContext);
                        System.Windows.Forms.Clipboard.SetText(contextCondition.ToString());
                    }
                    catch (Exception ex) {
                        System.Windows.Forms.Clipboard.SetText(
                            $"Error occured while compiling context \"{ScriptData.CommandContext}\" | {ex.Message}"
                            );
                    }
                };
                pyRevitCmdContextMenu.Items.Add(copyContext);

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
            var env = new EnvDictionary();
            int result = ScriptExecutor.ExecuteScript(
                ScriptData,
                ScriptRuntimeConfigs,
                new ScriptExecutorConfigs {
                    SendTelemetry = env.TelemetryState
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
        // separators
        const char CONTEXT_CONDITION_ALL_SEP = '&';
        const char CONTEXT_CONDITION_ANY_SEP = '|';
        const char CONTEXT_CONDITION_EXACT_SEP = ';';
        const char CONTEXT_CONDITION_NOT = '!';

        // category name separator for comparisons
        const string SEP = "|";

        public ScriptCommandExtendedAvail(string contextString) {
            ContextCondition = FromContextDefinition(contextString);
        }

        public static Condition FromContextDefinition(string contextString) {
            /*
            * Context string format is a list of tokens joined by either & or | but not both
            * and grouped inside (). Groups can also be joined by either & or | but not both
            * Context strings can not be nested
            * Examples: a,b,c are tokens
            * (a)
            * (a&b&c)
            * (a|b|c)
            * (a|b|c)&(a&b&c)
            * (a|b|c)|(a&b&c)
            */

            // parse context string
            CompoundCondition condition = new AllCondition();
            var collectedConditions = new HashSet<Condition>();

            bool capturingSubCondition = false;
            bool subConditionIsNot = false;
            CompoundCondition subCondition = new AllCondition();
            var  collectedSubConditions = new HashSet<Condition>();

            bool capturingToken = false;
            string currentToken = string.Empty;

            Action captureToken = () => {
                if (capturingToken && currentToken != string.Empty) {
                    if (Condition.FromToken(currentToken) is Condition condition)
                        collectedSubConditions.Add(condition);
                    currentToken = string.Empty;
                }
            };

            Action captureSubConditions = () => {
                if (capturingSubCondition) {
                    if (collectedSubConditions.Count > 0) {
                        subCondition.Conditions = collectedSubConditions;
                        subCondition.IsNot = subConditionIsNot;
                        collectedConditions.Add(subCondition);
                    }
                    collectedSubConditions = new HashSet<Condition>();
                    capturingSubCondition = false;
                    subConditionIsNot = false;
                }
            };

            foreach(char c in contextString) {
                switch (c) {
                    // sub conditions
                    case '(':
                        if (capturingSubCondition)
                            captureToken();
                        else {
                            capturingSubCondition = true;
                            capturingToken = true;
                        }
                        continue;
                    case ')':
                        captureToken();
                        captureSubConditions();
                        continue;

                    // (sub)condition types
                    case CONTEXT_CONDITION_ALL_SEP:
                        captureToken();
                        if (capturingSubCondition) subCondition = new AllCondition();
                        else condition = new AllCondition();
                        continue;
                    case CONTEXT_CONDITION_ANY_SEP:
                        captureToken();
                        if (capturingSubCondition) subCondition = new AnyCondition();
                        else condition = new AnyCondition();
                        continue;
                    case CONTEXT_CONDITION_EXACT_SEP:
                        captureToken();
                        if (capturingSubCondition) subCondition = new ExactCondition();
                        else condition = new ExactCondition();
                        continue;

                    case CONTEXT_CONDITION_NOT:
                        if (!capturingSubCondition) subConditionIsNot = true;
                        continue;

                    // tokens
                    default:
                        if (capturingToken) currentToken += c; continue;
                }
            }

            condition.Conditions = collectedConditions;
            condition.IsRoot = true;
            return condition;
        }

        public abstract class Condition {
            public bool IsRoot { get; set; } = false;
            public bool IsNot { get; set; } = false;
            public abstract bool IsMatch(UIApplication uiApp, CategorySet selectedCategories);

            public static Condition FromToken(string token) {
                // check for reserved tokens first
                switch (token.ToLower()) {
                    case "zero-doc":
                        return new ZeroDocCondition();

                    // selection token requires selected elements
                    case "selection":
                        return new SelectionCondition();

                    // document type
                    case "doc-project":
                        return new DocumentTypeCondition(
                            DocumentTypeCondition.DocumentType.Project
                            );
                    case "doc-family":
                        return new DocumentTypeCondition(
                            DocumentTypeCondition.DocumentType.Family
                            );

                    // active-* tokens require a certain type of active view
                    case "active-drafting-view":
                        return new ViewTypeCondition(ViewType.DraftingView);
                    case "active-detail-view":
                        return new ViewTypeCondition(ViewType.Detail);
                    case "active-plan-view":
                        return new ViewTypeCondition(
                            new ViewType[] {
                                ViewType.FloorPlan,
                                ViewType.CeilingPlan,
                                ViewType.AreaPlan,
                                ViewType.EngineeringPlan
                                }
                            );
                    case "active-floor-plan":
                        return new ViewTypeCondition(ViewType.FloorPlan);
                    case "active-rcp-plan":
                        return new ViewTypeCondition(ViewType.CeilingPlan);
                    case "active-structural-plan":
                        return new ViewTypeCondition(ViewType.EngineeringPlan);
                    case "active-area-plan":
                        return new ViewTypeCondition(ViewType.AreaPlan);
                    case "active-elevation-view":
                        return new ViewTypeCondition(ViewType.Elevation);
                    case "active-section-view":
                        return new ViewTypeCondition(ViewType.Section);
                    case "active-3d-view":
                        return new ViewTypeCondition(ViewType.ThreeD);
                    case "active-sheet":
                        return new ViewTypeCondition(ViewType.DrawingSheet);
                    case "active-legend":
                        return new ViewTypeCondition(ViewType.Legend);
                    case "active-schedule":
                        return new ViewTypeCondition(
                            new ViewType[] {
                                ViewType.PanelSchedule,
                                ViewType.ColumnSchedule,
                                ViewType.Schedule
                                }
                            );
                    case "active-panel-schedule":
                        return new ViewTypeCondition(ViewType.PanelSchedule);
                    case "active-column-schedule":
                        return new ViewTypeCondition(ViewType.ColumnSchedule);
                }

                // check for custom tokens next
                // NOTE:
                // docs have builtin categories
                // docs might have custom categories with non-english names
                // the compare mechanism is providing methods to cover both conditions
                // compare mechanism stores integer ids for builtin categories
                // compare mechanism stores strings for custom category names
                //   avail methods don't have access to doc object so the category names must be stored as string
                BuiltInCategory bic = BuiltInCategory.INVALID;
                if (Enum.TryParse(token, true, out bic) && bic != 0 && bic != BuiltInCategory.INVALID)
                    return new BuiltinCategoryCondition((int)bic);

                // assume the token must be a custom category name
                return new CustomCategoryCondition(token);
            }

            public abstract override bool Equals(object obj);
            public abstract override int GetHashCode();
            public abstract override string ToString();
        }

        abstract class KeywordCondition : Condition {
            public abstract string Keyword { get; }

            public override bool Equals(object obj) {
                if (obj is KeywordCondition)
                    return true;
                return false;
            }

            public override int GetHashCode() {
                return Keyword.GetHashCode();
            }

            public override string ToString() {
                return Keyword;
            }
        }

        abstract class CompoundCondition: Condition {
            public abstract string Separator { get; }

            public HashSet<Condition> Conditions = new HashSet<Condition>();

            public override bool Equals(object obj) {
                if (obj is HashSet<Condition> conditions)
                    return new HashSet<Condition>(Conditions.Except(conditions)).Count == 0;
                else if (obj is CompoundCondition compCond)
                    return new HashSet<Condition>(Conditions.Except(compCond.Conditions)).Count == 0;
                else
                    return false;
            }

            public override int GetHashCode() {
                return Conditions.GetHashCode();
            }

            public override string ToString() {
                if (IsRoot)
                    return string.Join(Separator, Conditions);
                else
                    return (IsNot ? "!" : "") + "(" + string.Join(Separator, Conditions) + ")";
            }
        }

        class DocumentTypeCondition : Condition {
            // acceptable document types
            public enum DocumentType {
                Any,
                Project,
                Family
            }

            DocumentType _docType = DocumentType.Any;

            public DocumentTypeCondition(DocumentType docType = DocumentType.Any) => _docType = docType;

            public override bool IsMatch(UIApplication uiApp, CategorySet selectedCategories) {
                // check document type
                switch (_docType) {
                    case DocumentType.Project:
                        if (uiApp != null && uiApp.ActiveUIDocument != null
                                && uiApp.ActiveUIDocument.Document.IsFamilyDocument)
                            return IsNot ? true : false;
                        break;
                    case DocumentType.Family:
                        if (uiApp != null && uiApp.ActiveUIDocument != null
                                && !uiApp.ActiveUIDocument.Document.IsFamilyDocument)
                            return IsNot ? true : false;
                        break;
                }
                return IsNot ? false : true;
            }

            public override bool Equals(object obj) {
                if (obj is DocumentType docType)
                    return _docType == docType;
                else if (obj is DocumentTypeCondition docTypeCond)
                    return _docType == docTypeCond._docType;
                else
                    return false;
            }

            public override int GetHashCode() {
                return _docType.GetHashCode();
            }

            public override string ToString() {
                return _docType.ToString();
            }
        }

        class ViewTypeCondition : Condition {
            HashSet<ViewType> _viewTypes;

            public ViewTypeCondition(ViewType viewType) => _viewTypes = new HashSet<ViewType> { viewType };
            public ViewTypeCondition(ViewType[] viewTypes) => _viewTypes = new HashSet<ViewType> (viewTypes);

            public override bool IsMatch(UIApplication uiApp, CategorySet selectedCategories) {
                try {
#if (REVIT2013 || REVIT2014)
                    // check active views
                    if (_viewTypes.Count > 0) {
                        if (uiApp != null && uiApp.ActiveUIDocument != null
                            && !_viewTypes.Contains(uiApp.ActiveUIDocument.ActiveView.ViewType))
                            return false;
                    }
#else
                    // check active views
                    if (_viewTypes.Count > 0) {
                        if (uiApp != null && uiApp.ActiveUIDocument != null
                            && !_viewTypes.Contains(uiApp.ActiveUIDocument.ActiveGraphicalView.ViewType))
                            return IsNot ? true : false;
                    }
#endif
                }
                // say no if any errors occured, otherwise Revit will not call this method again if exceptions
                // are bubbled up
                catch {}
                return IsNot ? true : false;
            }

            public override bool Equals(object obj) {
                if (obj is HashSet<ViewType> viewTypes)
                    return new HashSet<ViewType>(_viewTypes.Except(viewTypes)).Count == 0;
                else if (obj is ViewTypeCondition viewTypeCond)
                    return new HashSet<ViewType>(_viewTypes.Except(viewTypeCond._viewTypes)).Count == 0;
                else
                    return false;
            }

            public override int GetHashCode() {
                return _viewTypes.GetHashCode();
            }

            public override string ToString() {
                return string.Join(";", _viewTypes);
            }
        }

        abstract class CategoryCondition : Condition {
            public abstract bool IsMatch(Category category);
        }

        class BuiltinCategoryCondition : CategoryCondition {
            int _categoryId = -1;

            public BuiltinCategoryCondition(int categoryId) => _categoryId = categoryId;

            public override bool IsMatch(UIApplication uiApp, CategorySet selectedCategories) {
                if (selectedCategories.IsEmpty)
                    return IsNot ? true : false;

                try {
                    foreach (Category category in selectedCategories)
                    if (category.Id.IntegerValue == _categoryId)
                            return IsNot ? false : true;
                }
                catch { }

                return IsNot ? true : false;
            }

            public override bool IsMatch(Category category) {
                bool res = false;
                try {
                    res = category.Id.IntegerValue == _categoryId;
                }
                catch { }
                return IsNot ? !res : res;
            }

            public override bool Equals(object obj) {
                if (obj is int categoryId)
                    return _categoryId == categoryId;
                else if (obj is BuiltinCategoryCondition builtinCatCond)
                    return _categoryId == builtinCatCond._categoryId;
                else
                    return false;
            }

            public override int GetHashCode() {
                return _categoryId.GetHashCode();
            }

            public override string ToString() {
                return _categoryId.ToString();
            }
        }

        class CustomCategoryCondition : CategoryCondition {
            string _categoryName = string.Empty;

            public CustomCategoryCondition(string categoryName) => _categoryName = categoryName.ToLower();

            public override bool IsMatch(UIApplication uiApp, CategorySet selectedCategories) {
                if (selectedCategories.IsEmpty)
                    return IsNot ? true : false;
                try {
                    foreach (Category category in selectedCategories)
                        if (_categoryName.Equals(category.Name, StringComparison.InvariantCultureIgnoreCase))
                            return IsNot ? false : true;
                } catch { }

                return IsNot ? true : false;
            }

            public override bool IsMatch(Category category) {
                bool res = false;
                try {
                    res = _categoryName.Equals(category.Name, StringComparison.InvariantCultureIgnoreCase);
                }
                catch { }
                return IsNot ? !res : res;
            }

            public override bool Equals(object obj) {
                if (obj is string categoryName)
                    return _categoryName.Equals(categoryName, StringComparison.InvariantCultureIgnoreCase);
                else if (obj is CustomCategoryCondition catCond)
                    return _categoryName.Equals(catCond._categoryName, StringComparison.InvariantCultureIgnoreCase);
                else
                    return false;
            }

            public override int GetHashCode() {
                return _categoryName.GetHashCode();
            }

            public override string ToString() {
                return _categoryName;
            }
        }

        class ZeroDocCondition : KeywordCondition {
            public override string Keyword => "zero-doc";

            public override bool IsMatch(UIApplication uiApp, CategorySet selectedCategories) {
                return IsNot ? false : true;
            }
        }

        class SelectionCondition : KeywordCondition {
            public override string Keyword => "selection";

            public override bool IsMatch(UIApplication uiApp, CategorySet selectedCategories) {
                // check selection
                bool res = !selectedCategories.IsEmpty;
                return IsNot ? !res : res;
            }
        }

        class AllCondition : CompoundCondition {
            public override string Separator => new string(new char[] { CONTEXT_CONDITION_ALL_SEP });

            public override bool IsMatch(UIApplication uiApp, CategorySet selectedCategories) {
                bool res = Conditions.All(c => c.IsMatch(uiApp, selectedCategories));
                return IsNot ? !res : res;
            }
        }

        class AnyCondition: CompoundCondition {
            public override string Separator => new string(new char[] { CONTEXT_CONDITION_ANY_SEP });

            public override bool IsMatch(UIApplication uiApp, CategorySet selectedCategories) {
                bool res = Conditions.Any(c => c.IsMatch(uiApp, selectedCategories));
                return IsNot ? !res : res;
            }
        }

        class ExactCondition: CompoundCondition {
            public override string Separator => new string(new char[] { CONTEXT_CONDITION_EXACT_SEP });

            public override bool IsMatch(UIApplication uiApp, CategorySet selectedCategories) {
                var catConditions = Conditions.OfType<CategoryCondition>();
                
                // test if all category conditions are ALL in selectedCategories
                if (!catConditions.All(c => c.IsMatch(uiApp, selectedCategories)))
                    return IsNot ? true : false;
                
                // test if there is no selectedCategories that isnt matching ANY condition
                foreach (Category cat in selectedCategories)
                    if (!catConditions.Any(c => c.IsMatch(cat)))
                        return IsNot ? true : false;

                return IsNot ? false : true;
            }
        }

        public Condition ContextCondition = null;

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories) {
            if (ContextCondition is Condition ctx)
                return ctx.IsMatch(uiApp, selectedCategories);
            return false;
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

