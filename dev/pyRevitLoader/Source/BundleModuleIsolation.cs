using System;
using System.Collections.Generic;
using System.IO;
using Microsoft.Scripting.Hosting;

namespace PyRevitLoader
{
    /// <summary>
    /// Keeps apart the bundles that run in one shared IronPython engine: each bundle's code runs with
    /// that bundle's own <c>sys.path</c> and its own copies of the modules it loaded from its own
    /// search paths.
    /// </summary>
    /// <remarks>
    /// <see cref="SmartButtonExecutor"/>, <see cref="ComboBoxExecutor"/> and <see cref="CheckBoxExecutor"/>
    /// each run all their bundles in one engine, so their bundles share <c>sys.path</c> and
    /// <c>sys.modules</c>. Without this, a bundle that imports a module another bundle already loaded
    /// under the same name gets that bundle's cached copy.
    /// A bundle owns the modules it loaded from its own search paths, which are all of them except the
    /// shared roots: the engine's base paths and the roots added with <see cref="AddSharedRoot"/>, such
    /// as <c>pyrevitlib</c> and <c>site-packages</c>. A bundle's modules stay out of <c>sys.modules</c>
    /// while it is not the active bundle, so two bundles can ship <c>lib</c> modules with the same name
    /// while pyRevit and the standard library are still imported once for all of them.
    /// Invariant: modules loaded from a shared root are never moved, and neither is <c>__main__</c>.
    /// Note: only code that runs while its bundle is entered is kept apart. Callbacks a script subscribes
    /// itself, such as Revit event handlers, run with whatever the engine holds when they fire, so an
    /// import inside them can load a module again from the current <c>sys.path</c> instead of reusing
    /// the copy its bundle loaded.
    /// Important: not thread-safe. Use it only on the thread that runs the engine's scripts.
    /// </remarks>
    internal sealed class BundleModuleIsolation
    {
        private const string MainModuleName = "__main__";

        private readonly Action<string> _logger;
        private readonly HashSet<string> _sharedRoots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, string> _normalizedModuleFiles = new Dictionary<string, string>(StringComparer.Ordinal);
        private ScriptEngine _engine;
        private Bundle _activeBundle;

        /// <summary>
        /// Starts keeping apart the bundles of <paramref name="engine"/>. Its current search paths
        /// become shared roots.
        /// </summary>
        /// <param name="logger">Receives the failures of entering and leaving bundles.</param>
        /// <remarks>
        /// Important: create it right after the engine, before any bundle changes the search paths.
        /// </remarks>
        public BundleModuleIsolation(ScriptEngine engine, Action<string> logger)
        {
            _engine = engine;
            _logger = logger;
            foreach (var path in engine.GetSearchPaths())
                AddSharedRoot(path);
        }

        /// <summary>
        /// One bundle's share of the engine: the <c>sys.path</c> its code runs with and the modules it
        /// owns, which stay out of <c>sys.modules</c> while it is not the active bundle.
        /// </summary>
        internal sealed class Bundle
        {
            internal Bundle(string name, List<string> searchPaths)
            {
                Name = name;
                SearchPaths = searchPaths;
            }

            public string Name { get; }

            internal List<string> SearchPaths { get; }

            internal Dictionary<string, object> Modules { get; } = new Dictionary<string, object>(StringComparer.Ordinal);

            internal Dictionary<string, object> HiddenModules { get; } = new Dictionary<string, object>(StringComparer.Ordinal);
        }

        /// <summary>
        /// What <see cref="Enter"/> replaced: the bundle that was active before, or the engine's
        /// <c>sys.path</c> when none was. Disposing it leaves the entered bundle.
        /// </summary>
        private sealed class Activation : IDisposable
        {
            private readonly BundleModuleIsolation _isolation;
            private bool _left;

