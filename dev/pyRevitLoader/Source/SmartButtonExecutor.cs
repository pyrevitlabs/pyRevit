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
    /// Based on ScriptExecutor but specialized for __selfinit__ execution.
    /// </summary>
    public class SmartButtonExecutor {
        private readonly UIApplication _revit;
        private readonly Action<string> _logger;

        public SmartButtonExecutor(UIApplication uiApplication, Action<string> logger = null) {
            _revit = uiApplication;
            _logger = logger;
        }

        public string Message { get; private set; } = null;

        private void Log(string message) {
            _logger?.Invoke(message);
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
                Log($"Script not found: {scriptPath}");
                return true; // Don't deactivate
            }

            // Only process Python scripts
            if (!scriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase)) {
                return true;
            }

            ScriptEngine engine = null;
            try {
                Log($"Executing __selfinit__ for '{context.name}'");

                // Create and setup engine (reuse ScriptExecutor's approach)
                var scriptExecutor = new ScriptExecutor(_revit, false);
                engine = scriptExecutor.CreateEngine();
                
                // Setup environment with embedded lib and builtins
                var scope = scriptExecutor.SetupEnvironment(engine);

                // Setup additional search paths
                SetupSearchPaths(engine, context.directory, additionalSearchPaths);

                // Set __file__ variable
                scope.SetVariable("__file__", scriptPath);

                // Execute the script file to define __selfinit__
                Log($"Loading script: {scriptPath}");
                var script = engine.CreateScriptSourceFromFile(scriptPath, Encoding.UTF8, SourceCodeKind.File);

                // Compile with proper options
                var compilerOptions = (PythonCompilerOptions)engine.GetCompilerOptions(scope);
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
                    // Script exited, that's fine
                    return true;
                }
                catch (Exception ex) {
                    Message = $"Script execution error: {ex.Message}";
                    Log(Message);
                    LogSearchPaths(engine);
                    return true;
                }

                // Check if __selfinit__ is defined
                if (!scope.ContainsVariable("__selfinit__")) {
                    Log($"No __selfinit__ found in script for '{context.name}'");
                    return true;
                }

                // Get the __selfinit__ function
                var selfInitFunc = scope.GetVariable("__selfinit__");
                if (selfInitFunc == null) {
                    return true;
                }

                // The pythonic loader passes (smartbutton, smartbutton_ui, HOST_APP.uiapp)
                // We pass the same SmartButtonContext for both to provide all functionality
                Log($"Calling __selfinit__ for '{context.name}'");
                
                try {
                    // Call __selfinit__(script_cmp, ui_button_cmp, __rvt__)
                    var ops = engine.Operations;
                    var result = ops.Invoke(selfInitFunc, context, context, _revit);
                    
                    // If __selfinit__ returns False, the button should be deactivated
                    if (result is bool boolResult) {
                        if (boolResult == false) {
                            Log($"__selfinit__ returned False for '{context.name}' - deactivating button");
                            return false;
                        }
                    }

                    Log($"__selfinit__ completed successfully for '{context.name}'");
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
            finally {
                if (engine != null) {
                    try {
                        engine.Runtime.Shutdown();
                    }
                    catch { }
                }
            }
        }

        private void SetupSearchPaths(ScriptEngine engine, string componentDirectory, IEnumerable<string> additionalSearchPaths) {
            var paths = engine.GetSearchPaths();

            // Add component directory
            if (!string.IsNullOrEmpty(componentDirectory) && Directory.Exists(componentDirectory)) {
                paths.Add(componentDirectory);

                // Add lib subdirectory if exists
                var libPath = Path.Combine(componentDirectory, "lib");
                if (Directory.Exists(libPath))
                    paths.Add(libPath);
            }

            // Find and add pyrevitlib
            var pyrevitLib = FindPyRevitLib(componentDirectory);
            if (!string.IsNullOrEmpty(pyrevitLib)) {
                paths.Add(pyrevitLib);
                Log($"Added pyrevitlib: {pyrevitLib}");

                // Add site-packages
                var pyrevitRoot = Path.GetDirectoryName(pyrevitLib);
                if (!string.IsNullOrEmpty(pyrevitRoot)) {
                    var sitePackages = Path.Combine(pyrevitRoot, "site-packages");
                    if (Directory.Exists(sitePackages))
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
