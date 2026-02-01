using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Reflection;
using System.Text;
using Autodesk.Revit.UI;
using IronPython.Runtime.Exceptions;
using IronPython.Compiler;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using pyRevitAssemblyBuilder.UIManager;

namespace PyRevitLoader {
    /// <summary>
    /// Executes ComboBox event handler scripts using IronPython directly.
    /// Supports: __cmb_on_change__, __cmb_dropdown_close__, __cmb_dropdown_open__
    /// </summary>
    public class ComboBoxExecutor {
        private readonly UIApplication _revit;
        private readonly Action<string> _logger;
        private ScriptEngine _engine;
        private ScriptExecutor _scriptExecutor;
        private string _pyrevitLibPath;
        private HashSet<string> _baseSearchPaths;
        
        // Keep engines alive for ComboBoxes with event handlers
        private static readonly List<ScriptEngine> _activeEngines = new List<ScriptEngine>();

        public ComboBoxExecutor(UIApplication uiApplication, Action<string> logger = null) {
            _revit = uiApplication;
            _logger = logger;
        }

        public string Message { get; private set; } = null;

        private void Log(string message) {
            _logger?.Invoke(message);
        }

        /// <summary>
        /// Ensures the IronPython engine is initialized. Called once, reused for all ComboBoxes.
        /// </summary>
        private void EnsureEngineInitialized() {
            if (_engine != null)
                return;

            Log("Initializing shared IronPython engine for ComboBoxes");
            _scriptExecutor = new ScriptExecutor(_revit, false);
            _engine = _scriptExecutor.CreateEngine();

            // Cache base search paths
            _baseSearchPaths = new HashSet<string>(_engine.GetSearchPaths());
        }

        /// <summary>
        /// Executes event handler setup for a ComboBox script file.
        /// </summary>
        /// <param name="scriptPath">Path to the Python script file.</param>
        /// <param name="context">The ComboBoxContext to pass to event handlers.</param>
        /// <param name="comboBox">The Revit ComboBox to wire event handlers to.</param>
        /// <param name="additionalSearchPaths">Additional search paths for imports.</param>
        /// <returns>True if setup succeeded.</returns>
        public bool ExecuteEventHandlerSetup(
            string scriptPath,
            ComboBoxContext context,
            ComboBox comboBox,
            IEnumerable<string> additionalSearchPaths = null) {

            if (string.IsNullOrEmpty(scriptPath) || !File.Exists(scriptPath)) {
                return true;
            }

            // Only process Python scripts
            if (!scriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase)) {
                return true;
            }

            bool handlersWired = false;

            try {
                // Reuse the engine instead of creating new one each time
                EnsureEngineInitialized();

                // Create a fresh scope for this script (but reuse engine)
                var scope = _scriptExecutor.SetupEnvironment(_engine);

                // Setup search paths for this specific component
                SetupSearchPathsForComponent(_engine, context.directory, additionalSearchPaths);

                // Set __file__ variable
                scope.SetVariable("__file__", scriptPath);

                // Execute the script file to define event handlers
                var script = _engine.CreateScriptSourceFromFile(scriptPath, Encoding.UTF8, SourceCodeKind.File);

                // Compile with proper options
                var compilerOptions = (PythonCompilerOptions)_engine.GetCompilerOptions(scope);
                compilerOptions.ModuleName = "__main__";
                compilerOptions.Module |= IronPython.Runtime.ModuleOptions.Initialize;

                var errors = new ErrorReporter();
                var compiled = script.Compile(compilerOptions, errors);
                if (compiled == null) {
                    Message = string.Join("\r\n", "Compilation failed:", string.Join("\r\n", errors.Errors.ToArray()));
                    Log(Message);
                    return false;
                }

                try {
                    script.Execute(scope);
                }
                catch (SystemExitException) {
                    return true;
                }
                catch (Exception ex) {
                    Message = $"Script execution error: {ex.Message}";
                    Log(Message);
                    return false;
                }

                // Check for event handlers
                bool hasOnChange = scope.ContainsVariable("__cmb_on_change__");
                bool hasDropdownClose = scope.ContainsVariable("__cmb_dropdown_close__");
                bool hasDropdownOpen = scope.ContainsVariable("__cmb_dropdown_open__");

                if (!hasOnChange && !hasDropdownClose && !hasDropdownOpen) {
                    Log($"No event handlers found in script for ComboBox '{context.name}'.");
                    return true;
                }

                Log($"Found event handlers for ComboBox '{context.name}', wiring up...");
                var ops = _engine.Operations;

                // Wire up __cmb_on_change__ handler
                if (hasOnChange) {
                    var handler = scope.GetVariable("__cmb_on_change__");
                    if (handler != null) {
                        comboBox.CurrentChanged += (sender, args) => {
                            try {
                                ops.Invoke(handler, sender, args, context);
                            }
                            catch (Exception ex) {
                                Log($"Error in __cmb_on_change__: {ex.Message}");
                            }
                        };
                        Log("Wired __cmb_on_change__ handler");
                        handlersWired = true;
                    }
                }

                // Wire up __cmb_dropdown_close__ handler
                if (hasDropdownClose) {
                    var handler = scope.GetVariable("__cmb_dropdown_close__");
                    if (handler != null) {
                        comboBox.DropDownClosed += (sender, args) => {
                            try {
                                ops.Invoke(handler, sender, args, context);
                            }
                            catch (Exception ex) {
                                Log($"Error in __cmb_dropdown_close__: {ex.Message}");
                            }
                        };
                        Log("Wired __cmb_dropdown_close__ handler");
                        handlersWired = true;
                    }
                }

                // Wire up __cmb_dropdown_open__ handler
                if (hasDropdownOpen) {
                    var handler = scope.GetVariable("__cmb_dropdown_open__");
                    if (handler != null) {
                        comboBox.DropDownOpened += (sender, args) => {
                            try {
                                ops.Invoke(handler, sender, args, context);
                            }
                            catch (Exception ex) {
                                Log($"Error in __cmb_dropdown_open__: {ex.Message}");
                            }
                        };
                        Log("Wired __cmb_dropdown_open__ handler");
                        handlersWired = true;
                    }
                }

                // Keep engine alive if handlers were wired
                if (handlersWired) {
                    lock (_activeEngines) {
                        _activeEngines.Add(_engine);
                    }
                    Log($"Event handlers set up successfully for ComboBox '{context.name}'.");
                }

                return true;
            }
            catch (Exception ex) {
                Message = $"ComboBox executor error: {ex.Message}";
                Log(Message);
                return false;
            }
        }

