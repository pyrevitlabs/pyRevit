using System;
using System.Collections.Generic;
using System.IO;
using Microsoft.Scripting.Hosting;

namespace PyRevitLoader
{
    /// <summary>
    /// Keeps apart the bundles that run in one shared IronPython engine: each bundle's code runs with
    /// that bundle's own <c>sys.path</c> and its own copies of the modules it loaded.
    /// </summary>
    /// <remarks>
    /// <see cref="SmartButtonExecutor"/>, <see cref="ComboBoxExecutor"/> and <see cref="CheckBoxExecutor"/>
    /// each run all their bundles in one engine, so their bundles share <c>sys.path</c> and
    /// <c>sys.modules</c>. Without this, a bundle that imports a module another bundle already loaded
    /// under the same name gets that bundle's cached copy.
    /// A bundle owns the modules that appear in <c>sys.modules</c> while it is the active bundle and
    /// the modules loaded from its own search paths, except those loaded from a shared root: the
    /// engine's base paths and the roots added with <see cref="AddSharedRoot"/>, such as
    /// <c>pyrevitlib</c> and <c>site-packages</c>. A package's submodules go with the package, however
    /// deeply nested and even when loaded from a shared root. A bundle's modules stay out of
    /// <c>sys.modules</c> while it is not the active bundle, so two bundles can ship <c>lib</c> modules
    /// with the same name while pyRevit and the standard library are still imported once for all of
    /// them. A shared module steps aside while a bundle is active when one of the bundle's own search
    /// paths ahead of the module's shared root has a module or package of that name, so the bundle
    /// imports its own, as a fresh import would, and the shared module comes back when the bundle is
    /// left. A module stays with its bundle even after the bundle's code removes the folder it came
    /// from from <c>sys.path</c>. A shared module that a bundle's code replaces with one of its own,
    /// such as by deleting it from <c>sys.modules</c> and importing the bundle's module of that name,
    /// goes back into <c>sys.modules</c> when the bundle is left. A bundle that adds its own package to
    /// a shared package, by extending the shared package's <c>__path__</c>, keeps that folder and its
    /// submodule's binding on the shared package to itself: both are in place only while it is active,
    /// and the folder goes back to its place in the <c>__path__</c>.
    /// Invariant: a module loaded from a shared root moves only as a submodule of a package the bundle
    /// owns, a folder under a shared root never leaves a <c>__path__</c>, a <c>__path__</c> that cannot
    /// change size, such as a .NET array, is never changed, and <c>__main__</c> never moves.
    /// Note: only code that runs while its bundle is entered is kept apart. Callbacks a script subscribes
    /// itself, such as Revit event handlers, run with whatever the engine holds when they fire, without
    /// the folders the script added to <c>sys.path</c>, so an import inside them can fail, or load a
    /// module again from the current <c>sys.path</c> instead of reusing the copy its bundle loaded. Such
    /// a module, when it comes from outside the shared roots, is set aside while a bundle is active, so
    /// it does not reach that bundle, and it comes back when the bundle is left, even when the bundle
    /// loaded a shared module of that name. That shared module is kept for the next bundle that has no
    /// module of its own by that name.
    /// Warning: two cases are not kept apart. <c>sys.path</c> is a new list each time a bundle is
    /// entered or brought back after a nested bundle, so a reference kept to an earlier list, such as
    /// <c>from sys import path</c>, no longer changes the live path. And a submodule that a bundle adds
    /// to a shared package, by putting its own folder in that package's <c>__path__</c>, is found only
    /// while the shared package has no submodule of that name loaded: once a bundle loaded the shared
    /// one, every bundle gets it.
    /// Important: not thread-safe. Use it only on the thread that runs the engine's scripts.
    /// </remarks>
    internal sealed class BundleModuleIsolation
    {
        private const string MainModuleName = "__main__";

        private static readonly HashSet<string> NoModuleNames = new HashSet<string>(StringComparer.Ordinal);

        private readonly Action<string> _logger;
        private readonly HashSet<string> _sharedRoots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, string> _normalizedModuleFiles = new Dictionary<string, string>(StringComparer.Ordinal);
        private readonly Dictionary<string, ListedFolder> _listedFolders = new Dictionary<string, ListedFolder>(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, Dictionary<string, object>> _sharedModulesKeptAside = new Dictionary<string, Dictionary<string, object>>(StringComparer.Ordinal);
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
        /// One bundle's share of the engine: the <c>sys.path</c> its code runs with, the modules it
        /// owns and the folders it added to shared packages' <c>__path__</c>, which stay out of
        /// <c>sys.modules</c> and out of those packages while it is not the active bundle.
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

            internal Dictionary<string, object> ModulesWhenEntered { get; set; }

            internal Dictionary<string, List<PackagePathFolder>> PackagePathFolders { get; } = new Dictionary<string, List<PackagePathFolder>>(StringComparer.Ordinal);

            internal Dictionary<string, HashSet<string>> PackagePathFoldersPutBack { get; } = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);

