using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text;
using Autodesk.Revit.UI;
using IronPython.Compiler;
using IronPython.Runtime.Exceptions;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using pyRevitAssemblyBuilder.UIManager;

namespace PyRevitLoader
{
    /// <summary>
    /// Runs .checkbox bundle scripts in a shared IronPython engine and wires their handlers:
    /// <c>__chk_init__(ctx)</c> once per load, and <c>__chk_on_change__(sender, args, ctx)</c>
    /// whenever the checkbox's <c>IsChecked</c> changes.
    /// </summary>
    /// <remarks>
    /// Important: handlers run on the UI thread from WPF property-change notifications, outside
    /// Revit API context. They can read and store settings but must not start transactions.
    /// The checkbox is taken as <see cref="INotifyPropertyChanged"/> so this assembly does not
    /// need an AdWindows reference.
    /// </remarks>
    public class CheckBoxExecutor
    {
        private const string SessionSlotName = "CheckBoxExecutor";
        private const string InitHandlerName = "__chk_init__";
        private const string ChangeHandlerName = "__chk_on_change__";
        private const string CheckedPropertyName = "IsChecked";

        private static readonly object _aliveReferencesLock = new object();
        private static readonly ConditionalWeakTable<INotifyPropertyChanged, List<object>> _aliveReferences =
            new ConditionalWeakTable<INotifyPropertyChanged, List<object>>();

        private readonly UIApplication _revit;
        private readonly Action<string> _logger;
        private readonly List<Action> _handlerDetachers = new List<Action>();
        private readonly List<INotifyPropertyChanged> _wiredCheckBoxes = new List<INotifyPropertyChanged>();
        private ScriptEngine _engine;
        private ScriptExecutor _scriptExecutor;
        private LoggerStream _outputStream;
        private HashSet<string> _baseSearchPaths;
        private string _pyrevitLibPath;
        private bool _released;
        private bool _sessionSlotClaimed;

        private enum ScriptRunResult
        {
            Completed,
            Exited,
            Failed
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="CheckBoxExecutor"/> class.
        /// </summary>
        /// <param name="logger">Receives script output and setup diagnostics.</param>
        public CheckBoxExecutor(UIApplication uiApplication, Action<string> logger = null)
        {
            _revit = uiApplication;
            _logger = logger;
        }

        /// <summary>
        /// Releases the engine and handlers that the previous session load's executor left behind.
        /// </summary>
        /// <param name="onError">Receives the failure of the previous release, if it threw.</param>
        /// <remarks>
        /// Invariant: called by reflection from <c>CheckBoxScriptInitializer</c> at the start of
        /// every session load; keep the name and signature.
        /// </remarks>
        public static void ReleasePreviousSession(Action<string> onError)
        {
            SessionResourceRegistry.Release(SessionSlotName, onError);
        }

        /// <summary>
        /// Runs <paramref name="scriptPath"/>, calls its <c>__chk_init__</c>, then subscribes its
        /// <c>__chk_on_change__</c> to <paramref name="checkBox"/>.
        /// </summary>
        /// <param name="scopeVariables">Values set in the script's own module scope before it runs, such as
        /// <c>__commandname__</c>, so <c>EXEC_PARAMS</c> resolves this checkbox's identity without touching
        /// other checkboxes.</param>
        /// <returns>False when the script fails to compile or run; true otherwise, including when it defines no handlers.</returns>
        /// <remarks>
        /// Invariant: called by reflection from <c>CheckBoxScriptInitializer</c>; keep the name and signature.
        /// Note: <c>__chk_init__</c> runs before the change handler is subscribed, so restoring a saved
        /// state there does not raise <c>__chk_on_change__</c>.
        /// </remarks>
        public bool ExecuteEventHandlerSetup(
            string scriptPath,
            CheckBoxContext context,
            INotifyPropertyChanged checkBox,
            IEnumerable<string> additionalSearchPaths = null,
            IDictionary<string, object> scopeVariables = null)
        {
            if (_released || !IsPythonScript(scriptPath))
                return true;

            try
            {
                EnsureEngineInitialized();
                var scope = _scriptExecutor.SetupEnvironment(_engine);
                RedirectOutput();
                SetupSearchPathsForComponent(context.directory, additionalSearchPaths);
                scope.SetVariable("__file__", scriptPath);
                if (scopeVariables != null)
                {
                    foreach (var variable in scopeVariables)
                        scope.SetVariable(variable.Key, variable.Value);
                }

                var runResult = RunScript(scriptPath, scope);
                if (runResult != ScriptRunResult.Completed)
                    return runResult == ScriptRunResult.Exited;

                var searchPaths = new List<string>(_engine.GetSearchPaths());
                var ops = _engine.Operations;
                if (scope.ContainsVariable(InitHandlerName))
                    InvokeHandler(ops, searchPaths, InitHandlerName, scope.GetVariable(InitHandlerName), context);

                if (scope.ContainsVariable(ChangeHandlerName))
                    WireChangeHandler(checkBox, ops, searchPaths, scope, context);

                return true;
            }
            catch (Exception ex)
            {
                Log($"CheckBox executor error for '{context?.name}': {ex.Message}");
                return false;
            }
        }