        /// <summary>
        /// Sets up search paths for a specific component, reusing cached base paths.
        /// </summary>
        private void SetupSearchPathsForComponent(ScriptEngine engine, string componentDirectory, IEnumerable<string> additionalSearchPaths) {
            // Start with cached base paths
            var paths = new List<string>(_baseSearchPaths);

            // Add component directory
            if (!string.IsNullOrEmpty(componentDirectory) && Directory.Exists(componentDirectory)) {
                if (!paths.Contains(componentDirectory))
                    paths.Add(componentDirectory);

                // Add lib subdirectory if exists
                var libPath = Path.Combine(componentDirectory, "lib");
                if (Directory.Exists(libPath) && !paths.Contains(libPath))
                    paths.Add(libPath);
            }

            // Find and add pyrevitlib (cached)
            if (_pyrevitLibPath == null) {
                _pyrevitLibPath = FindPyRevitLib(componentDirectory) ?? string.Empty;
            }

            if (!string.IsNullOrEmpty(_pyrevitLibPath) && !paths.Contains(_pyrevitLibPath)) {
                paths.Add(_pyrevitLibPath);

                // Add site-packages
                var pyrevitRoot = Path.GetDirectoryName(_pyrevitLibPath);
                if (!string.IsNullOrEmpty(pyrevitRoot)) {
                    var sitePackages = Path.Combine(pyrevitRoot, "site-packages");
                    if (Directory.Exists(sitePackages) && !paths.Contains(sitePackages))
                        paths.Add(sitePackages);
                }
            }

            // Add additional search paths
            if (additionalSearchPaths != null) {
                foreach (var path in additionalSearchPaths) {
                    if (!string.IsNullOrEmpty(path) && !paths.Contains(path))
                        paths.Add(path);
                }
            }

            engine.SetSearchPaths(paths);
        }

        private string FindPyRevitLib(string componentDirectory) {
            // Strategy 1: Navigate up from component directory
            if (!string.IsNullOrEmpty(componentDirectory)) {
                var current = new DirectoryInfo(componentDirectory);
                int depth = 0;
                while (current != null && depth < 20) {
                    var pyrevitLibPath = Path.Combine(current.FullName, "pyrevitlib");
                    if (Directory.Exists(pyrevitLibPath)) {
                        return pyrevitLibPath;
                    }
                    current = current.Parent;
                    depth++;
                }
            }

            // Strategy 2: Find from this assembly location
            try {
                var assemblyPath = Assembly.GetExecutingAssembly().Location;
                if (!string.IsNullOrEmpty(assemblyPath)) {
                    var assemblyDir = new DirectoryInfo(Path.GetDirectoryName(assemblyPath));
                    // Navigate up: engines -> netfx -> bin -> pyRevit root
                    var current = assemblyDir?.Parent?.Parent?.Parent?.Parent;
                    if (current != null) {
                        var pyrevitLibPath = Path.Combine(current.FullName, "pyrevitlib");
                        if (Directory.Exists(pyrevitLibPath)) {
                            return pyrevitLibPath;
                        }
                    }
                }
            }
            catch { }

            return null;
        }
    }
}
