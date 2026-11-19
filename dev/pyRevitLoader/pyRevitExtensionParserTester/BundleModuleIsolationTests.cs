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
    /// which smart buttons, ComboBoxes and checkboxes all had, and these findings from the review of
    /// pyrevitlabs/pyRevit#4136:
    /// <list type="bullet">
    /// <item>a module imported from a folder the bundle removed from <c>sys.path</c> again reached the
    /// next bundle;</item>
    /// <item>a submodule kept shared between two bundles' copies of a package was missing from the
    /// second bundle's package, and the same held for a package a bundle adds to a shared package;</item>
    /// <item>a shared module a bundle replaced with its own was gone for the next bundle;</item>
    /// <item>a module or package that code outside any bundle imported from a bundle's folder reached
    /// the next bundle;</item>
    /// <item>a package a bundle adds to a shared package stayed bound to it, and in its <c>__path__</c>,
    /// for the next bundle;</item>
    /// <item>a bundle that owns a nested package got another bundle's shared submodule of it;</item>
    /// <item>leaving a bundle removed a module other code had assigned to a shared package's
    /// attribute;</item>
    /// <item>a bundle's folder went back to its old index even after a shared folder was added before
    /// its neighbour;</item>
    /// <item>a folder put back before a failed activation stayed in the shared package;</item>
    /// <item>a bundle's folder went back next to the first copy of a neighbour listed twice;</item>
    /// <item>leaving a bundle that had imported its package again removed the module other code had
    /// assigned to the shared package's attribute;</item>
    /// <item>a bundle's package stayed bound to a copy of the shared package that the bundle had
    /// imported again;</item>
    /// <item>a shared submodule kept aside for later bundles went back under a package the entering
    /// bundle owns.</item>
    /// </list>
    /// It also covers these findings from the review of pyrevitlabs/pyRevit#4138, which shows the same
    /// code:
    /// <list type="bullet">
    /// <item>a folder a bundle put first in a shared package's <c>__path__</c> came back last on its
    /// later calls;</item>
    /// <item>leaving a bundle took a folder out of a shared package's <c>__path__</c> that code outside
    /// any bundle had added again;</item>
    /// <item>a nested bundle that gave a shared package a fixed-size <c>__path__</c>, or whose bundle
    /// could not be set aside for another reason, left a bundle without its own modules, and the
    /// folder it put in a fixed-size <c>__path__</c> stayed there for the next bundle;</item>
    /// <item>a bundle whose <c>lib</c> has a module or package with the name of a shared one got the
    /// shared one once another bundle had loaded it;</item>
    /// <item>a module that code outside any bundle had loaded was lost when a bundle loaded a shared
    /// module of the same name.</item>
    /// </list>
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

        private static readonly string CountCallsOfLibModule =
            $"import {LibModuleName}\n{LibModuleName}.calls = getattr({LibModuleName}, 'calls', 0) + 1\n"
            + $"result = '%s %d' % ({LibModuleName}.VALUE, {LibModuleName}.calls)";

        private string _root = string.Empty;
        private object _engine = null!;
        private object _isolation = null!;
        private List<string> _baseSearchPaths = new List<string>();
        private List<string> _loggedFailures = new List<string>();

        [SetUp]
        public void SetUp()
        {
            _root = Path.Combine(Path.GetTempPath(), "pyRevitBundleIsolation_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_root);
            _engine = CreateEngine();
            _baseSearchPaths = GetSearchPaths();
            _loggedFailures = new List<string>();
            Type isolationType = LoaderAssembly().GetType("PyRevitLoader.BundleModuleIsolation", throwOnError: true)!;
            _isolation = Activator.CreateInstance(
                isolationType,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
                binder: null,
                args: new object?[] { _engine, new Action<string>(_loggedFailures.Add) },
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
        public void Dispose_BundleThatReplacedASharedModuleWithItsOwn_PutsTheSharedModuleBack()
        {
            string sharedRoot = CreateDirectory("pyrevitlib");
            File.WriteAllText(Path.Combine(sharedRoot, "common_mod.py"), "MARKS = []");
            Call(_isolation, "AddSharedRoot", sharedRoot);
            string replacerLib = CreateDirectory(Path.Combine("Replacer", "lib"));
            File.WriteAllText(Path.Combine(replacerLib, "common_mod.py"), "MARKS = ['replacer']");
            object first = CreateBundle("First", sharedRoot);
            object replacer = CreateBundleWithSharedRootFirst("Replacer", sharedRoot);
            string readMarks = "import common_mod\nresult = ','.join(common_mod.MARKS)";

            using (Enter(first))
                Execute("import common_mod\ncommon_mod.MARKS.append('first')");
            using (Enter(replacer))
                Execute($"import sys\ndel sys.modules['common_mod']\nsys.path.insert(0, {PythonString(replacerLib)})\nimport common_mod");

            using (Enter(first))
                Assert.That(Execute(readMarks), Is.EqualTo("first"));
            using (Enter(replacer))
                Assert.That(Execute(readMarks), Is.EqualTo("replacer"));
        }

        [Test]
        public void Enter_BundleWithItsOwnModuleOfASharedModulesName_ImportsItsOwnAfterAnotherBundleLoadedTheShared()
        {
            string sharedRoot = CreateSharedLibModule();
            object withoutOwn = CreateBundle("WithoutOwn", sharedRoot);
            object withOwn = CreateBundleWithLibModule("WithOwn", "VALUE = 'own'", sharedRoot);

            using (Enter(withoutOwn))
                Assert.That(Execute(CountCallsOfLibModule), Is.EqualTo("shared 1"));
            using (Enter(withOwn))
                Assert.That(Execute(CountCallsOfLibModule), Is.EqualTo("own 1"));
            using (Enter(withoutOwn))
                Assert.That(Execute(CountCallsOfLibModule), Is.EqualTo("shared 2"));
        }

        [Test]
        public void Enter_BundleWhoseOwnModuleComesAfterTheSharedRoot_GetsTheSharedModule()
        {
            string sharedRoot = CreateSharedLibModule();
            object withoutOwn = CreateBundle("WithoutOwn", sharedRoot);
            string lib = CreateDirectory(Path.Combine("SharedFirst", "lib"));
            File.WriteAllText(Path.Combine(lib, LibModuleName + ".py"), "VALUE = 'own'");
            object sharedFirst = CreateBundleWithSharedRootFirst("SharedFirst", sharedRoot);

            using (Enter(withoutOwn))
                Assert.That(Execute(CountCallsOfLibModule), Is.EqualTo("shared 1"));
            using (Enter(sharedFirst))
                Assert.That(Execute(CountCallsOfLibModule), Is.EqualTo("shared 2"));
        }

        [Test]
        public void Enter_BundleWithItsOwnPackageOfASharedPackagesName_ImportsItsOwnSubmodules()
        {
            string sharedRoot = CreateSharedPackage();
            File.WriteAllText(Path.Combine(sharedRoot, "spkg", "other.py"), "VALUE = 'shared'");
            object withoutOwn = CreateBundle("WithoutOwn", sharedRoot);
            string ownPackage = CreateDirectory(Path.Combine("WithOwn", "lib", "spkg"));
            File.WriteAllText(Path.Combine(ownPackage, "__init__.py"), string.Empty);
            File.WriteAllText(Path.Combine(ownPackage, "other.py"), "VALUE = 'own'");
            object withOwn = CreateBundle("WithOwn", sharedRoot);
            string readOther = "import spkg.other\nresult = spkg.other.VALUE";

            using (Enter(withoutOwn))
                Assert.That(Execute(readOther), Is.EqualTo("shared"));
            using (Enter(withOwn))
                Assert.That(Execute(readOther), Is.EqualTo("own"));
            using (Enter(withoutOwn))
                Assert.That(Execute(readOther), Is.EqualTo("shared"));
        }

        [Test]
        public void Enter_BundleThatOwnsAPackageOfASharedPackagesName_ImportsItsOwnSubmodulesAfterAnotherBundleLoadedTheShared()
        {
            string sharedRoot = CreateSharedPackage();
            File.WriteAllText(Path.Combine(sharedRoot, "spkg", "other.py"), "VALUE = 'shared'");
            object withoutOwn = CreateBundle("WithoutOwn", sharedRoot);
            string folder = PythonString(CreateDirectory("OwnPackages"));
            string ownPackage = CreateDirectory(Path.Combine("OwnPackages", "spkg"));
            File.WriteAllText(Path.Combine(ownPackage, "__init__.py"), string.Empty);
            File.WriteAllText(Path.Combine(ownPackage, "other.py"), "VALUE = 'own'");
            object owner = CreateBundleWithSharedRootFirst("Owner", sharedRoot);
            string readOther = "import spkg.other\nresult = spkg.other.VALUE";

            using (Enter(owner))
                Execute($"import sys\nsys.path.insert(0, {folder})\nimport spkg\nsys.path.remove({folder})");
            using (Enter(withoutOwn))
                Assert.That(Execute(readOther), Is.EqualTo("shared"));
            using (Enter(owner))
                Assert.That(Execute(readOther), Is.EqualTo("own"));
        }

        [Test]
        public void Enter_BundleThatOwnsANestedPackage_ImportsItsOwnSubmoduleAfterAnotherBundleLoadedTheShared()
        {
            string sharedRoot = CreateSharedPackage();
            string sharedPlugins = CreateDirectory(Path.Combine("site-packages", "spkg", "plugins"));
            File.WriteAllText(Path.Combine(sharedPlugins, "__init__.py"), string.Empty);
            File.WriteAllText(Path.Combine(sharedPlugins, "sub.py"), "VALUE = 'shared'");
            object other = CreateBundle("Other", sharedRoot);
            string ownParent = CreateDirectory(Path.Combine("Owner", "lib", "spkg_ext"));
            string ownPlugins = CreateDirectory(Path.Combine("Owner", "lib", "spkg_ext", "plugins"));
            File.WriteAllText(Path.Combine(ownPlugins, "__init__.py"), string.Empty);
            File.WriteAllText(Path.Combine(ownPlugins, "sub.py"), "VALUE = 'own'");
            object owner = CreateBundle("Owner", sharedRoot);
            string readSub = "from spkg.plugins import sub\nresult = sub.VALUE";

            using (Enter(owner))
                Execute($"import spkg\nspkg.__path__.insert(0, {PythonString(ownParent)})\nimport spkg.plugins");
            using (Enter(other))
                Assert.That(Execute(readSub), Is.EqualTo("shared"));
            using (Enter(owner))
                Assert.That(Execute(readSub), Is.EqualTo("own"));
            using (Enter(other))
                Assert.That(Execute(readSub), Is.EqualTo("shared"));
        }

        [Test]
        public void Enter_BundleThatOwnsANestedPackage_ImportsItsOwnSubmoduleOverASharedOneKeptAside()
        {
            string sharedRoot = CreateSharedPackage();
            string sharedPlugins = CreateDirectory(Path.Combine("site-packages", "spkg", "plugins"));
            File.WriteAllText(Path.Combine(sharedPlugins, "__init__.py"), string.Empty);
            File.WriteAllText(Path.Combine(sharedPlugins, "sub.py"), "VALUE = 'shared'");
            string outside = CreateDirectory("Outside");
            File.WriteAllText(Path.Combine(outside, "sub.py"), "VALUE = 'outside'");
            object other = CreateBundle("Other", sharedRoot);
            string ownParent = CreateDirectory(Path.Combine("Owner", "lib", "spkg_ext"));
            string ownPlugins = CreateDirectory(Path.Combine("Owner", "lib", "spkg_ext", "plugins"));
            File.WriteAllText(Path.Combine(ownPlugins, "__init__.py"), string.Empty);
            File.WriteAllText(Path.Combine(ownPlugins, "sub.py"), "VALUE = 'own'");
            object owner = CreateBundle("Owner", sharedRoot);
            string readSub = "from spkg.plugins import sub\nresult = sub.VALUE";

            using (Enter(owner))
                Execute($"import spkg\nspkg.__path__.insert(0, {PythonString(ownParent)})\nimport spkg.plugins");
            Assert.That(
                Execute($"import spkg.plugins\nspkg.plugins.__path__.insert(0, {PythonString(outside)})\n{readSub}\nspkg.plugins.__path__.remove({PythonString(outside)})"),
                Is.EqualTo("outside"));
            using (Enter(other))
                Assert.That(Execute(readSub), Is.EqualTo("shared"));
            using (Enter(owner))
                Assert.That(Execute(readSub), Is.EqualTo("own"));
            using (Enter(other))
                Assert.That(Execute(readSub), Is.EqualTo("shared"));
        }

        [Test]
        public void Dispose_BundleThatLoadedASharedModuleOverOneFromOutsideAnyBundle_PutsThatOneBack()
        {
            string sharedRoot = CreateSharedLibModule();
            object fallback = CreateBundle("Fallback", sharedRoot);
            CreateBundleWithLibModule("Unscoped", "VALUE = 'unscoped'");

            Assert.That(Execute(CountCallsOfLibModule), Is.EqualTo("unscoped 1"));
            using (Enter(fallback))
                Assert.That(Execute(CountCallsOfLibModule), Is.EqualTo("shared 1"));
            Assert.That(Execute(CountCallsOfLibModule), Is.EqualTo("unscoped 2"));
            using (Enter(fallback))
                Assert.That(Execute(CountCallsOfLibModule), Is.EqualTo("shared 2"));
        }

        [Test]
        public void Enter_SubmoduleOfAnOwnedPackageUnderASharedRoot_MovesWithItsPackage()
        {
            string sharedRoot = CreateDirectory("site-packages");
            string sharedPart = CreateSharedPackagePart(sharedRoot);
            object owner = CreateBundleWithPackage("Owner", sharedPart, sharedRoot);

            using (Enter(owner))
                Execute("import pkg.sub");

            Assert.That(Execute("import sys\nresult = 'pkg' in sys.modules"), Is.False);
            Assert.That(Execute("import sys\nresult = 'pkg.sub' in sys.modules"), Is.False);
        }

        [Test]
        public void Enter_TwoBundlesWhosePackagesExtendIntoTheSameSharedFolder_EachGetsTheSubmoduleOnItsOwnPackage()
        {
            string sharedRoot = CreateDirectory("site-packages");
            string sharedPart = CreateSharedPackagePart(sharedRoot);
            object first = CreateBundleWithPackage("First", sharedPart, sharedRoot);
            object second = CreateBundleWithPackage("Second", sharedPart, sharedRoot);

            using (Enter(first))
                Assert.That(Execute("import pkg.sub\nresult = pkg.sub.VALUE"), Is.EqualTo("shared"));
            using (Enter(second))
                Assert.That(Execute("import pkg.sub\nresult = pkg.sub.VALUE"), Is.EqualTo("shared"));
            using (Enter(first))
                Assert.That(Execute("import pkg.sub\nresult = pkg.sub.VALUE"), Is.EqualTo("shared"));
        }

        [Test]
        public void Enter_TwoBundlesThatAddAPackageToASharedPackage_EachGetsTheSubmoduleOnItsOwnPackage()
        {
            string sharedRoot = CreateDirectory("site-packages");
            string sharedPackage = CreateDirectory(Path.Combine("site-packages", "spkg"));
            File.WriteAllText(Path.Combine(sharedPackage, "__init__.py"), string.Empty);
            string sharedPart = CreateSharedPackagePart(sharedRoot);
            object first = CreateBundleWithPackageForSharedPackage("First", sharedPart, sharedRoot);
            object second = CreateBundleWithPackageForSharedPackage("Second", sharedPart, sharedRoot);

            using (Enter(first))
                Assert.That(Execute(ImportSubmoduleThroughSharedPackage("First")), Is.EqualTo("shared"));
            Assert.That(Execute("import sys\nresult = 'spkg.plugins.sub' in sys.modules"), Is.False);
            using (Enter(second))
                Assert.That(Execute(ImportSubmoduleThroughSharedPackage("Second")), Is.EqualTo("shared"));
        }

        [Test]
        public void Dispose_BundleThatReloadedASubmoduleOfItsPackage_KeepsTheEarlierCopyFromOtherBundles()
        {
            string sharedRoot = CreateDirectory("site-packages");
            string sharedPart = CreateSharedPackagePart(sharedRoot);
            object reloader = CreateBundleWithPackage("Reloader", sharedPart, sharedRoot);
            object other = CreateBundleWithPackage("Other", sharedPart, sharedRoot);

            using (Enter(reloader))
                Execute("import pkg.sub");
            using (Enter(reloader))
                Execute("import sys\ndel sys.modules['pkg.sub']\nimport pkg.sub");

            using (Enter(other))
                Assert.That(Execute("import pkg.sub\nresult = pkg.sub.VALUE"), Is.EqualTo("shared"));
        }

        [Test]
        public void Enter_TwoBundlesThatAddAPackageToASharedPackage_EachGetsItsOwnFromTheSharedPackage()
        {
            string sharedRoot = CreateDirectory("site-packages");
            string sharedPackage = CreateDirectory(Path.Combine("site-packages", "spkg"));
            File.WriteAllText(Path.Combine(sharedPackage, "__init__.py"), string.Empty);
            string sharedPart = CreateSharedPackagePart(sharedRoot);
            object first = CreateBundleWithPackageForSharedPackage("First", sharedPart, sharedRoot);
            object second = CreateBundleWithPackageForSharedPackage("Second", sharedPart, sharedRoot);

            using (Enter(first))
                Assert.That(Execute(ImportPackageFromSharedPackage("First")), Is.EqualTo("First"));
            using (Enter(second))
                Assert.That(Execute(ImportPackageFromSharedPackage("Second")), Is.EqualTo("Second"));
            using (Enter(first))
                Assert.That(Execute("from spkg import plugins\nresult = plugins.VALUE"), Is.EqualTo("First"));

            Assert.That(Execute("import spkg\nresult = '%s %d' % (hasattr(spkg, 'plugins'), len(spkg.__path__))"), Is.EqualTo("False 1"));
        }

        [Test]
        public void Enter_BundleThatPutItsFolderFirstInASharedPackage_FindsItsSubmoduleThereOnLaterCalls()
        {
            string sharedRoot = CreateSharedPackage();
            File.WriteAllText(Path.Combine(sharedRoot, "spkg", "other.py"), "VALUE = 'shared'");
            string folder = CreateDirectory(Path.Combine("First", "lib", "spkg_ext"));
            File.WriteAllText(Path.Combine(folder, "other.py"), "VALUE = 'First'");
            object bundle = CreateBundle("First", sharedRoot);

            using (Enter(bundle))
                Execute($"import spkg\nspkg.__path__.insert(0, {PythonString(folder)})");
            using (Enter(bundle))
                Assert.That(Execute("import spkg.other\nresult = spkg.other.VALUE"), Is.EqualTo("First"));
        }

        [Test]
        public void Enter_SharedFolderAddedBeforeTheBundlesNeighbour_KeepsTheBundlesFolderNextToThatNeighbour()
        {
            string sharedRoot = CreateDirectory("site-packages");
            string left = CreateDirectory(Path.Combine("site-packages", "spkg"));
            string right = CreateDirectory(Path.Combine("site-packages", "spkg_right"));
            string front = CreateDirectory(Path.Combine("site-packages", "spkg_front"));
            File.WriteAllText(Path.Combine(left, "__init__.py"), $"__path__.append({PythonString(right)})");
            File.WriteAllText(Path.Combine(left, "leaf.py"), "VALUE = 'left'");
            Call(_isolation, "AddSharedRoot", sharedRoot);
            string folder = CreateDirectory(Path.Combine("First", "lib", "spkg_ext"));
            File.WriteAllText(Path.Combine(folder, "leaf.py"), "VALUE = 'First'");
            object bundle = CreateBundle("First", sharedRoot);

            using (Enter(bundle))
                Execute($"import spkg\nspkg.__path__.insert(1, {PythonString(folder)})");
            Execute($"import spkg\nspkg.__path__.insert(0, {PythonString(front)})");
            using (Enter(bundle))
                Assert.That(Execute("import spkg.leaf\nresult = spkg.leaf.VALUE"), Is.EqualTo("left"));
        }

        [Test]
        public void Enter_BundleWhoseNeighbourIsListedTwice_PutsItsFolderBackWhereItWas()
        {
            string sharedRoot = CreateDirectory("site-packages");
            string package = CreateDirectory(Path.Combine("site-packages", "spkg"));
            string right = CreateDirectory(Path.Combine("site-packages", "spkg_right"));
            File.WriteAllText(Path.Combine(package, "__init__.py"), $"__path__.extend([{PythonString(right)}, __path__[0]])");
            File.WriteAllText(Path.Combine(right, "leaf.py"), "VALUE = 'right'");
            Call(_isolation, "AddSharedRoot", sharedRoot);
            string folder = CreateDirectory(Path.Combine("First", "lib", "spkg_ext"));
            File.WriteAllText(Path.Combine(folder, "leaf.py"), "VALUE = 'First'");
            object bundle = CreateBundle("First", sharedRoot);

            using (Enter(bundle))
                Execute($"import spkg\nspkg.__path__.append({PythonString(folder)})");
            using (Enter(bundle))
                Assert.That(Execute("import spkg.leaf\nresult = spkg.leaf.VALUE"), Is.EqualTo("right"));
        }

        [Test]
        public void Enter_BundleWhoseFoldersCannotAllGoBack_TakesOutTheOnesItPutBack()
        {
            string sharedRoot = CreateSharedPackage();
            string first = CreateDirectory(Path.Combine("First", "lib", "first_part"));
            string second = CreateDirectory(Path.Combine("First", "lib", "second_part"));
            object bundle = CreateBundle("First", sharedRoot);
            string hasFirst = $"import spkg\nresult = {PythonString(first)} in spkg.__path__";

            using (Enter(bundle))
                Execute($"import spkg\nspkg.__path__.append({PythonString(first)})\nspkg.__path__.append({PythonString(second)})");
            Execute(
                "import spkg\nfrom System.Collections import ArrayList\n"
                + "class RejectsSecondPart(ArrayList):\n    def Insert(self, index, value):\n"
                + "        if value.endswith('second_part'):\n            raise ValueError('rejected')\n"
                + "        ArrayList.Insert(self, index, value)\n"
                + "spkg.__path__ = RejectsSecondPart(list(spkg.__path__))");
            using (Enter(bundle))
                Assert.That(Execute(hasFirst), Is.False);

            Assert.That(Execute(hasFirst), Is.False);
            Assert.That(_loggedFailures, Has.Some.Contains("bring back the modules of 'First'"));
        }

        [Test]
        public void Dispose_BundleThatBoundItsPackageOverAnAlias_PutsTheAliasBack()
        {
            string sharedRoot = CreateSharedPackage();
            string sharedPart = CreateSharedPackagePart(sharedRoot);
            object bundle = CreateBundleWithPackageForSharedPackage("First", sharedPart, sharedRoot);
            string readAlias = "import spkg\nresult = getattr(getattr(spkg, 'plugins', None), '__name__', None)";

            using (Enter(bundle))
                Execute(ImportPackageFromSharedPackage("First"));
            Execute("import spkg, sys\nspkg.plugins = type(sys)('alias')");
            using (Enter(bundle))
                Assert.That(Execute("from spkg import plugins\nresult = plugins.VALUE"), Is.EqualTo("First"));

            Assert.That(Execute(readAlias), Is.EqualTo("alias"));
        }

        [Test]
        public void Dispose_BundleThatImportedItsPackageAgainOverAnAlias_PutsTheAliasBack()
        {
            string sharedRoot = CreateSharedPackage();
            string sharedPart = CreateSharedPackagePart(sharedRoot);
            object bundle = CreateBundleWithPackageForSharedPackage("First", sharedPart, sharedRoot);
            string readAlias = "import spkg\nresult = getattr(getattr(spkg, 'plugins', None), '__name__', None)";

            using (Enter(bundle))
                Execute(ImportPackageFromSharedPackage("First"));
            Execute("import spkg, sys\nspkg.plugins = type(sys)('alias')");
            using (Enter(bundle))
                Assert.That(
                    Execute("import spkg, sys\nloaded = spkg.plugins\ndel sys.modules['spkg.plugins']\nimport spkg.plugins\nresult = spkg.plugins is not loaded"),
                    Is.True);

            Assert.That(Execute(readAlias), Is.EqualTo("alias"));
        }

        [Test]
        public void Dispose_BundleThatImportedTheSharedPackageAgain_TakesItsPackageOffTheNewCopy()
        {
            string sharedRoot = CreateSharedPackage();
            string sharedPart = CreateSharedPackagePart(sharedRoot);
            object bundle = CreateBundleWithPackageForSharedPackage("First", sharedPart, sharedRoot);

            using (Enter(bundle))
                Execute(ImportPackageFromSharedPackage("First"));
            using (Enter(bundle))
                Assert.That(
                    Execute("import sys\ndel sys.modules['spkg']\nfrom spkg import plugins\nresult = sys.modules['spkg'].plugins.VALUE"),
                    Is.EqualTo("First"));

            Assert.That(Execute("import spkg\nresult = hasattr(spkg, 'plugins')"), Is.False);
        }

        [Test]
        public void Dispose_FolderThatCodeOutsideTheBundleAddedAgain_StaysInTheSharedPackage()
        {
            string sharedRoot = CreateSharedPackage();
            string sharedPart = CreateSharedPackagePart(sharedRoot);
            object bundle = CreateBundleWithPackageForSharedPackage("First", sharedPart, sharedRoot);
            string folder = PythonString(Path.Combine(_root, "First", "lib", "spkg_ext"));
            string hasFolder = $"import spkg\nresult = {folder} in spkg.__path__";

            using (Enter(bundle))
                Execute(ImportPackageFromSharedPackage("First"));
            Execute($"import spkg\nspkg.__path__.append({folder})");
            using (Enter(bundle))
                Assert.That(Execute("from spkg import plugins\nresult = plugins.VALUE"), Is.EqualTo("First"));
            Assert.That(Execute(hasFolder), Is.True);

            Execute($"import spkg\nspkg.__path__.remove({folder})");
            using (Enter(bundle))
                Assert.That(Execute(hasFolder), Is.True);
            Assert.That(Execute(hasFolder), Is.False);
        }

        [Test]
        public void Enter_AfterAnImportOutsideAnyBundle_TheNextBundleStillImportsItsOwnModule()
        {
            object second = CreateBundleWithLibModule("Second", "VALUE = 'second'");
            CreateBundleWithLibModule("First", "VALUE = 'first'");
            string readValue = $"import {LibModuleName}\nresult = {LibModuleName}.VALUE";

            Assert.That(Execute(readValue), Is.EqualTo("first"));

            Assert.That(ImportLibValue(second), Is.EqualTo("second"));
            Assert.That(Execute(readValue), Is.EqualTo("first"));
        }

        [Test]
        public void Enter_AfterAPackageWasImportedOutsideAnyBundle_TheNextBundleImportsItsOwnPackage()
        {
            string sharedRoot = CreateDirectory("site-packages");
            string sharedPart = CreateSharedPackagePart(sharedRoot);
            object isolated = CreateBundleWithPackage("Isolated", sharedPart, sharedRoot);
            CreateBundleWithPackage("Unscoped", sharedPart, sharedRoot);

            Execute("import pkg.sub");

            using (Enter(isolated))
                Assert.That(
                    Execute("import pkg.sub\nresult = pkg.sub.VALUE if 'Isolated' in pkg.__file__ else 'other package: ' + pkg.__file__"),
                    Is.EqualTo("shared"));
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
        public void Enter_OuterBundleAgainFromTheNestedBundle_EveryLevelKeepsItsOwnModule()
        {
            object outer = CreateBundleWithLibModule("Outer", "VALUE = 'outer'\ncalls = 0");
            object nested = CreateBundleWithLibModule("Nested", "VALUE = 'nested'");
            string countCall = $"import {LibModuleName}\n{LibModuleName}.calls += 1\nresult = {LibModuleName}.calls";
            string readValue = $"import {LibModuleName}\nresult = {LibModuleName}.VALUE";

            using (Enter(outer))
            {
                Execute(countCall);
                using (Enter(nested))
                {
                    using (Enter(outer))
                        Assert.That(Execute(countCall), Is.EqualTo(2));

                    Assert.That(Execute(readValue), Is.EqualTo("nested"));
                }

                Assert.That(Execute(countCall), Is.EqualTo(3));
            }
        }

        [Test]
        public void Dispose_NestedBundleThatMadeASharedPackagePathFixedSize_GivesTheOuterBundleItsModulesBack()
        {
            string sharedRoot = CreateSharedPackage();
            object outer = CreateBundleWithLibModule("Outer", "VALUE = 'outer'");
            object nested = CreateBundleWithLibModule("Nested", "VALUE = 'nested'", sharedRoot);
            string folder = PythonString(CreateDirectory(Path.Combine("Nested", "lib", "spkg_ext")));
            string readValue = $"import {LibModuleName}\nresult = {LibModuleName}.VALUE";

            using (Enter(outer))
            {
                Assert.That(Execute(readValue), Is.EqualTo("outer"));
                using (Enter(nested))
                    Execute($"import System, spkg\nspkg.__path__ = System.Array[System.String](list(spkg.__path__) + [{folder}])");

                Assert.That(Execute(readValue), Is.EqualTo("outer"));
            }

            Assert.That(_loggedFailures, Is.Empty);
        }

        [Test]
        public void Dispose_BundleThatMadeASharedPackagePathFixedSize_TakesItsFolderWithIt()
        {
            string sharedRoot = CreateSharedPackage();
            object other = CreateBundle("Other", sharedRoot);
            object fixer = CreateBundle("Fixer", sharedRoot);
            string folder = CreateDirectory(Path.Combine("Fixer", "lib", "spkg_ext"));
            File.WriteAllText(Path.Combine(folder, "extra.py"), "VALUE = 'Fixer'");
            string hasFolder = $"import spkg\nresult = {PythonString(folder)} in spkg.__path__";
            string importExtra = "try:\n    import spkg.extra\n    result = spkg.extra.VALUE\nexcept ImportError:\n    result = 'missing'";

            using (Enter(fixer))
                Execute($"import System, spkg\nspkg.__path__ = System.Array[System.String](list(spkg.__path__) + [{PythonString(folder)}])");
            using (Enter(other))
            {
                Assert.That(Execute(hasFolder), Is.False);
                Assert.That(Execute(importExtra), Is.EqualTo("missing"));
            }

            using (Enter(fixer))
                Assert.That(Execute(importExtra), Is.EqualTo("Fixer"));
            Assert.That(Execute(hasFolder), Is.False);
            Assert.That(_loggedFailures, Is.Empty);
        }

        [Test]
        public void EnterAndDispose_BundleThatCannotBeSetAside_TheNextBundleStillGetsItsOwnModule()
        {
            string sharedRoot = CreateSharedPackage();
            object outer = CreateBundleWithLibModule("Outer", "VALUE = 'outer'", sharedRoot);
            object nested = CreateBundleWithLibModule("Nested", "VALUE = 'nested'");
            string outerFolder = PythonString(CreateDirectory(Path.Combine("Outer", "lib", "spkg_ext")));
            string nestedFolder = PythonString(CreateDirectory(Path.Combine("Nested", "lib", "spkg_ext")));
            string readValue = $"import {LibModuleName}\nresult = {LibModuleName}.VALUE";

            using (Enter(outer))
            {
                Execute(readValue);
                Execute(
                    "import spkg\nfrom System.Collections import ArrayList\n"
                    + "class PathThatCannotShrink(ArrayList):\n    def RemoveAt(self, index):\n        raise ValueError('cannot shrink')\n"
                    + $"spkg.__path__ = PathThatCannotShrink(list(spkg.__path__) + [{outerFolder}])");
                using (Enter(nested))
                {
                    Assert.That(Execute(readValue), Is.EqualTo("nested"));
                    Execute($"import spkg\nspkg.__path__.Add({nestedFolder})");
                }

                Assert.That(Execute(readValue), Is.EqualTo("outer"));
            }

            Assert.That(_loggedFailures, Has.Count.EqualTo(2));
            Assert.That(_loggedFailures[0], Does.Contain("set aside the modules of 'Outer'"));
            Assert.That(_loggedFailures[1], Does.Contain("set aside the modules of 'Nested'"));
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

        private object CreateBundleWithLibModule(string name, string moduleSource, params string[] extraPaths)
        {
            string lib = CreateDirectory(Path.Combine(name, "lib"));
            File.WriteAllText(Path.Combine(lib, LibModuleName + ".py"), moduleSource);
            return CreateBundle(name, extraPaths);
        }

        private string CreateSharedPackage()
        {
            string sharedRoot = CreateDirectory("site-packages");
            string sharedPackage = CreateDirectory(Path.Combine("site-packages", "spkg"));
            File.WriteAllText(Path.Combine(sharedPackage, "__init__.py"), string.Empty);
            Call(_isolation, "AddSharedRoot", sharedRoot);
            return sharedRoot;
        }

        private string CreateSharedLibModule()
        {
            string sharedRoot = CreateDirectory("site-packages");
            File.WriteAllText(Path.Combine(sharedRoot, LibModuleName + ".py"), "VALUE = 'shared'");
            Call(_isolation, "AddSharedRoot", sharedRoot);
            return sharedRoot;
        }

        private object CreateBundleWithSharedRootFirst(string name, string sharedRoot)
        {
            string bundleDirectory = CreateDirectory(name);
            var paths = new List<string>(_baseSearchPaths) { sharedRoot, bundleDirectory, Path.Combine(bundleDirectory, "lib") };
            SetSearchPaths(paths);
            return Call(_isolation, "CreateBundle", name)!;
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

        private string CreateSharedPackagePart(string sharedRoot)
        {
            string sharedPart = CreateDirectory(Path.Combine(Path.GetFileName(sharedRoot), "pkg_ext"));
            File.WriteAllText(Path.Combine(sharedPart, "sub.py"), "VALUE = 'shared'");
            Call(_isolation, "AddSharedRoot", sharedRoot);
            return sharedPart;
        }

        private object CreateBundleWithPackage(string name, string extraPackagePath, string sharedRoot)
        {
            string package = CreateDirectory(Path.Combine(name, "lib", "pkg"));
            File.WriteAllText(Path.Combine(package, "__init__.py"), $"__path__.append({PythonString(extraPackagePath)})");
            return CreateBundle(name, sharedRoot);
        }

        private object CreateBundleWithPackageForSharedPackage(string name, string extraPackagePath, string sharedRoot)
        {
            string package = CreateDirectory(Path.Combine(name, "lib", "spkg_ext", "plugins"));
            File.WriteAllText(
                Path.Combine(package, "__init__.py"),
                $"__path__.append({PythonString(extraPackagePath)})\nVALUE = {PythonString(name)}");
            return CreateBundle(name, sharedRoot);
        }

        private string ImportSubmoduleThroughSharedPackage(string bundleName)
        {
            return ExtendSharedPackage(bundleName) + "import spkg.plugins.sub\nresult = spkg.plugins.sub.VALUE";
        }

        private string ImportPackageFromSharedPackage(string bundleName)
        {
            return ExtendSharedPackage(bundleName) + "from spkg import plugins\nresult = plugins.VALUE";
        }

        private string ExtendSharedPackage(string bundleName)
        {
            string packageParent = Path.Combine(_root, bundleName, "lib", "spkg_ext");
            return $"import spkg\nspkg.__path__.append({PythonString(packageParent)})\n";
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
