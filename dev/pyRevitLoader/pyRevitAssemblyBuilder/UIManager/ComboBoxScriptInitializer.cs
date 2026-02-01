using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Autodesk.Revit.UI;
using pyRevitExtensionParser;
using pyRevitAssemblyBuilder.SessionManager;
using RevitComboBoxMember = Autodesk.Revit.UI.ComboBoxMember;

namespace pyRevitAssemblyBuilder.UIManager
{
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

        public ComboBoxContext(ComboBox comboBox, ParsedComponent component, UIApplication uiApp)
        {
            _comboBox = comboBox;
            _component = component;
            _uiApp = uiApp;
        }

        /// <summary>Gets the raw Revit ComboBox API object.</summary>
        public ComboBox combobox => _comboBox;

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
        private readonly ILogger _logger;
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

        public ComboBoxScriptInitializer(UIApplication uiApp, ILogger logger)
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
                Action<string> logAction = msg => _logger.Debug(msg);
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
            var context = new ComboBoxContext(comboBox, component, _uiApp);

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