            public Activation(BundleModuleIsolation isolation, Bundle bundle, Bundle previousBundle, List<string> previousSearchPaths)
            {
                _isolation = isolation;
                Bundle = bundle;
                PreviousBundle = previousBundle;
                PreviousSearchPaths = previousSearchPaths;
            }

            public Bundle Bundle { get; }

            public Bundle PreviousBundle { get; }

            public List<string> PreviousSearchPaths { get; }

            public void Dispose()
            {
                if (_left)
                    return;

                _left = true;
                _isolation.Leave(this);
            }
        }

        /// <summary>
        /// Treats every module loaded from under <paramref name="path"/> as shared by all bundles.
        /// </summary>
        public void AddSharedRoot(string path)
        {
            var root = NormalizePath(path);
            if (root != null)
                _sharedRoots.Add(root);
        }

        /// <summary>
        /// Creates a bundle that starts with the engine's current search paths and no modules.
        /// </summary>
        /// <remarks>
        /// Note: set the bundle's search paths on the engine before creating it. Leaving an outermost
        /// bundle puts back the paths the engine had when it was entered, so after a bundle's first run
        /// the engine still holds that bundle's paths, including <c>pyrevitlib</c>, for code that runs
        /// outside any bundle, such as callbacks a script subscribes.
        /// </remarks>
        public Bundle CreateBundle(string name)
        {
            var engine = _engine;
            return new Bundle(name, engine == null ? new List<string>() : new List<string>(engine.GetSearchPaths()));
        }

        /// <summary>
        /// Makes <paramref name="bundle"/> the active bundle until the returned object is disposed: sets
        /// the active bundle aside, then points <c>sys.path</c> at this bundle's saved paths and puts
        /// its own modules back into <c>sys.modules</c>.
        /// </summary>
        /// <returns>What brings back the replaced state when disposed; null, which a <c>using</c>
        /// statement accepts, when the bundle is already active or the isolation is released.</returns>
        /// <remarks>
        /// Note: a bundle's code can raise another bundle's handler before it returns, for example a
        /// checkbox handler that ticks another checkbox. Entering the second bundle sets the first one
        /// aside, and leaving it brings the first one back, so every call runs with its own bundle's
        /// paths and modules. A call raised while its own bundle is already active keeps the running
        /// environment as it is. Paths and modules a bundle's code adds stay with that bundle for its
        /// later calls.
        /// Warning: dispose the returned objects in the reverse order of entering, as nested
        /// <c>using</c> statements do. Disposing never throws; failures go to the logger, because it
        /// runs in <c>finally</c> blocks inside ribbon event handlers.
        /// </remarks>
        public IDisposable Enter(Bundle bundle)
        {
            var engine = _engine;
            if (engine == null || ReferenceEquals(_activeBundle, bundle))
                return null;

            var activation = new Activation(this, bundle, _activeBundle, new List<string>(engine.GetSearchPaths()));
            _activeBundle = bundle;
            try
            {
                if (activation.PreviousBundle != null)
                    Deactivate(engine, activation.PreviousBundle);
                Activate(engine, bundle);
            }
            catch (Exception ex)
            {
                Log($"Failed to bring back the modules of '{bundle.Name}': {ex.Message}");
            }
            return activation;
        }

        /// <summary>
        /// Stops moving modules and search paths, before the engine shuts down.
        /// </summary>
        /// <remarks>
        /// Note: a bundle can still be entered when its session is released, for example by a handler
        /// that reloads pyRevit. Leaving it afterwards then leaves the shut-down engine untouched.
        /// </remarks>
        public void Release()
        {
            _engine = null;
            _activeBundle = null;
        }

        private void Leave(Activation activation)
        {
            var engine = _engine;
            try
            {
                if (engine == null)
                    return;

                Deactivate(engine, activation.Bundle);
                if (activation.PreviousBundle != null)
                    Activate(engine, activation.PreviousBundle);
                else
                    engine.SetSearchPaths(activation.PreviousSearchPaths);
            }
            catch (Exception ex)
            {
                Log($"Failed to set aside the modules of '{activation.Bundle.Name}': {ex.Message}");
            }
            finally
            {
                _activeBundle = activation.PreviousBundle;
            }
        }