            internal Dictionary<string, HashSet<string>> PackagePathsWhenEntered { get; set; }
        }

        /// <summary>
        /// A folder a bundle keeps in a shared package's <c>__path__</c>, with its position in that list,
        /// so the folder goes back in front of the same folders as before.
        /// </summary>
        internal sealed class PackagePathFolder
        {
            internal PackagePathFolder(string folder, int position)
            {
                Folder = folder;
                Position = position;
            }

            internal string Folder { get; }

            internal int Position { get; }
        }

        /// <summary>
        /// Where a bundle's search paths and its own top-level modules sit on its <c>sys.path</c>, to tell
        /// which shared modules a fresh import in that bundle would not reach.
        /// </summary>
        private sealed class OwnModules
        {
            internal OwnModules(Dictionary<string, int> searchPathIndexes, Dictionary<string, int> moduleIndexes)
            {
                SearchPathIndexes = searchPathIndexes;
                ModuleIndexes = moduleIndexes;
            }

            internal Dictionary<string, int> SearchPathIndexes { get; }

            internal Dictionary<string, int> ModuleIndexes { get; }
        }

        private sealed class ListedFolder
        {
            internal ListedFolder(DateTime stamp, HashSet<string> moduleNames)
            {
                Stamp = stamp;
                ModuleNames = moduleNames;
            }

            internal DateTime Stamp { get; }

            internal HashSet<string> ModuleNames { get; }
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
        /// runs in <c>finally</c> blocks inside ribbon event handlers. A bundle that fails to be set
        /// aside does not keep the next one out: the bundle being entered, or the one being brought
        /// back, still gets its own paths and modules.
        /// </remarks>
        public IDisposable Enter(Bundle bundle)
        {
            var engine = _engine;
            if (engine == null || ReferenceEquals(_activeBundle, bundle))
                return null;

            var activation = new Activation(this, bundle, _activeBundle, new List<string>(engine.GetSearchPaths()));
            _activeBundle = bundle;
            if (activation.PreviousBundle != null)
                SetAside(engine, activation.PreviousBundle);
            BringBack(engine, bundle);
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
            _sharedModulesKeptAside.Clear();
            _listedFolders.Clear();
        }

        private void Leave(Activation activation)
        {
            var engine = _engine;
            try
            {
                if (engine == null)
                    return;

                SetAside(engine, activation.Bundle);
                if (activation.PreviousBundle != null)
                    BringBack(engine, activation.PreviousBundle);
                else
                    PutBackSearchPaths(engine, activation.PreviousSearchPaths);
            }
            finally
            {
                _activeBundle = activation.PreviousBundle;
            }
        }

        private void SetAside(ScriptEngine engine, Bundle bundle)
        {
            try
            {
                Deactivate(engine, bundle);
            }
            catch (Exception ex)
            {
                Log($"Failed to set aside the modules of '{bundle.Name}': {ex.Message}");
            }
        }

        private void BringBack(ScriptEngine engine, Bundle bundle)
        {
            try
            {
                Activate(engine, bundle);
            }
            catch (Exception ex)
            {
                Log($"Failed to bring back the modules of '{bundle.Name}': {ex.Message}");
            }
        }

        private void PutBackSearchPaths(ScriptEngine engine, List<string> searchPaths)
        {
            try
            {
                engine.SetSearchPaths(searchPaths);
            }
            catch (Exception ex)
            {
                Log($"Failed to put back the engine's search paths: {ex.Message}");
            }
        }

