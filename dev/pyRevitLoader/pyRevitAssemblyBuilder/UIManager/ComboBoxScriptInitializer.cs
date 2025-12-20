using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using Autodesk.Revit.UI;
using pyRevitExtensionParser;
using pyRevitLabs.NLog;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Handles execution of __selfinit__ scripts for ComboBox components.
    /// Uses reflection to access IronPython since the assembly doesn't directly reference it.
    /// </summary>
    public class ComboBoxScriptInitializer
    {
        private readonly Logger _logger = LogManager.GetCurrentClassLogger();
        private readonly UIApplication _uiApp;
        
        // Cached reflection types and methods for IronPython
        private static Assembly _ironPythonAssembly;
        private static Assembly _microsoftScriptingAssembly;
        private static Type _pythonType;
        private static MethodInfo _createEngineMethod;
        private static MethodInfo _createModuleMethod;
        private static MethodInfo _getBuiltinModuleMethod;
        private static bool _initialized;
        private static bool _initializationFailed;
        
        /// <summary>
        /// Initializes a new instance of the ComboBoxScriptInitializer.
        /// </summary>
        /// <param name="uiApp">The Revit UIApplication instance.</param>
        public ComboBoxScriptInitializer(UIApplication uiApp)
        {
            _uiApp = uiApp;
            EnsureInitialized();
        }

        /// <summary>
        /// Initializes the IronPython reflection types (cached for performance).
        /// </summary>
        private void EnsureInitialized()
        {
            if (_initialized || _initializationFailed)
                return;

            try
            {
                // Find IronPython assemblies from loaded assemblies
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
                    _logger.Warn("IronPython assembly not found in loaded assemblies. ComboBox scripts will not be executed.");
                    _initializationFailed = true;
                    return;
                }

                // Get the Python hosting type
                _pythonType = _ironPythonAssembly.GetType("IronPython.Hosting.Python");
                if (_pythonType == null)
                {
                    _logger.Warn("IronPython.Hosting.Python type not found.");
                    _initializationFailed = true;
                    return;
                }

                // Cache the methods we need
                _createEngineMethod = _pythonType.GetMethod("CreateEngine", new Type[0]);
                _createModuleMethod = _pythonType.GetMethod("CreateModule", 
                    new[] { typeof(object).Assembly.GetType("Microsoft.Scripting.Hosting.ScriptEngine") ?? 
                            _microsoftScriptingAssembly?.GetType("Microsoft.Scripting.Hosting.ScriptEngine"), 
                            typeof(string) });
                _getBuiltinModuleMethod = _pythonType.GetMethod("GetBuiltinModule",
                    new[] { typeof(object).Assembly.GetType("Microsoft.Scripting.Hosting.ScriptEngine") ??
                            _microsoftScriptingAssembly?.GetType("Microsoft.Scripting.Hosting.ScriptEngine") });

                _initialized = true;
                _logger.Debug("ComboBoxScriptInitializer initialized successfully.");
            }
            catch (Exception ex)
            {
                _logger.Error(ex, "Failed to initialize ComboBoxScriptInitializer.");
                _initializationFailed = true;
            }
        }

        /// <summary>
        /// Executes the __selfinit__ function in a ComboBox script file.
        /// </summary>
        /// <param name="component">The parsed ComboBox component.</param>
        /// <param name="comboBox">The Revit ComboBox control.</param>
        /// <returns>True if initialization succeeded, false otherwise.</returns>
        public bool ExecuteSelfInit(ParsedComponent component, ComboBox comboBox)
        {
            if (_initializationFailed || !_initialized)
            {
                _logger.Debug("ComboBoxScriptInitializer not available. Skipping script execution.");
                return false;
            }

            // Find script.py in the component directory
            var scriptPath = FindScriptPath(component);
            if (string.IsNullOrEmpty(scriptPath))
            {
                _logger.Debug($"No script.py found for ComboBox '{component.DisplayName}'.");
                return true; // Not an error - script is optional
            }

            object engine = null;
            try
            {
                _logger.Info($"Executing __selfinit__ for ComboBox '{component.DisplayName}' from '{scriptPath}'");
                
                // Create IronPython engine using reflection
                engine = _createEngineMethod.Invoke(null, null);
                if (engine == null)
                {
                    _logger.Error("Failed to create IronPython engine.");
                    return false;
                }

                var engineType = engine.GetType();
                
                // Set up search paths
                var searchPaths = BuildSearchPaths(component);
                _logger.Debug($"Search paths: {string.Join(", ", searchPaths)}");
                
                var getSearchPathsMethod = engineType.GetMethod("GetSearchPaths");
                var setSearchPathsMethod = engineType.GetMethod("SetSearchPaths");
                
                if (getSearchPathsMethod != null && setSearchPathsMethod != null)
                {
                    var paths = getSearchPathsMethod.Invoke(engine, null) as ICollection<string>;
                    if (paths != null)
                    {
                        foreach (var path in searchPaths)
                        {
                            paths.Add(path);
                        }
                        setSearchPathsMethod.Invoke(engine, new[] { paths });
                    }
                }

                // Create a scope/module
                var createModuleMethod = _pythonType.GetMethod("CreateModule", 
                    BindingFlags.Public | BindingFlags.Static,
                    null,
                    new[] { engineType, typeof(string) },
                    null);
                
                var scope = createModuleMethod?.Invoke(null, new[] { engine, "__main__" });
                if (scope == null)
                {
                    _logger.Error("Failed to create script scope.");
                    return false;
                }

                var scopeType = scope.GetType();
                
                // Find methods carefully to avoid ambiguous match
                var setVariableMethod = FindMethod(scopeType, "SetVariable", typeof(string), typeof(object));
                var containsVariableMethod = FindMethod(scopeType, "ContainsVariable", typeof(string));
                var getVariableMethod = FindMethod(scopeType, "GetVariable", typeof(string));

                // Set up built-in variables
                var getBuiltinMethod = _pythonType.GetMethod("GetBuiltinModule",
                    BindingFlags.Public | BindingFlags.Static,
                    null,
                    new[] { engineType },
                    null);
                
                if (getBuiltinMethod != null)
                {
                    var builtin = getBuiltinMethod.Invoke(null, new[] { engine });
                    if (builtin != null && setVariableMethod != null)
                    {
                        var builtinSetVar = FindMethod(builtin.GetType(), "SetVariable", typeof(string), typeof(object));
                        builtinSetVar?.Invoke(builtin, new object[] { "__revit__", _uiApp });
                    }
                }

                // Load Revit API assemblies into the engine
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

                // Set __file__ variable
                setVariableMethod?.Invoke(scope, new object[] { "__file__", scriptPath });

                // Execute the script file
                _logger.Debug("Creating script source from file...");
                var createScriptSourceMethod = FindMethod(engineType, "CreateScriptSourceFromFile", typeof(string), typeof(Encoding));
                
                var scriptSource = createScriptSourceMethod?.Invoke(engine, new object[] { scriptPath, Encoding.UTF8 });
                if (scriptSource == null)
                {
                    _logger.Error($"Failed to create script source from '{scriptPath}'.");
                    return false;
                }

                _logger.Debug("Executing script file...");
                var executeMethod = FindMethod(scriptSource.GetType(), "Execute", scopeType);
                try
                {
                    executeMethod?.Invoke(scriptSource, new[] { scope });
                }
                catch (TargetInvocationException scriptEx)
                {
                    var innerEx = scriptEx.InnerException;
                    _logger.Error($"Script execution error: {innerEx?.Message ?? scriptEx.Message}");
                    _logger.Error($"Script error details: {innerEx?.ToString() ?? scriptEx.ToString()}");
                    return false;
                }

                // Now check if __selfinit__ is defined and call it
                if (containsVariableMethod != null && (bool)containsVariableMethod.Invoke(scope, new object[] { "__selfinit__" }))
                {
                    _logger.Debug("Found __selfinit__ function, preparing to call it...");
                    var selfInitFunc = getVariableMethod?.Invoke(scope, new object[] { "__selfinit__" });
                    if (selfInitFunc != null)
                    {
                        // Create wrappers using Python code that accesses C# objects directly
                        // Note: We pass the C# objects directly and access them in Python
                        var wrapperCode = $@"
class _ComboBoxUIWrapper:
    def __init__(self, cmb):
        self._cmb = cmb
    def get_rvtapi_object(self):
        return self._cmb
    def activate(self):
        pass
    def deactivate(self):
        pass

class _ComponentWrapper:
    def __init__(self):
        self.directory = '{EscapeForPython(component.Directory ?? string.Empty)}'
        self.name = '{EscapeForPython(component.Name ?? string.Empty)}'
        self.display_name = '{EscapeForPython(component.DisplayName ?? string.Empty)}'
        self.unique_name = '{EscapeForPython(component.UniqueId ?? string.Empty)}'
        self.script_file = '{EscapeForPython(scriptPath)}'
        self.module_paths = []

_ui_wrapper = _ComboBoxUIWrapper(_raw_combobox)
_component = _ComponentWrapper()
";
                        // Set the raw combobox variable
                        setVariableMethod?.Invoke(scope, new object[] { "_raw_combobox", comboBox });
                        
                        // Execute wrapper code
                        _logger.Debug("Creating wrapper objects...");
                        var createFromStringMethod = FindMethod(engineType, "CreateScriptSourceFromString", typeof(string));
                        var wrapperSource = createFromStringMethod?.Invoke(engine, new object[] { wrapperCode });
                        
                        try
                        {
                            executeMethod?.Invoke(wrapperSource, new[] { scope });
                        }
                        catch (TargetInvocationException wrapperEx)
                        {
                            var innerEx = wrapperEx.InnerException;
                            _logger.Error($"Wrapper code error: {innerEx?.Message ?? wrapperEx.Message}");
                            _logger.Error($"Wrapper code: {wrapperCode}");
                            return false;
                        }

                        // Get the wrapper
                        var uiWrapper = getVariableMethod?.Invoke(scope, new object[] { "_ui_wrapper" });
                        var componentWrapper = getVariableMethod?.Invoke(scope, new object[] { "_component" });

                        // Call __selfinit__(component, ui_wrapper, uiapp)
                        // We need to use IronPython's operation to call the function
                        var operationsProperty = engineType.GetProperty("Operations");
                        var operations = operationsProperty?.GetValue(engine);
                        
                        if (operations != null)
                        {
                            var invokeMethod = FindMethod(operations.GetType(), "Invoke", typeof(object), typeof(object[]));
                            
                            _logger.Debug("Calling __selfinit__...");
                            try
                            {
                                var result = invokeMethod?.Invoke(operations, 
                                    new object[] { selfInitFunc, new object[] { componentWrapper, uiWrapper, _uiApp } });

                                // Check result - if False, log warning
                                if (result is bool boolResult && !boolResult)
                                {
                                    _logger.Warn($"__selfinit__ returned False for ComboBox '{component.DisplayName}'.");
                                    return false;
                                }

                                _logger.Info($"__selfinit__ executed successfully for ComboBox '{component.DisplayName}'.");
                                return true;
                            }
                            catch (TargetInvocationException invokeEx)
                            {
                                var innerEx = invokeEx.InnerException;
                                _logger.Error($"__selfinit__ call error: {innerEx?.Message ?? invokeEx.Message}");
                                _logger.Error($"__selfinit__ error details: {innerEx?.ToString() ?? invokeEx.ToString()}");
                                return false;
                            }
                        }
                        else
                        {
                            _logger.Error("Failed to get engine Operations for calling __selfinit__.");
                        }
                    }
                }
                else
                {
                    _logger.Debug($"No __selfinit__ function found in script for ComboBox '{component.DisplayName}'.");
                }

                return true;
            }
            catch (Exception ex)
            {
                // Unwrap TargetInvocationException to get the real error
                var actualException = ex;
                while (actualException is TargetInvocationException tie && tie.InnerException != null)
                {
                    actualException = tie.InnerException;
                }
                
                _logger.Error($"Error executing __selfinit__ for ComboBox '{component.DisplayName}': {actualException.Message}");
                _logger.Error($"Full exception: {actualException}");
                return false;
            }
            finally
            {
                // Clean up the engine
                if (engine != null)
                {
                    try
                    {
                        var runtimeProperty = engine.GetType().GetProperty("Runtime");
                        var runtime = runtimeProperty?.GetValue(engine);
                        var shutdownMethod = FindMethodByName(runtime?.GetType(), "Shutdown");
                        shutdownMethod?.Invoke(runtime, null);
                    }
                    catch
                    {
                        // Ignore cleanup errors
                    }
                }
            }
        }
        
        /// <summary>
        /// Finds a method by name and parameter types, handling ambiguous matches.
        /// </summary>
        private static MethodInfo FindMethod(Type type, string name, params Type[] parameterTypes)
        {
            if (type == null) return null;
            
            try
            {
                // First try the direct approach
                return type.GetMethod(name, parameterTypes);
            }
            catch (AmbiguousMatchException)
            {
                // If ambiguous, search manually
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
        
        /// <summary>
        /// Finds a method by name only (for parameterless methods).
        /// </summary>
        private static MethodInfo FindMethodByName(Type type, string name)
        {
            if (type == null) return null;
            
            try
            {
                return type.GetMethod(name, Type.EmptyTypes);
            }
            catch (AmbiguousMatchException)
            {
                // Return first matching method with no parameters
                foreach (var method in type.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static))
                {
                    if (method.Name == name && method.GetParameters().Length == 0)
                        return method;
                }
                return null;
            }
        }
        
        /// <summary>
        /// Escapes a string for use in Python string literals.
        /// </summary>
        private static string EscapeForPython(string value)
        {
            if (string.IsNullOrEmpty(value))
                return string.Empty;
            
            return value
                .Replace("\\", "\\\\")
                .Replace("'", "\\'")
                .Replace("\r", "\\r")
                .Replace("\n", "\\n");
        }

        /// <summary>
        /// Finds the script.py path for a ComboBox component.
        /// </summary>
        private string FindScriptPath(ParsedComponent component)
        {
            if (string.IsNullOrEmpty(component.Directory))
                return null;

            // Check for script.py in the component directory
            var scriptPath = Path.Combine(component.Directory, "script.py");
            if (File.Exists(scriptPath))
                return scriptPath;

            // Also check ScriptPath from component
            if (!string.IsNullOrEmpty(component.ScriptPath) && File.Exists(component.ScriptPath))
                return component.ScriptPath;

            return null;
        }

        /// <summary>
        /// Builds search paths for the script execution.
        /// </summary>
        private List<string> BuildSearchPaths(ParsedComponent component)
        {
            var paths = new List<string>();
            
            if (!string.IsNullOrEmpty(component.Directory))
            {
                paths.Add(component.Directory);
                
                // Add lib subdirectory if it exists
                var libPath = Path.Combine(component.Directory, "lib");
                if (Directory.Exists(libPath))
                    paths.Add(libPath);
            }

            return paths;
        }

    }
}
