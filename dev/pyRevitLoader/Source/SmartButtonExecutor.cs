using System;
using System.Linq;
using System.Text;
using System.IO;
using System.Collections.Generic;
using System.Reflection;
using IronPython.Runtime.Exceptions;
using IronPython.Compiler;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.UIManager;

namespace PyRevitLoader {
    /// <summary>
    /// Executes SmartButton __selfinit__ scripts.
    /// Creating a new engine per button was the main performance bottleneck.
    /// </summary>
    public class SmartButtonExecutor {
        private readonly UIApplication _revit;
        private readonly Action<string> _logger;
        private ScriptEngine _engine;
        private ScriptExecutor _scriptExecutor;
        private string _pyrevitLibPath;
        private HashSet<string> _baseSearchPaths;

        public SmartButtonExecutor(UIApplication uiApplication, Action<string> logger = null) {
            _revit = uiApplication;
            _logger = logger;
        }

        public string Message { get; private set; } = null;

        private void Log(string message) {
            _logger?.Invoke(message);
        }
        
        /// <summary>
        /// Ensures the IronPython engine is initialized. Called once, reused for all buttons.
        /// </summary>
        private void EnsureEngineInitialized() {
            if (_engine != null)
                return;
                
            Log("Initializing shared IronPython engine for SmartButtons");
            _scriptExecutor = new ScriptExecutor(_revit, false);
            _engine = _scriptExecutor.CreateEngine();
            
            // Cache base search paths
            _baseSearchPaths = new HashSet<string>(_engine.GetSearchPaths());
        }

        /// <summary>
        /// Executes the __selfinit__ function for a SmartButton.
        /// </summary>
        /// <param name="scriptPath">Path to the Python script file.</param>
        /// <param name="context">The SmartButtonContext to pass to the script.</param>
        /// <param name="additionalSearchPaths">Additional search paths for imports.</param>
        /// <returns>True if initialization succeeded, false if the button should be deactivated.</returns>
        public bool ExecuteSelfInit(
            string scriptPath,
            SmartButtonContext context,
            IEnumerable<string> additionalSearchPaths = null) {
            
            if (string.IsNullOrEmpty(scriptPath) || !File.Exists(scriptPath)) {
                return true; // Don't deactivate
            }

            // Only process Python scripts for __selfinit__
            if (!scriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase)) {
                return true;
            }

            try {
                // Reuse the engine instead of creating new one each time
                EnsureEngineInitialized();
                
                // Create a fresh scope for this script (but reuse engine)
                var scope = _scriptExecutor.SetupEnvironment(_engine);

                // Setup search paths for this specific component
                SetupSearchPathsForComponent(_engine, context.directory, additionalSearchPaths);

                // Set __file__ variable
                scope.SetVariable("__file__", scriptPath);

                // Execute the script file to define __selfinit__
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
                    return true;
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
                    return true;
                }

                // Check if __selfinit__ is defined
                if (!scope.ContainsVariable("__selfinit__")) {
                    return true;
                }

                // Get the __selfinit__ function
                var selfInitFunc = scope.GetVariable("__selfinit__");
                if (selfInitFunc == null) {
                    return true;
                }

                try {
                    // Call __selfinit__(script_cmp, ui_button_cmp, __rvt__)
                    var ops = _engine.Operations;
                    var result = ops.Invoke(selfInitFunc, context, context, _revit);
                    
                    // If __selfinit__ returns False, the button should be deactivated
                    if (result is bool boolResult && boolResult == false) {
                        Log($"__selfinit__ returned False for '{context.name}' - deactivating button");
                        return false;
                    }

                    return true;
                }
                catch (Exception ex) {
                    Message = $"Error executing __selfinit__: {ex.Message}";
                    Log(Message);
                    return true;
                }
            }
            catch (Exception ex) {
                Message = $"SmartButton executor error: {ex.Message}";
                Log(Message);
                return true;
            }
            // NOTE: We no longer shutdown the engine after each execution
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

        private void LogSearchPaths(ScriptEngine engine) {
            try {
                var paths = engine.GetSearchPaths();
                Log($"Search paths ({paths.Count} total):");
                foreach (var p in paths) {
                    Log($"  - {p}");
                }
            }
            catch { }
        }
    }
}