        private static bool IsPythonScript(string scriptPath)
        {
            return !string.IsNullOrEmpty(scriptPath)
                && scriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase)
                && File.Exists(scriptPath);
        }

        private void Log(string message)
        {
            _logger?.Invoke(message);
        }

        private void EnsureEngineInitialized()
        {
            if (_engine != null)
                return;

            if (!_sessionSlotClaimed)
            {
                SessionResourceRegistry.Replace(SessionSlotName, ReleaseSessionResources, _logger);
                _sessionSlotClaimed = true;
            }

            Log("Initializing shared IronPython engine for CheckBoxes");
            _scriptExecutor = new ScriptExecutor(_revit, false);
            _engine = _scriptExecutor.CreateEngine();
            _outputStream = new LoggerStream(_logger);
            RedirectOutput();
            _baseSearchPaths = new HashSet<string>(_engine.GetSearchPaths());
        }

        /// <summary>
        /// Points the engine's stdout and stderr at the pyRevit logger.
        /// </summary>
        /// <remarks>
        /// Note: also called before every handler call, because session cleanup and
        /// <c>SetupEnvironment</c> can replace <c>sys.stdout</c> after the engine is created.
        /// </remarks>
        private void RedirectOutput()
        {
            var engine = _engine;
            if (engine == null)
                return;

            engine.Runtime.IO.SetOutput(_outputStream, Encoding.UTF8);
            engine.Runtime.IO.SetErrorOutput(_outputStream, Encoding.UTF8);
        }

        private ScriptRunResult RunScript(string scriptPath, ScriptScope scope)
        {
            var script = _engine.CreateScriptSourceFromFile(scriptPath, Encoding.UTF8, SourceCodeKind.File);
            var compilerOptions = (PythonCompilerOptions)_engine.GetCompilerOptions(scope);
            compilerOptions.ModuleName = "__main__";
            compilerOptions.Module |= IronPython.Runtime.ModuleOptions.Initialize;

            var errors = new ErrorReporter();
            if (script.Compile(compilerOptions, errors) == null)
            {
                Log("Compilation failed:\r\n" + string.Join("\r\n", errors.Errors));
                return ScriptRunResult.Failed;
            }

            try
            {
                script.Execute(scope);
                return ScriptRunResult.Completed;
            }
            catch (SystemExitException)
            {
                return ScriptRunResult.Exited;
            }
            catch (Exception ex)
            {
                Log($"Script execution error in '{scriptPath}': {ex.Message}");
                return ScriptRunResult.Failed;
            }
        }

        private void WireChangeHandler(INotifyPropertyChanged checkBox, ObjectOperations ops, List<string> searchPaths, ScriptScope scope, CheckBoxContext context)
        {
            object handler = scope.GetVariable(ChangeHandlerName);
            PropertyChangedEventHandler onChange = (sender, args) =>
            {
                if (args.PropertyName == CheckedPropertyName)
                    InvokeHandler(ops, searchPaths, ChangeHandlerName, handler, sender, args, context);
            };
            checkBox.PropertyChanged += onChange;

            lock (_aliveReferencesLock)
            {
                _handlerDetachers.Add(() => checkBox.PropertyChanged -= onChange);
                _wiredCheckBoxes.Add(checkBox);
                _aliveReferences.GetOrCreateValue(checkBox).AddRange(
                    new object[] { _engine, ops, _outputStream, scope, context, handler, onChange });
            }
            Log($"Wired {ChangeHandlerName} for CheckBox '{context.name}'.");
        }