        /// <summary>
        /// Points <c>sys.path</c> at the bundle's saved paths, sets aside the modules of other bundles
        /// that are still in <c>sys.modules</c> and the shared modules the bundle's own modules shadow,
        /// and puts the bundle's own modules in, keeping what they hide for <see cref="Deactivate"/>.
        /// Puts back the shared modules kept aside for names the bundle has no module of its own for.
        /// Binds its submodules of shared packages to those packages and puts the folders it added back
        /// to their places in their <c>__path__</c>. Then records what <c>sys.modules</c> and the shared
        /// packages' <c>__path__</c> hold, so <see cref="Deactivate"/> can tell what changed while the
        /// bundle was active.
        /// </summary>
        /// <remarks>
        /// Note: another bundle's module is in <c>sys.modules</c> here only when code outside any
        /// bundle, such as a callback a script subscribed, imported it. Without setting it aside, the
        /// entering bundle would get that cached module instead of loading its own.
        /// </remarks>
        private void Activate(ScriptEngine engine, Bundle bundle)
        {
            bundle.ModulesWhenEntered = null;
            bundle.PackagePathsWhenEntered = null;
            engine.SetSearchPaths(bundle.SearchPaths);
            var modules = GetSysModules(engine);
            var modulesBefore = new Dictionary<string, object>(StringComparer.Ordinal);
            var ownModules = FindOwnModules(bundle);
            bundle.HiddenModules.Clear();
            foreach (var name in FindModulesOfOtherBundles(modules, bundle))
                Hide(modules, bundle, name, modulesBefore);
            foreach (var name in FindSharedModulesShadowedByOwnModules(modules, bundle, ownModules))
                Hide(modules, bundle, name, modulesBefore);

            foreach (var module in bundle.Modules)
            {
                if (modules.TryGetValue(module.Key, out var hiddenModule))
                    bundle.HiddenModules[module.Key] = hiddenModule;
                modulesBefore[module.Key] = hiddenModule;
                modules[module.Key] = module.Value;
            }

            PutBackSharedModulesKeptAside(modules, ownModules, modulesBefore);
            BindToSharedPackages(modules, modulesBefore);
            AddPackagePathFolders(modules, bundle);
            bundle.ModulesWhenEntered = CopyModules(modules);
            bundle.PackagePathsWhenEntered = CopyPackagePaths(modules, bundle);
        }

        private static void Hide(IDictionary<object, object> modules, Bundle bundle, string name, Dictionary<string, object> modulesBefore)
        {
            modulesBefore[name] = modules[name];
            bundle.HiddenModules[name] = modules[name];
            modules.Remove(name);
        }

        /// <summary>
        /// Saves <c>sys.path</c> into the bundle, moves the modules it owns out of <c>sys.modules</c>
        /// and into the bundle, and puts back the modules they hid, the shared modules they replaced and
        /// the modules set aside when it was entered, keeping aside a shared module that took one of
        /// those names meanwhile. Unbinds its submodules from shared packages and takes the folders it
        /// added to their <c>__path__</c> with it.
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
            var ownNames = FindOwnModuleNames(modules, bundle);
            var replacedSharedModules = FindReplacedSharedModules(bundle, ownNames);
            var modulesBefore = new Dictionary<string, object>(StringComparer.Ordinal);
            bundle.Modules.Clear();
            foreach (var name in ownNames)
            {
                modulesBefore[name] = modules[name];
                bundle.Modules[name] = modules[name];
                modules.Remove(name);
            }

            foreach (var module in replacedSharedModules)
                modules[module.Key] = module.Value;

            TakeOutModulesThatTookHiddenNames(modules, bundle, modulesBefore);
            foreach (var module in bundle.HiddenModules)
            {
                if (modules.ContainsKey(module.Key))
                    continue;

                modules[module.Key] = module.Value;
                if (!modulesBefore.ContainsKey(module.Key))
                    modulesBefore[module.Key] = null;
            }

            BindToSharedPackages(modules, modulesBefore);
            MovePackagePathFolders(modules, bundle, modulesBefore);
            bundle.HiddenModules.Clear();
            bundle.ModulesWhenEntered = null;
            bundle.PackagePathsWhenEntered = null;
        }

        /// <summary>
        /// Lists the <c>sys.modules</c> entries the active bundle owns: the entries it owned when it
        /// was entered, the modules that appeared or were replaced since then, the modules whose file
        /// lies under one of its search paths that is not shared, and every entry inside a package it
        /// owns, however deeply nested, including the <c>None</c> entries IronPython 2 records for
        /// failed implicit relative imports.
        /// </summary>
        /// <remarks>
        /// Note: ownership does not depend on the bundle's final <c>sys.path</c>, so a module imported
        /// from a folder that the bundle's code removed from <c>sys.path</c> again still goes with the
        /// bundle. A module that appeared without a file path, such as a built-in or .NET namespace
        /// module or one from the embedded standard library, whose <c>__file__</c> is relative, stays
        /// shared unless it belongs to an owned package.
        /// Note: a submodule goes with its package even when its file lies under a shared root, as in a
        /// package that extends its <c>__path__</c> into <c>site-packages</c>. It cannot stay shared
        /// between two bundles' copies of the package: <c>import pkg.sub</c> in the second bundle would
        /// find the cached submodule and leave that bundle's <c>pkg</c> without it. The same holds for a
        /// package the bundle adds to a shared package, such as its own <c>pkg.plugins</c> inside a shared
        /// <c>pkg</c>: its submodules go with it, while <c>pkg</c> and its other submodules stay shared.
        /// Invariant: call it before <see cref="Bundle.Modules"/> is cleared, because those are the
        /// entries the bundle owned when it was entered.
        /// </remarks>
        private List<string> FindOwnModuleNames(IDictionary<object, object> modules, Bundle bundle)
        {
            var ownRoots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var path in bundle.SearchPaths)
            {
                var root = NormalizePath(path);
                if (root != null && !_sharedRoots.Contains(root))
                    ownRoots.Add(root);
            }

