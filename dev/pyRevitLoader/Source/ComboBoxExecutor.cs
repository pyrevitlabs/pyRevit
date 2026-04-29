using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
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
        
        // Keep shared runtime objects alive once and keep per-combo references attached
        // to each ComboBox instance. This prevents event handler callables from being
        // garbage-collected while avoiding duplicate references for shared objects.
        private static readonly object _aliveReferencesLock = new object();
        private static readonly HashSet<object> _sharedAliveReferences = new HashSet<object>();
        private static readonly ConditionalWeakTable<ComboBox, List<object>> _comboBoxAliveReferences =
            new ConditionalWeakTable<ComboBox, List<object>>();

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
        private LoggerStream _outputStream;

        private void EnsureEngineInitialized() {
            if (_engine != null)
                return;

            Log("Initializing shared IronPython engine for ComboBoxes");
            _scriptExecutor = new ScriptExecutor(_revit, false);
            _engine = _scriptExecutor.CreateEngine();

            // Keep reference to prevent GC
            _outputStream = new LoggerStream(_logger);

            // Redirect runtime IO - this sets sys.stdout/sys.stderr via IronPython internals
            _engine.Runtime.IO.SetOutput(_outputStream, Encoding.UTF8);
            _engine.Runtime.IO.SetErrorOutput(_outputStream, Encoding.UTF8);

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

                // Re-apply stdout/stderr redirect after SetupEnvironment
                // (SetupEnvironment may reset sys.stdout via embedded lib init)
                _engine.Runtime.IO.SetOutput(_outputStream, Encoding.UTF8);
                _engine.Runtime.IO.SetErrorOutput(_outputStream, Encoding.UTF8);

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

                // Keep Python handler objects alive so GC doesn't collect them
                var handlerObjects = new List<object>();

                // Capture engine and output stream for use in event handler lambdas.
                // Event handlers fire later when sys.stdout may have been set to None
                // by session cleanup, so we restore it before each invocation.
                var engine = _engine;
                var outStream = _outputStream;

                // Wire up __cmb_on_change__ handler
                if (hasOnChange) {
                    var handler = scope.GetVariable("__cmb_on_change__");
                    if (handler != null) {
                        handlerObjects.Add(handler);
                        comboBox.CurrentChanged += (sender, args) => {
                            try {
                                // Restore stdout in case session cleanup set it to None
                                engine.Runtime.IO.SetOutput(outStream, Encoding.UTF8);
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
                        handlerObjects.Add(handler);
                        comboBox.DropDownClosed += (sender, args) => {
                            try {
                                engine.Runtime.IO.SetOutput(outStream, Encoding.UTF8);
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
                        handlerObjects.Add(handler);
                        comboBox.DropDownOpened += (sender, args) => {
                            try {
                                engine.Runtime.IO.SetOutput(outStream, Encoding.UTF8);
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

                // Keep engine, scope, Python handler objects, and context alive.
                // This prevents GC from collecting the Python callables and
                // their parent scope, which would silently break event delivery.
                if (handlersWired) {
                    lock (_aliveReferencesLock) {
                        _sharedAliveReferences.Add(_engine);
                        _sharedAliveReferences.Add(ops);
                        _sharedAliveReferences.Add(outStream);

                        if (!_comboBoxAliveReferences.TryGetValue(comboBox, out var comboAliveReferences)) {
                            comboAliveReferences = new List<object>();
                            _comboBoxAliveReferences.Add(comboBox, comboAliveReferences);
                        }

                        comboAliveReferences.Add(scope);
                        comboAliveReferences.Add(context);
                        comboAliveReferences.AddRange(handlerObjects);
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

    /// <summary>
    /// Stream implementation that forwards Write calls to a logger Action.
    /// Used to redirect IronPython print() output to the pyRevit logger.
    /// </summary>
    internal class LoggerStream : Stream {
        private readonly Action<string> _logger;
        private readonly StringBuilder _buffer = new StringBuilder();

        public LoggerStream(Action<string> logger) {
            _logger = logger;
        }

        public override void Write(byte[] buffer, int offset, int count) {
            var text = Encoding.UTF8.GetString(buffer, offset, count);
            _buffer.Append(text);

            // Flush complete lines
            int newlineIdx;
            while ((newlineIdx = _buffer.ToString().IndexOf('\n')) >= 0) {
                var line = _buffer.ToString(0, newlineIdx).TrimEnd('\r');
                _buffer.Remove(0, newlineIdx + 1);
                _logger?.Invoke(line);
            }
        }

        public override void Flush() {
            if (_buffer.Length > 0) {
                var remaining = _buffer.ToString();
                _logger?.Invoke(remaining);
                _buffer.Clear();
            }
        }

        public override bool CanRead => false;
        public override bool CanSeek => false;
        public override bool CanWrite => true;
        public override long Length => throw new NotSupportedException();
        public override long Position {
            get => throw new NotSupportedException();
            set => throw new NotSupportedException();
        }
        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
    }
}
