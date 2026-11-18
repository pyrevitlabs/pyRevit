using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;

using NUnit.Framework;

using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Bundles that share one IronPython engine keep their own modules: a bundle that ships a
    /// <c>lib</c> module with the same name as another bundle's imports its own copy, modules under a
    /// shared root stay one module for all bundles, and a nested bundle hands the outer bundle's
    /// modules back. Reproduces the shared-engine finding from the review of pyrevitlabs/pyRevit#4133,
    /// which smart buttons, ComboBoxes and checkboxes all had, and the finding from the review of
    /// pyrevitlabs/pyRevit#4136 that a module imported from a folder the bundle removed from
    /// <c>sys.path</c> again reached the next bundle.
    /// </summary>
    /// <remarks>
    /// Drives <c>PyRevitLoader.BundleModuleIsolation</c> from the IronPython 3 <c>pyRevitLoader.dll</c>
    /// that the Runtime reference copies next to the tests. It goes through reflection because this
    /// project compiles against neither the loader nor IronPython.
    /// </remarks>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class BundleModuleIsolationTests
    {
        private const string LibModuleName = "shared_name";
        private const string TemporaryModuleName = "tmp_mod";

        private string _root = string.Empty;
        private object _engine = null!;
        private object _isolation = null!;
        private List<string> _baseSearchPaths = new List<string>();

        [SetUp]
        public void SetUp()
        {
            _root = Path.Combine(Path.GetTempPath(), "pyRevitBundleIsolation_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_root);
            _engine = CreateEngine();
            _baseSearchPaths = GetSearchPaths();
            Type isolationType = LoaderAssembly().GetType("PyRevitLoader.BundleModuleIsolation", throwOnError: true)!;
            _isolation = Activator.CreateInstance(
                isolationType,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
                binder: null,
                args: new object?[] { _engine, null },
                culture: null)!;
        }

        [TearDown]
        public void TearDown()
        {
            Call(_isolation, "Release");
            object runtime = _engine.GetType().GetProperty("Runtime")!.GetValue(_engine)!;
            Call(runtime, "Shutdown");
            if (Directory.Exists(_root))
                Directory.Delete(_root, recursive: true);
        }

        [Test]
        public void Enter_TwoBundlesShipALibModuleWithTheSameName_EachImportsItsOwn()
        {
            object first = CreateBundleWithLibModule("First", "VALUE = 'first'");
            object second = CreateBundleWithLibModule("Second", "VALUE = 'second'");

            Assert.That(ImportLibValue(first), Is.EqualTo("first"));
            Assert.That(ImportLibValue(second), Is.EqualTo("second"));
            Assert.That(ImportLibValue(first), Is.EqualTo("first"));
        }

        [Test]
        public void Enter_BundleAgain_GetsTheModuleItLoadedBefore()
        {
            object keeper = CreateBundleWithLibModule("Keeper", "VALUE = 'keeper'");
            object other = CreateBundleWithLibModule("Other", "VALUE = 'other'");
            using (Enter(keeper))
                Execute($"import {LibModuleName}\n{LibModuleName}.calls = 1");
            ImportLibValue(other);

            using (Enter(keeper))
                Assert.That(Execute($"import {LibModuleName}\nresult = {LibModuleName}.calls"), Is.EqualTo(1));
        }

        [Test]
        public void Enter_ModuleUnderASharedRoot_StaysOneModuleForAllBundles()
        {
            string sharedRoot = CreateDirectory("pyrevitlib");
            File.WriteAllText(Path.Combine(sharedRoot, "common_mod.py"), "MARKS = []");
            Call(_isolation, "AddSharedRoot", sharedRoot);
            object first = CreateBundle("First", sharedRoot);
            object second = CreateBundle("Second", sharedRoot);

            using (Enter(first))
                Execute("import common_mod\ncommon_mod.MARKS.append('first')");

            using (Enter(second))
                Assert.That(Execute("import common_mod\nresult = ','.join(common_mod.MARKS)"), Is.EqualTo("first"));
        }

        [Test]
        public void Enter_SubmoduleOfAnOwnedPackageUnderASharedRoot_StaysShared()
        {
            string sharedRoot = CreateDirectory("site-packages");
            string sharedPart = CreateDirectory(Path.Combine("site-packages", "pkg_ext"));
            File.WriteAllText(Path.Combine(sharedPart, "sub.py"), "VALUE = 'shared'");
            Call(_isolation, "AddSharedRoot", sharedRoot);
            string package = CreateDirectory(Path.Combine("Owner", "lib", "pkg"));
            File.WriteAllText(Path.Combine(package, "__init__.py"), $"__path__.append({PythonString(sharedPart)})");
            object owner = CreateBundle("Owner", sharedRoot);

            using (Enter(owner))
                Execute("import pkg.sub");

            Assert.That(Execute("import sys\nresult = 'pkg' in sys.modules"), Is.False);
            Assert.That(Execute("import sys\nresult = 'pkg.sub' in sys.modules"), Is.True);
        }

        [Test]
        public void Enter_ModuleImportedFromAFolderTheBundleRemovedAgain_StaysWithThatBundle()
        {
            object first = CreateBundle("First");
            object second = CreateBundle("Second");
            string firstFolder = CreateModuleFolder("first_tmp", "VALUE = 'first'");
            string secondFolder = CreateModuleFolder("second_tmp", "VALUE = 'second'");

            Assert.That(ImportFromFolderRemovedAfterwards(first, firstFolder), Is.EqualTo("first"));
            Assert.That(ImportFromFolderRemovedAfterwards(second, secondFolder), Is.EqualTo("second"));
            using (Enter(first))
                Assert.That(Execute($"import {TemporaryModuleName}\nresult = {TemporaryModuleName}.VALUE"), Is.EqualTo("first"));
        }

        [Test]
        public void Enter_BundleThatRemovedOneOfItsSearchPaths_KeepsTheModulesItLoadedFromThere()
        {
            string library = CreateDirectory("RemoverLibrary");
            File.WriteAllText(Path.Combine(library, LibModuleName + ".py"), "VALUE = 'remover'");
            object remover = CreateBundle("Remover", library);
            object other = CreateBundleWithLibModule("Other", "VALUE = 'other'");
            ImportLibValue(remover);

            using (Enter(remover))
                Execute($"import sys\nsys.path.remove({PythonString(library)})");

            Assert.That(ImportLibValue(other), Is.EqualTo("other"));
            using (Enter(remover))
                Assert.That(Execute($"import {LibModuleName}\nresult = {LibModuleName}.VALUE"), Is.EqualTo("remover"));
        }

        [Test]
        public void Enter_ModuleFromTheEmbeddedStandardLibrary_StaysOneModuleForAllBundles()
        {
            RegisterEmbeddedStandardLibrary();
            object first = CreateBundle("First");
            object second = CreateBundle("Second");

            using (Enter(first))
                Execute("import colorsys\ncolorsys.loaded_by = 'first'");

            using (Enter(second))
                Assert.That(Execute("import colorsys\nresult = getattr(colorsys, 'loaded_by', None)"), Is.EqualTo("first"));
        }

        [Test]
        public void Enter_NestedBundle_GivesTheOuterBundleItsModulesBack()
        {
            object outer = CreateBundleWithLibModule("Outer", "VALUE = 'outer'");
            object inner = CreateBundleWithLibModule("Inner", "VALUE = 'inner'");

            using (Enter(outer))
            {
                Execute($"import {LibModuleName}");
                Assert.That(ImportLibValue(inner), Is.EqualTo("inner"));
                Assert.That(Execute($"import {LibModuleName}\nresult = {LibModuleName}.VALUE"), Is.EqualTo("outer"));
            }
        }

        [Test]
        public void Enter_AfterABundleChangedSysPath_KeepsTheChangeForThatBundleOnly()
        {
            string extraPath = CreateDirectory("extra");
            object changer = CreateBundleWithLibModule("Changer", "VALUE = 'changer'");
            object other = CreateBundleWithLibModule("Other", "VALUE = 'other'");

            using (Enter(changer))
                Execute($"import sys\nsys.path.append({PythonString(extraPath)})");

            using (Enter(other))
                Assert.That(GetSearchPaths(), Does.Not.Contain(extraPath));
            using (Enter(changer))
                Assert.That(GetSearchPaths(), Does.Contain(extraPath));
        }

        [Test]
        public void Dispose_OutermostBundle_PutsBackTheEnginePathsFromBeforeEntering()
        {
            object bundle = CreateBundleWithLibModule("Bundle", "VALUE = 'bundle'");
            var pathsBefore = new List<string>(_baseSearchPaths) { CreateDirectory("before") };
            SetSearchPaths(pathsBefore);

            using (Enter(bundle))
                Assert.That(GetSearchPaths(), Is.Not.EqualTo(pathsBefore));

            Assert.That(GetSearchPaths(), Is.EqualTo(pathsBefore));
        }

        [Test]
        public void Enter_BundleThatIsAlreadyActive_ReturnsNothingToDispose()
        {
            object bundle = CreateBundleWithLibModule("Active", "VALUE = 'active'");

            using (Enter(bundle))
                Assert.That(Enter(bundle), Is.Null);
        }

        [Test]
        public void Enter_AfterRelease_ReturnsNothingToDispose()
        {
            object bundle = CreateBundleWithLibModule("Released", "VALUE = 'released'");

            Call(_isolation, "Release");

            Assert.That(Enter(bundle), Is.Null);
        }

        private object CreateBundleWithLibModule(string name, string moduleSource)
        {
            string lib = CreateDirectory(Path.Combine(name, "lib"));
            File.WriteAllText(Path.Combine(lib, LibModuleName + ".py"), moduleSource);
            return CreateBundle(name);
        }

        private object CreateBundle(string name, params string[] extraPaths)
        {
            string bundleDirectory = CreateDirectory(name);
            var paths = new List<string>(_baseSearchPaths) { bundleDirectory, Path.Combine(bundleDirectory, "lib") };
            paths.AddRange(extraPaths);
            SetSearchPaths(paths);
            return Call(_isolation, "CreateBundle", name)!;
        }

        private object? ImportLibValue(object bundle)
        {
            using (Enter(bundle))
                return Execute($"import {LibModuleName}\nresult = {LibModuleName}.VALUE");
        }

        private string CreateModuleFolder(string name, string moduleSource)
        {
            string folder = CreateDirectory(name);
            File.WriteAllText(Path.Combine(folder, TemporaryModuleName + ".py"), moduleSource);
            return folder;
        }

        private object? ImportFromFolderRemovedAfterwards(object bundle, string folder)
        {
            using (Enter(bundle))
                return Execute(
                    $"import sys\nsys.path.append({PythonString(folder)})\nimport {TemporaryModuleName}\n"
                    + $"sys.path.remove({PythonString(folder)})\nresult = {TemporaryModuleName}.VALUE");
        }

        /// <summary>
        /// Adds the standard library embedded in the loader to the engine, first in
        /// <c>sys.meta_path</c>, the way <c>ScriptExecutor.AddEmbeddedLib</c> adds it for pyRevit's
        /// engines. Its modules get a relative <c>__file__</c>, such as <c>colorsys.py</c>.
        /// </summary>
        private void RegisterEmbeddedStandardLibrary()
        {
            Assembly loader = LoaderAssembly();
            string resource = loader.GetManifestResourceNames()
                .Single(name => name.EndsWith("_lib.zip", StringComparison.OrdinalIgnoreCase));
            Type importerType = LoadReferencedAssembly(loader, "IronPython.Modules")
                .GetType("IronPython.Modules.ResourceMetaPathImporter", throwOnError: true)!;
            object importer = Activator.CreateInstance(importerType, loader, resource)!;

            Type python = IronPythonAssembly().GetType("IronPython.Hosting.Python", throwOnError: true)!;
            object sys = python.GetMethods(BindingFlags.Static | BindingFlags.Public)
                .Single(method => method.Name == "GetSysModule"
                    && method.GetParameters().Length == 1
                    && method.GetParameters()[0].ParameterType.IsInstanceOfType(_engine))
                .Invoke(null, new[] { _engine })!;
            object metaPath = Call(sys, "GetVariable", "meta_path")!;
            metaPath.GetType()
                .GetMethods(BindingFlags.Instance | BindingFlags.Public)
                .First(method => method.Name == "insert" && method.GetParameters().Length == 2)
                .Invoke(metaPath, new object[] { 0, importer });
        }

        private IDisposable? Enter(object bundle)
        {
            return (IDisposable?)Call(_isolation, "Enter", bundle);
        }

        private string CreateDirectory(string relativePath)
        {
            string path = Path.Combine(_root, relativePath);
            Directory.CreateDirectory(path);
            return path;
        }

        private static string PythonString(string value)
        {
            return "'" + value.Replace("\\", "\\\\").Replace("'", "\\'") + "'";
        }

        private object? Execute(string code)
        {
            object scope = Call(_engine, "CreateScope")!;
            MethodInfo execute = _engine.GetType()
                .GetMethods(BindingFlags.Instance | BindingFlags.Public)
                .Single(method => method.Name == "Execute"
                    && !method.IsGenericMethodDefinition
                    && method.GetParameters().Length == 2
                    && method.GetParameters()[0].ParameterType == typeof(string));
            execute.Invoke(_engine, new[] { code, scope });

            MethodInfo tryGetVariable = scope.GetType()
                .GetMethods(BindingFlags.Instance | BindingFlags.Public)
                .Single(method => method.Name == "TryGetVariable"
                    && !method.IsGenericMethodDefinition
                    && method.GetParameters().Length == 2);
            var arguments = new object?[] { "result", null };
            return (bool)tryGetVariable.Invoke(scope, arguments)! ? arguments[1] : null;
        }

        private List<string> GetSearchPaths()
        {
            return new List<string>((ICollection<string>)Call(_engine, "GetSearchPaths")!);
        }

        private void SetSearchPaths(List<string> paths)
        {
            Call(_engine, "SetSearchPaths", paths);
        }

        private static object? Call(object target, string methodName, params object[] arguments)
        {
            MethodInfo method = target.GetType()
                .GetMethods(BindingFlags.Instance | BindingFlags.Public)
                .Single(candidate => candidate.Name == methodName
                    && !candidate.IsGenericMethodDefinition
                    && candidate.GetParameters().Length == arguments.Length);
            return method.Invoke(target, arguments);
        }

        private static object CreateEngine()
        {
            Type python = IronPythonAssembly().GetType("IronPython.Hosting.Python", throwOnError: true)!;
            return python.GetMethod("CreateEngine", Type.EmptyTypes)!.Invoke(null, null)!;
        }

        private static Assembly LoaderAssembly()
        {
            return LoadReferencedAssembly(typeof(IronPythonRuleCaches).Assembly, "pyRevitLoader");
        }

        private static Assembly IronPythonAssembly()
        {
            return LoadReferencedAssembly(LoaderAssembly(), "IronPython");
        }

        private static Assembly LoadReferencedAssembly(Assembly referencingAssembly, string name)
        {
            AssemblyName reference = referencingAssembly
                .GetReferencedAssemblies()
                .First(candidate => string.Equals(candidate.Name, name, StringComparison.Ordinal)
                    || (candidate.Name ?? string.Empty).EndsWith("." + name, StringComparison.Ordinal));
            return Assembly.Load(reference);
        }
    }
}