        /// <summary>
        /// Points <c>sys.path</c> at the bundle's saved paths and puts its own modules into
        /// <c>sys.modules</c>, keeping the modules they hide for <see cref="Deactivate"/>.
        /// </summary>
        private static void Activate(ScriptEngine engine, Bundle bundle)
        {
            engine.SetSearchPaths(bundle.SearchPaths);
            var modules = GetSysModules(engine);
            bundle.HiddenModules.Clear();
            foreach (var module in bundle.Modules)
            {
                if (modules.TryGetValue(module.Key, out var hiddenModule))
                    bundle.HiddenModules[module.Key] = hiddenModule;
                modules[module.Key] = module.Value;
            }
        }

        /// <summary>
        /// Saves <c>sys.path</c> into the bundle, moves the modules it owns out of <c>sys.modules</c>
        /// and into the bundle, and puts back the modules they hid.
        /// </summary>
        /// <remarks>
        /// Invariant: only call it for the active bundle. Its saved modules are rebuilt from
        /// <c>sys.modules</c>, which holds all of them only while it is active.
        /// </remarks>
        private void Deactivate(ScriptEngine engine, Bundle bundle)
        {
            var currentPaths = new List<string>(engine.GetSearchPaths());
            bundle.SearchPaths.Clear();
            bundle.SearchPaths.AddRange(currentPaths);

            var modules = GetSysModules(engine);
            bundle.Modules.Clear();
            foreach (var name in FindOwnModuleNames(modules, bundle.SearchPaths))
            {
                bundle.Modules[name] = modules[name];
                modules.Remove(name);
            }

            foreach (var module in bundle.HiddenModules)
            {
                if (!modules.ContainsKey(module.Key))
                    modules[module.Key] = module.Value;
            }
            bundle.HiddenModules.Clear();
        }

        /// <summary>
        /// Lists the <c>sys.modules</c> entries a bundle owns: modules whose file lies under one of its
        /// search paths that is not shared, and the other entries inside such a package, including the
        /// <c>None</c> entries IronPython 2 records for failed implicit relative imports.
        /// </summary>
        /// <remarks>
        /// Invariant: a module whose file lies under a shared root is never owned, even inside an
        /// owned package that extends its <c>__path__</c> into <c>site-packages</c>.
        /// </remarks>
        private List<string> FindOwnModuleNames(IDictionary<object, object> modules, IEnumerable<string> searchPaths)
        {
            var names = new List<string>();
            var ownRoots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var path in searchPaths)
            {
                var root = NormalizePath(path);
                if (root != null && !_sharedRoots.Contains(root))
                    ownRoots.Add(root);
            }

            if (ownRoots.Count == 0)
                return names;

            var moduleFiles = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var entry in modules)
            {
                if (entry.Key is string name && name != MainModuleName)
                    moduleFiles[name] = NormalizeModuleFile(GetModuleFile(entry.Value));
            }

            var loadedFromOwnRoots = new HashSet<string>(StringComparer.Ordinal);
            foreach (var module in moduleFiles)
            {
                if (module.Value != null && IsUnderAny(module.Value, ownRoots) && !IsUnderAny(module.Value, _sharedRoots))
                    loadedFromOwnRoots.Add(module.Key);
            }

            foreach (var module in moduleFiles)
            {
                var loadedFromSharedRoot = module.Value != null && IsUnderAny(module.Value, _sharedRoots);
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

        private string NormalizeModuleFile(string file)
        {
            if (file == null)
                return null;

            if (!_normalizedModuleFiles.TryGetValue(file, out var normalized))
            {
                normalized = NormalizePath(file);
                _normalizedModuleFiles[file] = normalized;
            }
            return normalized;
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

        private void Log(string message)
        {
            _logger?.Invoke(message);
        }
    }
}