            var moduleNames = new List<string>();
            var owned = new HashSet<string>(StringComparer.Ordinal);
            foreach (var entry in modules)
            {
                if (!(entry.Key is string name) || name == MainModuleName)
                    continue;

                moduleNames.Add(name);
                var file = NormalizeModuleFile(GetModuleFile(entry.Value));
                if (file != null && IsUnderAny(file, _sharedRoots))
                    continue;

                if (bundle.Modules.ContainsKey(name)
                    || (file != null && (IsUnderAny(file, ownRoots) || AppearedWhileActive(bundle, name, entry.Value))))
                    owned.Add(name);
            }

            var names = new List<string>();
            foreach (var name in moduleNames)
            {
                if (owned.Contains(name) || IsInsideAnyPackage(name, owned))
                    names.Add(name);
            }
            return names;
        }

        /// <summary>
        /// Lists the <c>sys.modules</c> entries that belong to a bundle other than
        /// <paramref name="bundle"/>: the modules loaded from a file outside the shared roots that it
        /// does not own, and every entry inside such a package, however deeply nested.
        /// </summary>
        private List<string> FindModulesOfOtherBundles(IDictionary<object, object> modules, Bundle bundle)
        {
            var moduleNames = new List<string>();
            var bundleModules = new HashSet<string>(StringComparer.Ordinal);
            foreach (var entry in modules)
            {
                if (!(entry.Key is string name) || name == MainModuleName || bundle.Modules.ContainsKey(name))
                    continue;

                moduleNames.Add(name);
                if (!IsShared(entry.Value))
                    bundleModules.Add(name);
            }

            var names = new List<string>();
            foreach (var name in moduleNames)
            {
                if (bundleModules.Contains(name) || IsInsideAnyPackage(name, bundleModules))
                    names.Add(name);
            }
            return names;
        }

        /// <summary>
        /// Lists the shared modules that a fresh import in <paramref name="bundle"/> would not reach,
        /// with everything inside them: the top-level modules loaded from a shared root that comes after
        /// one of the bundle's own search paths with a module or package of the same name, and the
        /// shared submodules of the top-level packages the bundle owns.
        /// </summary>
        /// <remarks>
        /// Note: <c>import</c> looks in <c>sys.modules</c> before <c>sys.path</c>, so without setting them
        /// aside a bundle whose <c>lib</c> has a module with the name of a shared one would get the shared
        /// one once another bundle loaded it, and a bundle's own package would get another bundle's shared
        /// submodule. A module without a file, such as a built-in one or one from the embedded standard
        /// library, and one whose root comes before the bundle's own paths, such as the standard library's,
        /// stay, as they would for a fresh import. The bundle's own modules are left to <see cref="Activate"/>.
        /// </remarks>
        private List<string> FindSharedModulesShadowedByOwnModules(IDictionary<object, object> modules, Bundle bundle, OwnModules ownModules)
        {
            var names = new List<string>();
            if (ownModules.ModuleIndexes.Count == 0 && bundle.Modules.Count == 0)
                return names;

            var shadowed = new HashSet<string>(StringComparer.Ordinal);
            foreach (var entry in modules)
            {
                if (entry.Key is string name
                    && name.IndexOf('.') < 0
                    && name != MainModuleName
                    && (bundle.Modules.ContainsKey(name) || IsShadowedByOwnModule(ownModules, name, entry.Value)))
                    shadowed.Add(name);
            }

            if (shadowed.Count == 0)
                return names;

            foreach (var entry in modules)
            {
                if (entry.Key is string name
                    && !bundle.Modules.ContainsKey(name)
                    && (shadowed.Contains(name) || IsInsideAnyPackage(name, shadowed)))
                    names.Add(name);
            }
            return names;
        }

        private bool IsShadowedByOwnModule(OwnModules ownModules, string name, object module)
        {
            if (!ownModules.ModuleIndexes.TryGetValue(name, out var ownIndex))
                return false;

            var file = NormalizeModuleFile(GetModuleFile(module));
            return file != null && IsUnderAny(file, _sharedRoots) && ownIndex < GetSearchPathIndex(ownModules, file, name);
        }

        private static int GetSearchPathIndex(OwnModules ownModules, string moduleFile, string name)
        {
            var folder = Path.GetDirectoryName(moduleFile);
            if (folder != null
                && string.Equals(Path.GetFileNameWithoutExtension(moduleFile), "__init__", StringComparison.OrdinalIgnoreCase)
                && string.Equals(Path.GetFileName(folder), name, StringComparison.OrdinalIgnoreCase))
                folder = Path.GetDirectoryName(folder);
            return folder != null && ownModules.SearchPathIndexes.TryGetValue(folder, out var index) ? index : int.MaxValue;
        }

        /// <summary>
        /// Maps the bundle's search paths to their positions, and the top-level modules and packages in
        /// its own search paths, the ones outside the shared roots, to the position of the first path
        /// that has them.
        /// </summary>
        private OwnModules FindOwnModules(Bundle bundle)
        {
            var searchPathIndexes = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            var moduleIndexes = new Dictionary<string, int>(StringComparer.Ordinal);
            for (var i = 0; i < bundle.SearchPaths.Count; i++)
            {
                var path = NormalizeModuleFile(bundle.SearchPaths[i]);
                if (path == null || searchPathIndexes.ContainsKey(path))
                    continue;

                searchPathIndexes[path] = i;
                if (!IsOutsideSharedRoots(path))
                    continue;

                foreach (var name in ListModuleNames(path))
                {
                    if (!moduleIndexes.ContainsKey(name))
                        moduleIndexes[name] = i;
                }
            }
            return new OwnModules(searchPathIndexes, moduleIndexes);
        }

        /// <summary>
        /// Lists the modules and regular packages directly in <paramref name="folder"/>: its <c>.py</c>
        /// files and its folders that have an <c>__init__.py</c>.
        /// </summary>
        /// <remarks>
        /// Note: the list is kept until the folder's last write time changes, so entering a bundle does
        /// not read its folders again on every call.
        /// </remarks>
        private HashSet<string> ListModuleNames(string folder)
        {
            DateTime stamp;
            try
            {
                if (!Directory.Exists(folder))
                    return NoModuleNames;
                stamp = Directory.GetLastWriteTimeUtc(folder);
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException || ex is ArgumentException || ex is NotSupportedException)
            {
                return NoModuleNames;
            }

            if (_listedFolders.TryGetValue(folder, out var listed) && listed.Stamp == stamp)
                return listed.ModuleNames;

            var names = new HashSet<string>(StringComparer.Ordinal);
            try
            {
                foreach (var file in Directory.EnumerateFiles(folder))
                {
                    if (string.Equals(Path.GetExtension(file), ".py", StringComparison.OrdinalIgnoreCase))
                        names.Add(Path.GetFileNameWithoutExtension(file));
                }

                foreach (var directory in Directory.EnumerateDirectories(folder))
                {
                    if (File.Exists(Path.Combine(directory, "__init__.py")))
                        names.Add(Path.GetFileName(directory));
                }
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException)
            {
                Log($"Failed to list the modules in '{folder}': {ex.Message}");
            }

            _listedFolders[folder] = new ListedFolder(stamp, names);
            return names;
        }

        /// <summary>
        /// Takes out of <c>sys.modules</c> the modules that took the names of the modules set aside when
        /// the bundle was entered, with everything inside them, so the set-aside ones can go back. A
        /// shared module that took the name of another bundle's module or of a module that code outside
        /// any bundle loaded is kept aside for later bundles. One that took the name of a shared module
        /// is dropped, because that shared module goes back.
        /// </summary>
        /// <remarks>
        /// Note: such a shared module is one the bundle loaded because it has no module of that name of
        /// its own, such as one from <c>site-packages</c>, while a callback outside any bundle had loaded
        /// a <c>lib</c> module of that name. Leaving it in <c>sys.modules</c> would hand that callback a
        /// different module, without the state it kept on its own.
        /// Invariant: call it after the bundle's own modules left <c>sys.modules</c>, so every module
        /// left there is shared.
        /// </remarks>
        private void TakeOutModulesThatTookHiddenNames(IDictionary<object, object> modules, Bundle bundle, Dictionary<string, object> modulesBefore)
        {
            var takenNames = new HashSet<string>(StringComparer.Ordinal);
            foreach (var hidden in bundle.HiddenModules)
            {
                if (modules.TryGetValue(hidden.Key, out var module) && !ReferenceEquals(module, hidden.Value))
                    takenNames.Add(hidden.Key);
            }

            if (takenNames.Count == 0)
                return;

            var names = new List<string>();
            foreach (var entry in modules)
            {
                if (entry.Key is string name && (takenNames.Contains(name) || IsInsideAnyPackage(name, takenNames)))
                    names.Add(name);
            }

            var keptAside = new Dictionary<string, Dictionary<string, object>>(StringComparer.Ordinal);
            foreach (var name in names)
            {
                var module = modules[name];
                var takenName = FindOutermostName(name, takenNames);
                if (!IsShared(bundle.HiddenModules[takenName]))
                {
                    if (!keptAside.TryGetValue(takenName, out var group))
                    {
                        group = new Dictionary<string, object>(StringComparer.Ordinal);
                        keptAside[takenName] = group;
                    }
                    group[name] = module;
                }

                modulesBefore[name] = module;
                modules.Remove(name);
            }

            foreach (var group in keptAside)
                _sharedModulesKeptAside[group.Key] = group.Value;
        }

        /// <summary>
        /// Puts back the shared modules that <see cref="TakeOutModulesThatTookHiddenNames"/> kept aside,
        /// each group under a name that is free while the bundle is active and that the bundle's own
        /// modules do not shadow, so every bundle that loads one of them keeps using the same copy.
        /// </summary>
        private void PutBackSharedModulesKeptAside(IDictionary<object, object> modules, OwnModules ownModules, Dictionary<string, object> modulesBefore)
        {
            var namesPutBack = new List<string>();
            foreach (var group in _sharedModulesKeptAside)
            {
                if (!IsFree(modules, group.Value.Keys) || !IsParentLoaded(modules, group.Key))
                    continue;

                if (group.Key.IndexOf('.') < 0
                    && group.Value.TryGetValue(group.Key, out var groupModule)
                    && IsShadowedByOwnModule(ownModules, group.Key, groupModule))
                    continue;

                foreach (var module in group.Value)
                {
                    modules[module.Key] = module.Value;
                    if (!modulesBefore.ContainsKey(module.Key))
                        modulesBefore[module.Key] = null;
                }
                namesPutBack.Add(group.Key);
            }

            foreach (var name in namesPutBack)
                _sharedModulesKeptAside.Remove(name);
        }

        private static bool IsFree(IDictionary<object, object> modules, IEnumerable<string> names)
        {
            foreach (var name in names)
            {
                if (modules.ContainsKey(name))
                    return false;
            }
            return true;
        }

        private static bool IsParentLoaded(IDictionary<object, object> modules, string name)
        {
            var dot = name.LastIndexOf('.');
            return dot < 0 || modules.ContainsKey(name.Substring(0, dot));
        }

        private static string FindOutermostName(string moduleName, HashSet<string> names)
        {
            for (var dot = moduleName.IndexOf('.'); dot >= 0; dot = moduleName.IndexOf('.', dot + 1))
            {
                var prefix = moduleName.Substring(0, dot);
                if (names.Contains(prefix))
                    return prefix;
            }
            return moduleName;
        }

        /// <summary>
        /// Makes each package that stays in <c>sys.modules</c> bind the submodules whose entries just
        /// changed to what <c>sys.modules</c> now holds for them, as the import system binds a submodule
        /// it loads.
        /// </summary>
        /// <param name="modulesBefore">The names whose entries changed, each with the module the entry
        /// held before, or null when there was none.</param>
        /// <remarks>
        /// Note: <c>from pkg import sub</c> reads the package's <c>sub</c> attribute before it looks in
        /// <c>sys.modules</c>. A bundle's submodule left bound to a shared package would reach the next
        /// bundle, and one put back without its binding would be missing from the package.
        /// Invariant: an attribute is set only when it is unset or holds a module, and removed only when
        /// it still holds the module that left, so a value the package set itself stays.
        /// </remarks>
        private static void BindToSharedPackages(IDictionary<object, object> modules, Dictionary<string, object> modulesBefore)
        {
            foreach (var change in modulesBefore)
            {
                var dot = change.Key.LastIndexOf('.');
                if (dot < 0 || modulesBefore.ContainsKey(change.Key.Substring(0, dot)))
                    continue;

                if (!modules.TryGetValue(change.Key.Substring(0, dot), out var parent)
                    || !(parent is IronPython.Runtime.PythonModule package))
                    continue;

                var childName = change.Key.Substring(dot + 1);
                var attributes = package.Get__dict__();
                var isBound = attributes.TryGetValue(childName, out var bound);
                if (modules.TryGetValue(change.Key, out var module) && module != null)
                {
                    if (!isBound || bound is IronPython.Runtime.PythonModule)
                        attributes[childName] = module;
                }
                else if (isBound && ReferenceEquals(bound, change.Value))
                {
                    attributes.Remove(childName);
                }
            }
        }

        /// <summary>
        /// Puts the folders the bundle keeps in shared packages' <c>__path__</c> that are missing there
        /// back to their positions, and records which ones it put back.
        /// </summary>
        /// <remarks>
        /// Note: a folder that is already in the list, such as one a callback outside any bundle added
        /// again, is not recorded, so <see cref="MovePackagePathFolders"/> leaves it there for that code.
        /// Invariant: <see cref="Bundle.PackagePathFolders"/> lists each package's folders by position,
        /// lowest first, so each one goes back in front of the same folders as before.
        /// </remarks>
        private static void AddPackagePathFolders(IDictionary<object, object> modules, Bundle bundle)
        {
            bundle.PackagePathFoldersPutBack.Clear();
            foreach (var package in bundle.PackagePathFolders)
            {
                if (!modules.TryGetValue(package.Key, out var module) || !(GetResizablePackagePath(module) is System.Collections.IList packagePath))
                    continue;

                var foldersPutBack = new HashSet<string>(StringComparer.Ordinal);
                foreach (var folder in package.Value)
                {
                    if (packagePath.Contains(folder.Folder))
                        continue;

                    packagePath.Insert(Math.Min(folder.Position, packagePath.Count), folder.Folder);
                    foldersPutBack.Add(folder.Folder);
                }
                bundle.PackagePathFoldersPutBack[package.Key] = foldersPutBack;
            }
        }

        private static Dictionary<string, HashSet<string>> CopyPackagePaths(IDictionary<object, object> modules, Bundle bundle)
        {
            var copy = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);
            foreach (var entry in modules)
            {
                if (!(entry.Key is string name) || bundle.Modules.ContainsKey(name) || !(GetPackagePath(entry.Value) is System.Collections.IList packagePath))
                    continue;

                var folders = new HashSet<string>(StringComparer.Ordinal);
                foreach (var folder in packagePath)
                {
                    if (folder is string path)
                        folders.Add(path);
                }
                copy[name] = folders;
            }
            return copy;
        }

        /// <summary>
        /// Takes the folders the active bundle added to the <c>__path__</c> of packages that stay in
        /// <c>sys.modules</c> out of those lists and into the bundle, with their positions: the folders
        /// outside the shared roots that were not there when it was entered, and the ones
        /// <see cref="Activate"/> put back. A folder the bundle keeps that was already there when it
        /// was entered stays in place and stays with the bundle.
        /// </summary>
        /// <param name="modulesBefore">The names whose <c>sys.modules</c> entries <see cref="Deactivate"/>
        /// just changed. Their packages are skipped, because they were not in <c>sys.modules</c> while
        /// the bundle was active.</param>
        /// <remarks>
        /// Note: a bundle that extends a shared package's <c>__path__</c> with its own folder would
        /// otherwise leave that folder in the package, and another bundle that imports a submodule of
        /// the same name would load the first bundle's file. A folder that code outside the bundle added
        /// again is left for that code, and the bundle still gets it back on a later call if it is gone
        /// by then.
        /// Invariant: a folder under a shared root never moves, and a <c>__path__</c> that cannot change
        /// size is left as it is. A package that appeared while the bundle was active is looked at only
        /// when it was loaded from a shared root, so a package without a file keeps its <c>__path__</c>.
        /// Without a record of what the bundle was entered with, as after a failed
        /// <see cref="Activate"/>, the bundle keeps the folders it had.
        /// </remarks>
        private void MovePackagePathFolders(IDictionary<object, object> modules, Bundle bundle, Dictionary<string, object> modulesBefore)
        {
            var pathsWhenEntered = bundle.PackagePathsWhenEntered;
            if (pathsWhenEntered == null)
                return;

            var keptFolders = new Dictionary<string, List<PackagePathFolder>>(StringComparer.Ordinal);
            foreach (var entry in modules)
            {
                if (!(entry.Key is string name)
                    || modulesBefore.ContainsKey(name)
                    || !(GetResizablePackagePath(entry.Value) is System.Collections.IList packagePath))
                    continue;

                var wasThere = pathsWhenEntered.TryGetValue(name, out var foldersWhenEntered);
                if (!wasThere && !IsLoadedFromSharedRoot(entry.Value))
                    continue;

                bundle.PackagePathFoldersPutBack.TryGetValue(name, out var foldersPutBack);
                var foldersLeftInPlace = FindFoldersLeftInPlace(bundle, name, foldersPutBack);
                var folders = new List<PackagePathFolder>();
                for (var i = packagePath.Count - 1; i >= 0; i--)
                {
                    if (!(packagePath[i] is string folder) || !IsOutsideSharedRoots(folder))
                        continue;

                    if (!wasThere || !foldersWhenEntered.Contains(folder) || (foldersPutBack != null && foldersPutBack.Contains(folder)))
                    {
                        folders.Insert(0, new PackagePathFolder(folder, i));
                        packagePath.RemoveAt(i);
                    }
                    else if (foldersLeftInPlace.Contains(folder))
                    {
                        folders.Insert(0, new PackagePathFolder(folder, i));
                    }
                }

                if (folders.Count > 0)
                    keptFolders[name] = folders;
            }

            bundle.PackagePathFolders.Clear();
            foreach (var folders in keptFolders)
                bundle.PackagePathFolders[folders.Key] = folders.Value;
            bundle.PackagePathFoldersPutBack.Clear();
        }

        private static HashSet<string> FindFoldersLeftInPlace(Bundle bundle, string packageName, HashSet<string> foldersPutBack)
        {
            var folders = new HashSet<string>(StringComparer.Ordinal);
            if (bundle.PackagePathFolders.TryGetValue(packageName, out var keptFolders))
            {
                foreach (var folder in keptFolders)
                {
                    if (foldersPutBack == null || !foldersPutBack.Contains(folder.Folder))
                        folders.Add(folder.Folder);
                }
            }
            return folders;
        }

        /// <summary>
        /// Lists the shared modules that the names in <paramref name="ownNames"/> held when the active
        /// bundle was entered, for the names it did not own then, such as a shared module its code
        /// replaced with a <c>lib</c> module of the same name.
        /// </summary>
        /// <remarks>
        /// Invariant: never lists a module the bundle owned when it was entered, or one loaded from a
        /// file outside the shared roots, which belongs to a bundle: putting either back would hand it to
        /// the next bundle. Call it before <see cref="Bundle.Modules"/> is cleared.
        /// </remarks>
        private Dictionary<string, object> FindReplacedSharedModules(Bundle bundle, List<string> ownNames)
        {
            var sharedModules = new Dictionary<string, object>(StringComparer.Ordinal);
            var modulesWhenEntered = bundle.ModulesWhenEntered;
            if (modulesWhenEntered == null)
                return sharedModules;

            foreach (var name in ownNames)
            {
                if (!bundle.Modules.ContainsKey(name)
                    && modulesWhenEntered.TryGetValue(name, out var moduleWhenEntered)
                    && moduleWhenEntered != null
                    && IsShared(moduleWhenEntered))
                    sharedModules[name] = moduleWhenEntered;
            }
            return sharedModules;
        }

        private bool IsShared(object module)
        {
            var file = NormalizeModuleFile(GetModuleFile(module));
            return file == null || IsUnderAny(file, _sharedRoots);
        }

        private bool IsLoadedFromSharedRoot(object module)
        {
            var file = NormalizeModuleFile(GetModuleFile(module));
            return file != null && IsUnderAny(file, _sharedRoots);
        }

        private bool IsOutsideSharedRoots(string folder)
        {
            var path = NormalizeModuleFile(folder);
            return path != null && !_sharedRoots.Contains(path) && !IsUnderAny(path, _sharedRoots);
        }

        private static bool IsInsideAnyPackage(string moduleName, HashSet<string> packageNames)
        {
            for (var dot = moduleName.IndexOf('.'); dot >= 0; dot = moduleName.IndexOf('.', dot + 1))
            {
                if (packageNames.Contains(moduleName.Substring(0, dot)))
                    return true;
            }
            return false;
        }

        private static bool AppearedWhileActive(Bundle bundle, string name, object module)
        {
            var modulesWhenEntered = bundle.ModulesWhenEntered;
            return modulesWhenEntered != null
                && (!modulesWhenEntered.TryGetValue(name, out var moduleWhenEntered) || !ReferenceEquals(moduleWhenEntered, module));
        }

        private static Dictionary<string, object> CopyModules(IDictionary<object, object> modules)
        {
            var copy = new Dictionary<string, object>(StringComparer.Ordinal);
            foreach (var entry in modules)
            {
                if (entry.Key is string name)
                    copy[name] = entry.Value;
            }
            return copy;
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

        private static System.Collections.IList GetPackagePath(object module)
        {
            if (module is IronPython.Runtime.PythonModule pythonModule
                && pythonModule.Get__dict__().TryGetValue("__path__", out var packagePath))
                return packagePath as System.Collections.IList;
            return null;
        }

        private static System.Collections.IList GetResizablePackagePath(object module)
        {
            var packagePath = GetPackagePath(module);
            return packagePath == null || packagePath.IsFixedSize || packagePath.IsReadOnly ? null : packagePath;
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
