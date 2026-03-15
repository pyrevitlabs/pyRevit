using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Autodesk.Revit.UI;
using pyRevitExtensionParser;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitLabs.NLog;
using RevitComboBoxMember = Autodesk.Revit.UI.ComboBoxMember;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Lightweight wrapper around Revit ComboBox that provides the same API
    /// as pyrevit.coreutils.ribbon._PyRevitRibbonComboBox, so that Python
    /// scripts using ctx.ui_item work identically under the C# loader.
    /// </summary>
    public class ComboBoxUIItemWrapper
    {
        private readonly ComboBox _comboBox;
        private readonly SessionManager.ILogger _logger;

        public ComboBoxUIItemWrapper(ComboBox comboBox, SessionManager.ILogger logger = null)
        {
            _comboBox = comboBox;
            _logger = logger;
        }

        /// <summary>Gets or sets the currently selected ComboBoxMember.</summary>
        public RevitComboBoxMember current
        {
            get
            {
                try { return _comboBox?.Current; }
                catch (Exception ex)
                {
                    _logger?.Debug($"Failed to read ComboBox current item: {ex.Message}");
                    return null;
                }
            }
            set
            {
                if (_comboBox != null)
                    _comboBox.Current = value;
            }
        }

        /// <summary>Gets whether the ComboBox is enabled.</summary>
        public bool enabled
        {
            get => _comboBox?.Enabled ?? false;
            set { if (_comboBox != null) _comboBox.Enabled = value; }
        }

        /// <summary>Gets whether the ComboBox is visible.</summary>
        public bool visible
        {
            get => _comboBox?.Visible ?? false;
            set { if (_comboBox != null) _comboBox.Visible = value; }
        }

        /// <summary>
         /// Adds a single item using plain values instead of Revit API types.
         /// </summary>
        public RevitComboBoxMember AddItem(string name, string itemText, string groupName = null)
        {
            if (_comboBox == null || string.IsNullOrEmpty(name) || string.IsNullOrEmpty(itemText))
                return null;

            var memberData = new ComboBoxMemberData(name, itemText);
            if (!string.IsNullOrEmpty(groupName))
                memberData.GroupName = groupName;

            return _comboBox.AddItem(memberData);
        }

        /// <summary>
        /// pyRevit-compatible alias for adding one item.
        /// Supports: add_item(spec), add_item(spec, defaultGroup),
        /// and add_item(name, text[, group]).
        /// </summary>
        public RevitComboBoxMember add_item(params object[] args)
        {
            if (_comboBox == null || args == null || args.Length == 0)
                return null;

            if (!TryCreateMemberDataFromArguments(args, out var memberData))
                return null;

            return _comboBox.AddItem(memberData);
        }

        /// <summary>
        /// Adds multiple items using plain values.
        /// Supported item formats: string, [name, text], [name, text, group].
        /// </summary>
        public void add_items(IEnumerable itemSpecs, string defaultGroupName = null)
        {
            if (_comboBox == null || itemSpecs == null)
                return;

            foreach (var itemSpec in itemSpecs)
            {
                if (!TryCreateMemberData(itemSpec, defaultGroupName, out var memberData))
                    continue;
                _comboBox.AddItem(memberData);
            }
        }

        /// <summary>
        /// .NET-style alias for adding multiple plain item specs.
        /// </summary>
        public void AddItems(IEnumerable itemSpecs, string defaultGroupName = null)
        {
            add_items(itemSpecs, defaultGroupName);
        }

        /// <summary>
        /// .NET-style overload for adding typed ComboBox member data entries.
        /// </summary>
        public void AddItems(IEnumerable<ComboBoxMemberData> memberDataItems)
        {
            if (_comboBox == null || memberDataItems == null)
                return;

            foreach (var memberData in memberDataItems)
            {
                if (memberData != null)
                    _comboBox.AddItem(memberData);
            }
        }

        private static bool TryCreateMemberData(object itemSpec, string defaultGroupName, out ComboBoxMemberData memberData)
        {
            memberData = null;
            if (itemSpec == null)
                return false;

            if (itemSpec is string text)
            {
                if (string.IsNullOrEmpty(text))
                    return false;

                memberData = new ComboBoxMemberData(text, text);
                if (!string.IsNullOrEmpty(defaultGroupName))
                    memberData.GroupName = defaultGroupName;
                return true;
            }

            if (itemSpec is IList values && values.Count >= 2)
            {
                var name = values[0]?.ToString();
                var itemText = values[1]?.ToString();
                var groupName = values.Count > 2 ? values[2]?.ToString() : defaultGroupName;
                if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(itemText))
                    return false;

                memberData = new ComboBoxMemberData(name, itemText);
                if (!string.IsNullOrEmpty(groupName))
                    memberData.GroupName = groupName;
                return true;
            }

            return false;
        }

        private static bool TryCreateMemberDataFromArguments(object[] args, out ComboBoxMemberData memberData)
        {
            memberData = null;
            if (args == null || args.Length == 0)
                return false;

            if (args.Length == 1)
            {
                var itemSpec = args[0];
                if (itemSpec is ComboBoxMemberData typedMemberData)
                {
                    memberData = typedMemberData;
                    return true;
                }

                return TryCreateMemberData(itemSpec, null, out memberData);
            }

            if (args.Length == 2)
            {
                var first = args[0];
                var second = args[1]?.ToString();

                if (first is ComboBoxMemberData typedMemberData)
                {
                    memberData = typedMemberData;
                    return true;
                }

                if (first is string name)
                {
                    if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(second))
                        return false;

                    memberData = new ComboBoxMemberData(name, second);
                    return true;
                }

                return TryCreateMemberData(first, second, out memberData);
            }

            if (args.Length == 3)
            {
                var name = args[0]?.ToString();
                var itemText = args[1]?.ToString();
                var groupName = args[2]?.ToString();

                if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(itemText))
                    return false;

                memberData = new ComboBoxMemberData(name, itemText);
                if (!string.IsNullOrEmpty(groupName))
                    memberData.GroupName = groupName;
                return true;
            }

            return false;
        }

        /// <summary>Adds a separator to the ComboBox dropdown list.</summary>
        public void add_separator()
        {
            _comboBox?.AddSeparator();
        }

        /// <summary>Gets all items in the ComboBox.</summary>
        public IList<RevitComboBoxMember> get_items()
        {
            try { return _comboBox?.GetItems() ?? (IList<RevitComboBoxMember>)new List<RevitComboBoxMember>(); }
            catch (Exception ex)
            {
                _logger?.Debug($"Failed to read ComboBox items: {ex.Message}");
                return new List<RevitComboBoxMember>();
            }
        }

        /// <summary>Gets contextual help for the ComboBox.</summary>
        public ContextualHelp get_contexthelp()
        {
            try { return _comboBox?.GetContextualHelp(); }
            catch (Exception ex)
            {
                _logger?.Debug($"Failed to read ComboBox contextual help: {ex.Message}");
                return null;
            }
        }

        /// <summary>Sets contextual help for the ComboBox.</summary>
        public void set_contexthelp(ContextualHelp help)
        {
            _comboBox?.SetContextualHelp(help);
        }
    }

    /// <summary>
    /// Context object providing access to ComboBox state and data.
    /// This C# class is passed directly to Python event handlers.
    /// </summary>
    public class ComboBoxContext
    {
        private readonly ComboBox _comboBox;
        private readonly ParsedComponent _component;
        private readonly UIApplication _uiApp;
        private readonly Dictionary<string, object> _userData = new Dictionary<string, object>();
        private readonly ComboBoxUIItemWrapper _uiItem;

        public ComboBoxContext(ComboBox comboBox, ParsedComponent component, UIApplication uiApp, SessionManager.ILogger logger = null)
        {
            _comboBox = comboBox;
            _component = component;
            _uiApp = uiApp;
            _uiItem = new ComboBoxUIItemWrapper(comboBox, logger);
        }

        /// <summary>Gets the raw Revit ComboBox API object.</summary>
        public ComboBox combobox => _comboBox;

        /// <summary>
        /// Gets the UI item wrapper providing the same API as
        /// pyrevit.coreutils.ribbon._PyRevitRibbonComboBox.
        /// </summary>
        public ComboBoxUIItemWrapper ui_item => _uiItem;

        /// <summary>Gets the currently selected ComboBoxMember.</summary>
        public RevitComboBoxMember current_item => _comboBox?.Current;

        /// <summary>Gets the text of the currently selected item.</summary>
        public string current_value => current_item?.ItemText ?? string.Empty;

        /// <summary>Gets the name/id of the currently selected item.</summary>
        public string current_name => current_item?.Name ?? string.Empty;

        /// <summary>Gets all items in the ComboBox.</summary>
        public IList<RevitComboBoxMember> items => _comboBox?.GetItems() ?? (IList<RevitComboBoxMember>)new List<RevitComboBoxMember>();

        /// <summary>Gets the number of items in the ComboBox.</summary>
        public int item_count => items.Count;

        /// <summary>Gets the text values of all items.</summary>
        public IList<string> item_texts => items.Select(i => i.ItemText).ToList();

        /// <summary>Gets the names/ids of all items.</summary>
        public IList<string> item_names => items.Select(i => i.Name).ToList();

        /// <summary>Gets the Revit UIApplication instance.</summary>
        public UIApplication uiapp => _uiApp;

        /// <summary>Gets the component's bundle directory.</summary>
        public string directory => _component?.Directory ?? string.Empty;

        /// <summary>Gets the component name.</summary>
        public string name => _component?.Name ?? string.Empty;

        /// <summary>Gets the component display name.</summary>
        public string display_name => _component?.DisplayName ?? string.Empty;

        /// <summary>Gets the user data dictionary for storing custom data between events.</summary>
        public Dictionary<string, object> user_data => _userData;

        /// <summary>
        /// Sets the current selection by name or text.
        /// </summary>
        /// <param name="item_name_or_text">The Name or ItemText of the item to select.</param>
        /// <returns>True if item was found and selected.</returns>
        public bool set_current(string item_name_or_text)
        {
            if (_comboBox == null) return false;

            foreach (var item in items)
            {
                if (item.Name == item_name_or_text || item.ItemText == item_name_or_text)
                {
                    try
                    {
                        _comboBox.Current = item;
                        return true;
                    }
                    catch
                    {
                        return false;
                    }
                }
            }
            return false;
        }

        /// <summary>
        /// Gets an item by its Name.
        /// </summary>
        /// <param name="itemName">The Name to search for.</param>
        /// <returns>The item or null.</returns>
        public RevitComboBoxMember get_item_by_name(string itemName)
        {
            return items.FirstOrDefault(i => i.Name == itemName);
        }

        /// <summary>
        /// Gets an item by its ItemText.
        /// </summary>
        /// <param name="text">The ItemText to search for.</param>
        /// <returns>The item or null.</returns>
        public RevitComboBoxMember get_item_by_text(string text)
        {
            return items.FirstOrDefault(i => i.ItemText == text);
        }
    }

    /// <summary>
    /// Handles execution of ComboBox event handler scripts.
    /// Delegates to PyRevitLoader.ComboBoxExecutor for actual IronPython execution.
    /// </summary>
    public class ComboBoxScriptInitializer
    {
        private static readonly Logger nlog = LogManager.GetCurrentClassLogger();
        private readonly SessionManager.ILogger _logger;
        private readonly UIApplication _uiApp;

        // Cached reflection types and methods
        private static Assembly _pyRevitLoaderAssembly;
        private static Type _executorType;
        private static bool _staticInitialized;
        private static bool _staticInitializationFailed;
        private static readonly object _staticLock = new object();

        private object _executor;
        private MethodInfo _executeMethod;
        private bool _instanceInitialized;
        private bool _instanceInitializationFailed;

        public ComboBoxScriptInitializer(UIApplication uiApp, SessionManager.ILogger logger)
        {
            _uiApp = uiApp;
            _logger = logger;
            EnsureStaticInitialized();
        }

        /// <summary>
        /// One-time static initialization to find assemblies and types.
        /// </summary>
        private void EnsureStaticInitialized()
        {
            if (_staticInitialized || _staticInitializationFailed)
                return;

            lock (_staticLock)
            {
                if (_staticInitialized || _staticInitializationFailed)
                    return;

                try
                {
                    // Use AssemblyCache to find pyRevitLoader assembly
                    _pyRevitLoaderAssembly = SessionManager.AssemblyCache.GetByPrefix("pyRevitLoader");

                    if (_pyRevitLoaderAssembly == null)
                    {
                        _staticInitializationFailed = true;
                        return;
                    }

                    // Get ComboBoxExecutor type
                    _executorType = _pyRevitLoaderAssembly.GetType("PyRevitLoader.ComboBoxExecutor");
                    if (_executorType == null)
                    {
                        _staticInitializationFailed = true;
                        return;
                    }

                    _staticInitialized = true;
                }
                catch
                {
                    _staticInitializationFailed = true;
                }
            }
        }

        /// <summary>
        /// Per-instance initialization to create executor with UIApp.
        /// </summary>
        private void EnsureInstanceInitialized()
        {
            if (_instanceInitialized || _instanceInitializationFailed)
                return;

            if (_staticInitializationFailed || _executorType == null)
            {
                _logger.Warning("PyRevitLoader assembly or ComboBoxExecutor type not found");
                _instanceInitializationFailed = true;
                return;
            }

            try
            {
                // Create executor instance with logger
                Action<string> logAction = msg => nlog.Info(msg);
                _executor = Activator.CreateInstance(_executorType, _uiApp, logAction);

                // Get ExecuteEventHandlerSetup method
                _executeMethod = _executorType.GetMethod("ExecuteEventHandlerSetup");

                _instanceInitialized = true;
                _logger.Debug("ComboBoxScriptInitializer initialized successfully");
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to initialize ComboBoxScriptInitializer: {ex.Message}");
                _instanceInitializationFailed = true;
            }
        }

        /// <summary>
        /// Executes event handler setup for a ComboBox script file.
        /// </summary>
        public bool ExecuteEventHandlerSetup(ParsedComponent component, ComboBox comboBox)
        {
            EnsureInstanceInitialized();

            if (_instanceInitializationFailed || _executor == null || _executeMethod == null)
            {
                _logger.Debug("ComboBoxScriptInitializer not available. Skipping script execution.");
                return false;
            }

            var scriptPath = FindScriptPath(component);
            if (string.IsNullOrEmpty(scriptPath))
            {
                _logger.Debug($"No script.py found for ComboBox '{component.DisplayName}'.");
                return true;
            }

            // Create context
            var context = new ComboBoxContext(comboBox, component, _uiApp, _logger);

            // Collect additional search paths from extension hierarchy
            var additionalPaths = new List<string>();
            if (!string.IsNullOrEmpty(component?.Directory))
            {
                var current = new DirectoryInfo(component.Directory);
                while (current != null)
                {
                    var libPath = Path.Combine(current.FullName, "lib");
                    if (Directory.Exists(libPath) && !additionalPaths.Contains(libPath))
                        additionalPaths.Add(libPath);

                    if (current.Name.EndsWith(".extension", StringComparison.OrdinalIgnoreCase))
                        break;
                    current = current.Parent;
                }
            }

            try
            {
                // Call ComboBoxExecutor.ExecuteEventHandlerSetup(scriptPath, context, comboBox, additionalPaths)
                var result = _executeMethod.Invoke(_executor, new object[] { scriptPath, context, comboBox, additionalPaths });
                return result is bool boolResult ? boolResult : true;
            }
            catch (TargetInvocationException ex)
            {
                _logger.Error($"Error setting up event handlers: {ex.InnerException?.Message ?? ex.Message}");
                return false;
            }
            catch (Exception ex)
            {
                _logger.Error($"Error setting up event handlers: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Finds the script path for a ComboBox component.
        /// Only Python scripts (.py) are supported for ComboBox event handlers.
        /// </summary>
        private string FindScriptPath(ParsedComponent component)
        {
            if (string.IsNullOrEmpty(component.Directory))
                return null;

            // Only Python scripts can define event handlers for ComboBoxes
            var scriptPath = Path.Combine(component.Directory, "script.py");
            if (File.Exists(scriptPath))
                return scriptPath;

            // Also check if component's ScriptPath is a Python file
            if (!string.IsNullOrEmpty(component.ScriptPath) &&
                component.ScriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase) &&
                File.Exists(component.ScriptPath))
                return component.ScriptPath;

            return null;
        }
    }
}