        /// <summary>
        /// Calls a handler with the engine's output and search paths set for its checkbox.
        /// </summary>
        /// <remarks>
        /// Note: all checkboxes share one engine, whose <c>sys.path</c> holds the paths of the script
        /// that ran last. Each call therefore restores the paths captured right after its own
        /// checkbox's script ran, so imports inside a handler find that bundle's <c>lib</c> folder.
        /// </remarks>
        private void InvokeHandler(ObjectOperations ops, ICollection<string> searchPaths, string handlerName, object handler, params object[] args)
        {
            try
            {
                RedirectOutput();
                _engine?.SetSearchPaths(searchPaths);
                ops.Invoke(handler, args);
            }
            catch (Exception ex)
            {
                Log($"Error in {handlerName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Detaches the handlers this executor wired, drops their references and shuts its engine down.
        /// Registered with <see cref="SessionResourceRegistry"/> so the next session load runs it.
        /// </summary>
        private void ReleaseSessionResources()
        {
            Log("Releasing CheckBox engine of the previous session");
            lock (_aliveReferencesLock)
            {
                _released = true;

                foreach (var detach in _handlerDetachers)
                {
                    try
                    {
                        detach();
                    }
                    catch (Exception ex)
                    {
                        Log($"Failed to detach CheckBox handler: {ex.Message}");
                    }
                }
                _handlerDetachers.Clear();

                foreach (var checkBox in _wiredCheckBoxes)
                    _aliveReferences.Remove(checkBox);
                _wiredCheckBoxes.Clear();
            }

            var engine = _engine;
            _engine = null;
            _scriptExecutor = null;
            _outputStream = null;
            _baseSearchPaths = null;

            try
            {
                engine?.Runtime.Shutdown();
            }
            catch (Exception ex)
            {
                Log($"Failed to shut down CheckBox engine: {ex.Message}");
            }
        }

        private void SetupSearchPathsForComponent(string componentDirectory, IEnumerable<string> additionalSearchPaths)
        {
            var paths = new List<string>(_baseSearchPaths);

            void AddPath(string path)
            {
                if (!string.IsNullOrEmpty(path) && !paths.Contains(path))
                    paths.Add(path);
            }

            if (!string.IsNullOrEmpty(componentDirectory) && Directory.Exists(componentDirectory))
            {
                AddPath(componentDirectory);
                var libPath = Path.Combine(componentDirectory, "lib");
                if (Directory.Exists(libPath))
                    AddPath(libPath);
            }

            if (additionalSearchPaths != null)
            {
                foreach (var path in additionalSearchPaths)
                    AddPath(path);
            }

            if (_pyrevitLibPath == null)
                _pyrevitLibPath = FindPyRevitLib(componentDirectory) ?? string.Empty;

            if (_pyrevitLibPath.Length > 0)
            {
                AddPath(_pyrevitLibPath);
                var pyrevitRoot = Path.GetDirectoryName(_pyrevitLibPath);
                var sitePackages = string.IsNullOrEmpty(pyrevitRoot) ? null : Path.Combine(pyrevitRoot, "site-packages");
                if (sitePackages != null && Directory.Exists(sitePackages))
                    AddPath(sitePackages);
            }

            _engine.SetSearchPaths(paths);
        }

        /// <summary>
        /// Finds the clone's <c>pyrevitlib</c> folder above the bundle, falling back to the one
        /// above this assembly (<c>bin/netfx|netcore/engines/IPYxxx</c>).
        /// </summary>
        private string FindPyRevitLib(string componentDirectory)
        {
            var current = string.IsNullOrEmpty(componentDirectory) ? null : new DirectoryInfo(componentDirectory);
            for (var depth = 0; current != null && depth < 20; depth++)
            {
                var candidate = Path.Combine(current.FullName, "pyrevitlib");
                if (Directory.Exists(candidate))
                    return candidate;
                current = current.Parent;
            }

            try
            {
                var assemblyDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                var pyrevitRoot = string.IsNullOrEmpty(assemblyDir)
                    ? null
                    : new DirectoryInfo(assemblyDir).Parent?.Parent?.Parent?.Parent;
                var candidate = pyrevitRoot == null ? null : Path.Combine(pyrevitRoot.FullName, "pyrevitlib");
                if (candidate != null && Directory.Exists(candidate))
                    return candidate;
            }
            catch (Exception ex)
            {
                Log($"Could not locate pyrevitlib from the loader assembly: {ex.Message}");
            }

            return null;
        }
    }
}
