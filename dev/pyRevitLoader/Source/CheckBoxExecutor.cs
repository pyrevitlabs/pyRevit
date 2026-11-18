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
    /// Note: all checkboxes share one engine, so they share <c>sys.path</c> and <c>sys.modules</c>.
    /// Each script run and handler call therefore starts from its own checkbox's search paths and
    /// modules and hands them back when it ends. A checkbox owns the modules it loaded from its own
    /// search paths, which are all of them except the engine's base paths, <c>pyrevitlib</c> and
    /// <c>site-packages</c>, so two bundles can ship <c>lib</c> modules with the same name while
    /// pyRevit and the standard library are still imported once for all checkboxes.
    /// </remarks>
    public class CheckBoxExecutor
    {
        private const string SessionSlotName = "CheckBoxExecutor";
        private const string InitHandlerName = "__chk_init__";
        private const string ChangeHandlerName = "__chk_on_change__";
        private const string CheckedPropertyName = "IsChecked";
        private const string MainModuleName = "__main__";

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
        private HashSet<string> _sharedModuleRoots;
        private CheckBoxState _activeState;
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
        /// One checkbox's share of the engine: the <c>sys.path</c> its code runs with and the modules
        /// it owns, which stay out of <c>sys.modules</c> while it is not the active checkbox.
        /// </summary>
        private sealed class CheckBoxState
        {
            public CheckBoxState(string name, List<string> searchPaths)
            {
                Name = name;
                SearchPaths = searchPaths;
            }

            public string Name { get; }

            public List<string> SearchPaths { get; }

            public Dictionary<string, object> Modules { get; } = new Dictionary<string, object>(StringComparer.Ordinal);

            public Dictionary<string, object> HiddenModules { get; } = new Dictionary<string, object>(StringComparer.Ordinal);
        }

        /// <summary>
        /// What <see cref="EnterCheckBox"/> replaced: the checkbox that was active before, or the
        /// engine's <c>sys.path</c> when none was.
        /// </summary>
        private sealed class ReplacedEngineState
        {
            public ReplacedEngineState(CheckBoxState previousState, List<string> searchPaths)
            {
                PreviousState = previousState;
                SearchPaths = searchPaths;
            }

            public CheckBoxState PreviousState { get; }

            public List<string> SearchPaths { get; }
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

                var state = new CheckBoxState(context.name, new List<string>(_engine.GetSearchPaths()));
                var replaced = EnterCheckBox(state);
                ScriptRunResult runResult;
                try
                {
                    runResult = RunScript(scriptPath, scope);
                }
                finally
                {
                    LeaveCheckBox(state, replaced);
                }

                if (runResult != ScriptRunResult.Completed)
                    return runResult == ScriptRunResult.Exited;

                var ops = _engine.Operations;
                if (scope.ContainsVariable(InitHandlerName))
                    InvokeHandler(ops, state, InitHandlerName, scope.GetVariable(InitHandlerName), context);

                if (scope.ContainsVariable(ChangeHandlerName))
                    WireChangeHandler(checkBox, ops, state, scope, context);

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
            _sharedModuleRoots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var path in _baseSearchPaths)
                AddSharedModuleRoot(path);
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

        private void WireChangeHandler(INotifyPropertyChanged checkBox, ObjectOperations ops, CheckBoxState state, ScriptScope scope, CheckBoxContext context)
        {
            object handler = scope.GetVariable(ChangeHandlerName);
            PropertyChangedEventHandler onChange = (sender, args) =>
            {
                if (args.PropertyName == CheckedPropertyName)
                    InvokeHandler(ops, state, ChangeHandlerName, handler, sender, args, context);
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
        /// Calls a handler with the engine's output, search paths and modules set for its checkbox.
        /// </summary>
        /// <remarks>
        /// Note: the engine's <c>sys.path</c> and <c>sys.modules</c> hold whatever the last script or
        /// handler left there. Each call therefore enters its checkbox first, so imports inside a
        /// handler find that bundle's <c>lib</c> folder and its own modules, and leaves it afterwards,
        /// so the paths and modules a handler adds, including in <c>__chk_init__</c>, stay with that
        /// checkbox for its later calls. Handlers of linked checkboxes can raise each other before
        /// they return, for example A ticks B and B unticks A: entering B sets A aside, the nested
        /// call to A sets B aside, and each leave brings back the checkbox that was active before, so
        /// every call runs with its own checkbox's paths and modules. A call raised while its own
        /// checkbox is already active keeps the running environment as it is.
        /// </remarks>
        private void InvokeHandler(ObjectOperations ops, CheckBoxState state, string handlerName, object handler, params object[] args)
        {
            ReplacedEngineState replaced = null;
            try
            {
                RedirectOutput();
                replaced = EnterCheckBox(state);
                ops.Invoke(handler, args);
            }
            catch (Exception ex)
            {
                Log($"Error in {handlerName}: {ex.Message}");
            }
            finally
            {
                LeaveCheckBox(state, replaced);
            }
        }

        /// <summary>
        /// Makes the checkbox the active one: sets the previously active checkbox aside, then points
        /// <c>sys.path</c> at this checkbox's saved paths and puts its own modules back into
        /// <c>sys.modules</c>.
        /// </summary>
        /// <returns>What this replaced, for <see cref="LeaveCheckBox"/> to put back; null when the
        /// checkbox is already active or the engine is released.</returns>
        private ReplacedEngineState EnterCheckBox(CheckBoxState state)
        {
            var engine = _engine;
            var sharedRoots = _sharedModuleRoots;
            if (engine == null || sharedRoots == null || ReferenceEquals(_activeState, state))
                return null;

            var replaced = new ReplacedEngineState(_activeState, new List<string>(engine.GetSearchPaths()));
            if (_activeState != null)
                Deactivate(engine, _activeState, sharedRoots);
            Activate(engine, state);
            _activeState = state;
            return replaced;
        }

        /// <summary>
        /// Sets the checkbox aside and makes the previously active checkbox active again, or puts the
        /// engine's previous <c>sys.path</c> back when there was none.
        /// </summary>
        /// <param name="replaced">What <see cref="EnterCheckBox"/> returned; null, which does nothing,
        /// when this call did not enter the checkbox.</param>
        /// <remarks>
        /// Warning: runs in <c>finally</c> blocks inside ribbon event handlers, so it logs failures
        /// instead of throwing them into AdWindows.
        /// </remarks>
        private void LeaveCheckBox(CheckBoxState state, ReplacedEngineState replaced)
        {
            if (replaced == null)
                return;

            var engine = _engine;
            var sharedRoots = _sharedModuleRoots;
            try
            {
                if (engine == null || sharedRoots == null)
                    return;

                Deactivate(engine, state, sharedRoots);
                if (replaced.PreviousState != null)
                    Activate(engine, replaced.PreviousState);
                else
                    engine.SetSearchPaths(replaced.SearchPaths);
            }
            catch (Exception ex)
            {
                Log($"Failed to set aside the modules of CheckBox '{state.Name}': {ex.Message}");
            }
            finally
            {
                _activeState = replaced.PreviousState;
            }
        }

        /// <summary>
        /// Points <c>sys.path</c> at the checkbox's saved paths and puts its own modules into
        /// <c>sys.modules</c>, keeping the shared modules they hide for <see cref="Deactivate"/>.
        /// </summary>
        private static void Activate(ScriptEngine engine, CheckBoxState state)
        {
            engine.SetSearchPaths(state.SearchPaths);
            var modules = GetSysModules(engine);
            state.HiddenModules.Clear();
            foreach (var module in state.Modules)
            {
                if (modules.TryGetValue(module.Key, out var hiddenModule))
                    state.HiddenModules[module.Key] = hiddenModule;
                modules[module.Key] = module.Value;
            }
        }

        /// <summary>
        /// Saves <c>sys.path</c> into the checkbox, moves the modules it owns out of
        /// <c>sys.modules</c> and into the checkbox, and puts back the shared modules they hid.
        /// </summary>
        /// <remarks>
        /// Invariant: only call it for the active checkbox. Its saved modules are rebuilt from
        /// <c>sys.modules</c>, which holds all of them only while it is active.
        /// </remarks>
        private static void Deactivate(ScriptEngine engine, CheckBoxState state, ICollection<string> sharedRoots)
        {
            var currentPaths = new List<string>(engine.GetSearchPaths());
            state.SearchPaths.Clear();
            state.SearchPaths.AddRange(currentPaths);

            var modules = GetSysModules(engine);
            state.Modules.Clear();
            foreach (var name in FindOwnModuleNames(modules, state.SearchPaths, sharedRoots))
            {
                state.Modules[name] = modules[name];
                modules.Remove(name);
            }

            foreach (var module in state.HiddenModules)
            {
                if (!modules.ContainsKey(module.Key))
                    modules[module.Key] = module.Value;
            }
            state.HiddenModules.Clear();
        }

        /// <summary>
        /// Lists the <c>sys.modules</c> entries a checkbox owns: modules whose file lies under one of
        /// its search paths that is not shared, and the other entries inside such a package, including
        /// the <c>None</c> entries IronPython 2 records for failed implicit relative imports.
        /// </summary>
        /// <remarks>
        /// Invariant: a module whose file lies under a shared root is never owned, even inside an
        /// owned package that extends its <c>__path__</c> into <c>site-packages</c>.
        /// </remarks>
        private static List<string> FindOwnModuleNames(IDictionary<object, object> modules, IEnumerable<string> searchPaths, ICollection<string> sharedRoots)
        {
            var names = new List<string>();
            var ownRoots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var path in searchPaths)
            {
                var root = NormalizePath(path);
                if (root != null && !sharedRoots.Contains(root))
                    ownRoots.Add(root);
            }

            if (ownRoots.Count == 0)
                return names;

            var moduleFiles = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var entry in modules)
            {
                if (entry.Key is string name && name != MainModuleName)
                    moduleFiles[name] = NormalizePath(GetModuleFile(entry.Value));
            }

            var loadedFromOwnRoots = new HashSet<string>(StringComparer.Ordinal);
            foreach (var module in moduleFiles)
            {
                if (module.Value != null && IsUnderAny(module.Value, ownRoots) && !IsUnderAny(module.Value, sharedRoots))
                    loadedFromOwnRoots.Add(module.Key);
            }

            foreach (var module in moduleFiles)
            {
                var loadedFromSharedRoot = module.Value != null && IsUnderAny(module.Value, sharedRoots);
                if (loadedFromOwnRoots.Contains(module.Key)
                    || (!loadedFromSharedRoot && loadedFromOwnRoots.Contains(TopLevelName(module.Key))))
                    names.Add(module.Key);
            }
            return names;
        }

        private static IDictionary<object, object> GetSysModules(ScriptEngine engine)
        {
            object modules = IronPython.Hosting.Python.GetSysModule(engine).GetVariable("modules");
            return (IDictionary<object, object>)modules;
        }

        private static string GetModuleFile(object module)
        {
            if (module is IronPython.Runtime.PythonModule pythonModule
                && pythonModule.Get__dict__().TryGetValue("__file__", out var file))
                return file as string;
            return null;
        }

        private static string TopLevelName(string moduleName)
        {
            var dot = moduleName.IndexOf('.');
            return dot < 0 ? moduleName : moduleName.Substring(0, dot);
        }

        private void AddSharedModuleRoot(string path)
        {
            var root = NormalizePath(path);
            if (root != null)
                _sharedModuleRoots.Add(root);
        }

        private static string NormalizePath(string path)
        {
            if (string.IsNullOrEmpty(path))
                return null;

            try
            {
                if (!Path.IsPathRooted(path))
                    return null;
                return Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            }
            catch (Exception ex) when (ex is ArgumentException || ex is NotSupportedException || ex is PathTooLongException || ex is System.Security.SecurityException)
            {
                return null;
            }
        }

        private static bool IsUnderAny(string filePath, IEnumerable<string> directories)
        {
            foreach (var directory in directories)
            {
                if (filePath.StartsWith(directory + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                    return true;
            }
            return false;
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
            _sharedModuleRoots = null;
            _activeState = null;

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
                AddSharedModuleRoot(_pyrevitLibPath);
                var pyrevitRoot = Path.GetDirectoryName(_pyrevitLibPath);
                var sitePackages = string.IsNullOrEmpty(pyrevitRoot) ? null : Path.Combine(pyrevitRoot, "site-packages");
                if (sitePackages != null && Directory.Exists(sitePackages))
                {
                    AddPath(sitePackages);
                    AddSharedModuleRoot(sitePackages);
                }
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
