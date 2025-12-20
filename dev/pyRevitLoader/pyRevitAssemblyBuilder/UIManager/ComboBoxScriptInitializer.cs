using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
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
    /// Supports: __cmb_on_change__, __cmb_dropdown_close__, __cmb_dropdown_open__
    /// Uses reflection to access IronPython since the assembly doesn't directly reference it.
    /// </summary>
    public class ComboBoxScriptInitializer
    {
        private readonly LoggingHelper _logger;
        private readonly UIApplication _uiApp;
        
        // Cached reflection types and methods for IronPython
        private static Assembly _ironPythonAssembly;
        private static Assembly _microsoftScriptingAssembly;
        private static Type _pythonType;
        private static MethodInfo _createEngineMethod;
        private static bool _initialized;
        private static bool _initializationFailed;
        
        public ComboBoxScriptInitializer(UIApplication uiApp, object pythonLogger)
        {
            _uiApp = uiApp;
            _logger = new LoggingHelper(pythonLogger);
            EnsureInitialized();
        }

        private void EnsureInitialized()
        {
            if (_initialized || _initializationFailed)
                return;

            try
            {
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    var name = assembly.GetName().Name;
                    if (name != null)
                    {
                        if (name.Contains("IronPython") && !name.Contains("Modules") && 
                            !name.Contains("SQLite") && !name.Contains("Wpf"))
                        {
                            _ironPythonAssembly = assembly;
                        }
                        else if (name.Contains("Microsoft.Scripting") && !name.Contains("Metadata"))
                        {
                            _microsoftScriptingAssembly = assembly;
                        }
                    }
                }

                if (_ironPythonAssembly == null)
                {
                    _logger.Warning("IronPython assembly not found. ComboBox scripts will not be executed.");
                    _initializationFailed = true;
                    return;
                }

                _pythonType = _ironPythonAssembly.GetType("IronPython.Hosting.Python");
                if (_pythonType == null)
                {
                    _logger.Warning("IronPython.Hosting.Python type not found.");
                    _initializationFailed = true;
                    return;
                }

                _createEngineMethod = _pythonType.GetMethod("CreateEngine", new Type[0]);
                _initialized = true;
                _logger.Debug("ComboBoxScriptInitializer initialized successfully.");
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to initialize ComboBoxScriptInitializer: {ex.Message}");
                _initializationFailed = true;
            }
        }

        // Keep engines alive for ComboBoxes with event handlers
        private static readonly List<object> _activeEngines = new List<object>();

        /// <summary>
        /// Executes event handler setup for a ComboBox script file.
        /// </summary>
        public bool ExecuteEventHandlerSetup(ParsedComponent component, ComboBox comboBox)
        {
            if (_initializationFailed || !_initialized)
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

            object engine = null;
            bool handlersWired = false;
            try
            {
                _logger.Info($"Setting up event handlers for ComboBox '{component.DisplayName}' from '{scriptPath}'");
                
                engine = _createEngineMethod.Invoke(null, null);
                if (engine == null)
                {
                    _logger.Error("Failed to create IronPython engine.");
                    return false;
                }

                var engineType = engine.GetType();
                
                // Set up search paths
                SetupSearchPaths(engine, engineType, component);

                // Create scope
                var createModuleMethod = _pythonType.GetMethod("CreateModule", 
                    BindingFlags.Public | BindingFlags.Static, null,
                    new[] { engineType, typeof(string) }, null);
                
                var scope = createModuleMethod?.Invoke(null, new[] { engine, "__main__" });
                if (scope == null)
                {
                    _logger.Error("Failed to create script scope.");
                    return false;
                }

                var scopeType = scope.GetType();
                var setVariableMethod = FindMethod(scopeType, "SetVariable", typeof(string), typeof(object));
                var containsVariableMethod = FindMethod(scopeType, "ContainsVariable", typeof(string));
                var getVariableMethod = FindMethod(scopeType, "GetVariable", typeof(string));

                // Set up built-in variables
                SetupBuiltins(engine, engineType);

                // Load Revit API assemblies
                LoadRevitAssemblies(engine, engineType);

                // Set __file__ variable
                setVariableMethod?.Invoke(scope, new object[] { "__file__", scriptPath });

                // Execute the script file
                _logger.Debug("Executing script file...");
                var createScriptSourceMethod = FindMethod(engineType, "CreateScriptSourceFromFile", typeof(string), typeof(Encoding));
                var scriptSource = createScriptSourceMethod?.Invoke(engine, new object[] { scriptPath, Encoding.UTF8 });
                if (scriptSource == null)
                {
                    _logger.Error($"Failed to create script source from '{scriptPath}'.");
                    return false;
                }

                var executeMethod = FindMethod(scriptSource.GetType(), "Execute", scopeType);
                try
                {
                    executeMethod?.Invoke(scriptSource, new[] { scope });
                }
                catch (TargetInvocationException scriptEx)
                {
                    var innerEx = scriptEx.InnerException;
                    _logger.Error($"Script execution error: {innerEx?.Message ?? scriptEx.Message}");
                    return false;
                }

                // Check for event handlers
                bool hasOnChange = (bool)(containsVariableMethod?.Invoke(scope, new object[] { "__cmb_on_change__" }) ?? false);
                bool hasDropdownClose = (bool)(containsVariableMethod?.Invoke(scope, new object[] { "__cmb_dropdown_close__" }) ?? false);
                bool hasDropdownOpen = (bool)(containsVariableMethod?.Invoke(scope, new object[] { "__cmb_dropdown_open__" }) ?? false);

                if (!hasOnChange && !hasDropdownClose && !hasDropdownOpen)
                {
                    _logger.Debug($"No event handlers found in script for ComboBox '{component.DisplayName}'.");
                    return true;
                        }

                _logger.Debug("Found event handlers, setting up ComboBox context...");

                // Create the C# context object - passed directly to Python
                var ctx = new ComboBoxContext(comboBox, component, _uiApp);

                // Get operations for invoking Python functions
                        var operationsProperty = engineType.GetProperty("Operations");
                        var operations = operationsProperty?.GetValue(engine);
                var invokeMethod = operations != null ? 
                    FindMethod(operations.GetType(), "Invoke", typeof(object), typeof(object[])) : null;

                // Wire up event handlers
                if (hasOnChange)
                {
                    var handler = getVariableMethod?.Invoke(scope, new object[] { "__cmb_on_change__" });
                    if (handler != null && invokeMethod != null)
                    {
                        comboBox.CurrentChanged += (sender, args) =>
                        {
                            try
                            {
                                invokeMethod.Invoke(operations, new object[] { handler, new object[] { sender, args, ctx } });
                            }
                            catch (Exception ex)
                            {
                                _logger.Error($"Error in __cmb_on_change__: {ex.Message}");
                            }
                        };
                        _logger.Debug("Wired __cmb_on_change__ handler");
                        handlersWired = true;
                                }
                }

                if (hasDropdownClose)
                {
                    var handler = getVariableMethod?.Invoke(scope, new object[] { "__cmb_dropdown_close__" });
                    if (handler != null && invokeMethod != null)
                    {
                        comboBox.DropDownClosed += (sender, args) =>
                        {
                            try
                            {
                                invokeMethod.Invoke(operations, new object[] { handler, new object[] { sender, args, ctx } });
                            }
                            catch (Exception ex)
                            {
                                _logger.Error($"Error in __cmb_dropdown_close__: {ex.Message}");
                            }
                        };
                        _logger.Debug("Wired __cmb_dropdown_close__ handler");
                        handlersWired = true;
                    }
                }

                if (hasDropdownOpen)
                {
                    var handler = getVariableMethod?.Invoke(scope, new object[] { "__cmb_dropdown_open__" });
                    if (handler != null && invokeMethod != null)
                    {
                        comboBox.DropDownOpened += (sender, args) =>
                        {
                            try
                            {
                                invokeMethod.Invoke(operations, new object[] { handler, new object[] { sender, args, ctx } });
                            }
                            catch (Exception ex)
                        {
                                _logger.Error($"Error in __cmb_dropdown_open__: {ex.Message}");
                        }
                        };
                        _logger.Debug("Wired __cmb_dropdown_open__ handler");
                        handlersWired = true;
                    }
                }

                // Keep engine alive if handlers were wired
                if (handlersWired)
                {
                    _activeEngines.Add(engine);
                    _logger.Info($"Event handlers set up successfully for ComboBox '{component.DisplayName}'.");
                }

                return true;
            }
            catch (Exception ex)
            {
                var actualException = ex;
                while (actualException is TargetInvocationException tie && tie.InnerException != null)
                    actualException = tie.InnerException;
                
                _logger.Error($"Error setting up event handlers for ComboBox '{component.DisplayName}': {actualException.Message}");
                
                // Cleanup engine on error
                if (!handlersWired)
                    CleanupEngine(engine);
                
                return false;
            }
        }

        private void SetupSearchPaths(object engine, Type engineType, ParsedComponent component)
        {
            var getSearchPathsMethod = engineType.GetMethod("GetSearchPaths");
            var setSearchPathsMethod = engineType.GetMethod("SetSearchPaths");
            
            if (getSearchPathsMethod != null && setSearchPathsMethod != null)
            {
                var paths = getSearchPathsMethod.Invoke(engine, null) as ICollection<string>;
                if (paths != null && !string.IsNullOrEmpty(component.Directory))
                {
                    paths.Add(component.Directory);
                    var libPath = Path.Combine(component.Directory, "lib");
                    if (Directory.Exists(libPath))
                        paths.Add(libPath);
                    setSearchPathsMethod.Invoke(engine, new[] { paths });
                }
            }
        }

        private void SetupBuiltins(object engine, Type engineType)
        {
            var getBuiltinMethod = _pythonType.GetMethod("GetBuiltinModule",
                BindingFlags.Public | BindingFlags.Static, null, new[] { engineType }, null);
            
            if (getBuiltinMethod != null)
            {
                var builtin = getBuiltinMethod.Invoke(null, new[] { engine });
                if (builtin != null)
                {
                    var builtinSetVar = FindMethod(builtin.GetType(), "SetVariable", typeof(string), typeof(object));
                    builtinSetVar?.Invoke(builtin, new object[] { "__revit__", _uiApp });
                }
            }
        }

        private void LoadRevitAssemblies(object engine, Type engineType)
        {
            var runtimeProperty = engineType.GetProperty("Runtime");
            var runtime = runtimeProperty?.GetValue(engine);
            if (runtime != null)
            {
                var loadAssemblyMethod = FindMethod(runtime.GetType(), "LoadAssembly", typeof(Assembly));
                if (loadAssemblyMethod != null)
                {
                    loadAssemblyMethod.Invoke(runtime, new object[] { typeof(Autodesk.Revit.DB.Document).Assembly });
                    loadAssemblyMethod.Invoke(runtime, new object[] { typeof(Autodesk.Revit.UI.TaskDialog).Assembly });
                }
            }
        }

        private void CleanupEngine(object engine)
        {
            if (engine == null) return;
                    try
                    {
                        var runtimeProperty = engine.GetType().GetProperty("Runtime");
                        var runtime = runtimeProperty?.GetValue(engine);
                        var shutdownMethod = FindMethodByName(runtime?.GetType(), "Shutdown");
                        shutdownMethod?.Invoke(runtime, null);
                    }
            catch { /* Ignore cleanup errors */ }
                }

        private string FindScriptPath(ParsedComponent component)
        {
            if (string.IsNullOrEmpty(component.Directory))
                return null;

            var scriptPath = Path.Combine(component.Directory, "script.py");
            if (File.Exists(scriptPath))
                return scriptPath;

            if (!string.IsNullOrEmpty(component.ScriptPath) && File.Exists(component.ScriptPath))
                return component.ScriptPath;

            return null;
        }

        private static MethodInfo FindMethod(Type type, string name, params Type[] parameterTypes)
        {
            if (type == null) return null;
            
            try
            {
                return type.GetMethod(name, parameterTypes);
            }
            catch (AmbiguousMatchException)
            {
                foreach (var method in type.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static))
                {
                    if (method.Name != name) continue;
                    var parameters = method.GetParameters();
                    if (parameters.Length != parameterTypes.Length) continue;
                    
                    bool match = true;
                    for (int i = 0; i < parameters.Length; i++)
                    {
                        if (!parameters[i].ParameterType.IsAssignableFrom(parameterTypes[i]) &&
                            parameters[i].ParameterType != parameterTypes[i])
                        {
                            match = false;
                            break;
                        }
                    }
                    if (match) return method;
                }
                return null;
            }
        }
        
        private static MethodInfo FindMethodByName(Type type, string name)
        {
            if (type == null) return null;
            try
            {
                return type.GetMethod(name, Type.EmptyTypes);
            }
            catch (AmbiguousMatchException)
            {
                foreach (var method in type.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static))
                {
                    if (method.Name == name && method.GetParameters().Length == 0)
                        return method;
                }
                return null;
            }
        }
    }
}
