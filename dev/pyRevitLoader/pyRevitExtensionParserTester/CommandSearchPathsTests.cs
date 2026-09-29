using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using NUnit.Framework;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// The search paths the C# loader bakes into every command. The bundle folder used to appear
    /// twice - once as the script's own directory and again as the tail of the collected binary
    /// paths - which put a duplicate entry on <c>sys.path</c> for every command. #3687.
    /// </summary>
    [TestFixture]
    public class CommandSearchPathsTests : TempFileTestBase
    {
        private const string Bundle = "DummyUi.extension/Dummy.tab/Smoke.panel/Check.pushbutton";

        private static List<string> SearchPathsFrom(string generatedCode)
        {
            // The search paths are the third argument of the ScriptCommand base call.
            Match ctor = Regex.Match(
                generatedCode,
                @"public\s+\w+\(\)\s*:\s*base\(",
                RegexOptions.None);
            Assert.That(ctor.Success, Is.True, "no ScriptCommand constructor found in generated code");

            int close = generatedCode.IndexOf(')', ctor.Index + ctor.Length);
            string args = generatedCode.Substring(ctor.Index + ctor.Length, close - ctor.Index - ctor.Length);

            return Regex.Matches(args, "@\"((?:[^\"]|\"\")*)\"")
                .Cast<Match>()
                .Select(m => m.Groups[1].Value.Replace("\"\"", "\""))
                .Skip(2)
                .First()
                .Split(';')
                .Where(p => !string.IsNullOrEmpty(p))
                .ToList();
        }

        private string Generate(string libraryExtensionDir = null)
        {
            CreateFile(Bundle + "/script.py", "print(1)");
            var uiDir = Path.Combine(TestTempDir, "DummyUi.extension");
            var ui = ParseInstalledExtensions(new[] { uiDir }).First();
            var libs = libraryExtensionDir == null
                ? new ParsedExtension[0]
                : new[] { new ParsedExtension { Directory = libraryExtensionDir, Name = "DummyLib" } };

            var code = new RoslynCommandTypeGenerator(new MockPythonLogger())
                .GenerateExtensionCode(ui, "2024", libs);
            return code;
        }

        private string BundleDir => Path.Combine(TestTempDir,
            "DummyUi.extension", "Dummy.tab", "Smoke.panel", "Check.pushbutton");

        [Test]
        public void BundleFolderAppearsOnce()
        {
            var paths = SearchPathsFrom(Generate());

            int occurrences = paths.Count(p => p == BundleDir);
            Assert.That(occurrences, Is.EqualTo(1),
                "bundle folder should appear exactly once, got: " + string.Join(" | ", paths));
        }

        [Test]
        public void NoEntryIsRepeated()
        {
            var paths = SearchPathsFrom(Generate());

            var repeated = paths
                .GroupBy(p => p, StringComparer.OrdinalIgnoreCase)
                .Where(g => g.Count() > 1)
                .Select(g => g.Key)
                .ToList();

            Assert.That(repeated, Is.Empty,
                "repeated search path entries: " + string.Join(" | ", repeated));
        }

        [Test]
        public void BundleFolderIsFirst()
        {
            var paths = SearchPathsFrom(Generate());

            // Python puts the script's own directory first; the documented order depends on it.
            Assert.That(paths[0], Is.EqualTo(BundleDir));
        }

        [Test]
        public void KeepsTheBundleBinFolderAlongsideTheBundle()
        {
            // A bundle that ships a bin/ folder needs both: bin/ for module DLLs, the bundle
            // itself for the script's own modules. They are different folders, not a duplicate.
            Directory.CreateDirectory(Path.Combine(BundleDir, "bin"));

            var paths = SearchPathsFrom(Generate());
            var bundleBin = Path.Combine(BundleDir, "bin");

            Assert.Multiple(() => {
                Assert.That(paths, Does.Contain(BundleDir));
                Assert.That(paths, Does.Contain(bundleBin));
            });
        }

        [Test]
        public void KeepsLibFolderAlongsideTheBundle()
        {
            Directory.CreateDirectory(Path.Combine(BundleDir, "lib"));

            var paths = SearchPathsFrom(Generate());
            var bundleLib = Path.Combine(BundleDir, "lib");

            Assert.Multiple(() => {
                Assert.That(paths, Does.Contain(BundleDir));
                Assert.That(paths, Does.Contain(bundleLib));
            });
        }

        [Test]
        public void KeepsExtensionBinAndLibFolders()
        {
            var extDir = Path.Combine(TestTempDir, "DummyUi.extension");
            Directory.CreateDirectory(Path.Combine(extDir, "bin"));
            Directory.CreateDirectory(Path.Combine(extDir, "lib"));

            var paths = SearchPathsFrom(Generate());

            Assert.Multiple(() => {
                Assert.That(paths, Does.Contain(Path.Combine(extDir, "bin")));
                Assert.That(paths, Does.Contain(Path.Combine(extDir, "lib")));
            });
        }

        [Test]
        public void KeepsLibraryExtensionPaths()
        {
            var libRoot = CreateSubDirectory("DummyLib.lib");
            Directory.CreateDirectory(Path.Combine(libRoot, "lib"));

            var paths = SearchPathsFrom(Generate(libRoot));

            Assert.Multiple(() => {
                Assert.That(paths, Does.Contain(libRoot));
                Assert.That(paths, Does.Contain(Path.Combine(libRoot, "lib")));
            });
        }

        [Test]
        public void KeepsPyrevitLibAndSitePackagesLast()
        {
            var paths = SearchPathsFrom(Generate());

            Assert.That(paths.Count, Is.GreaterThanOrEqualTo(2));
            Assert.That(paths[paths.Count - 2], Does.EndWith("pyrevitlib"));
            Assert.That(paths[paths.Count - 1], Does.EndWith("site-packages"));
        }

        [Test]
        public void PreservesTheDocumentedOrder()
        {
            // script dir, then lib folders, then bin folders, then library extensions,
            // then pyrevitlib and site-packages.
            var extDir = Path.Combine(TestTempDir, "DummyUi.extension");
            Directory.CreateDirectory(Path.Combine(extDir, "lib"));
            var libRoot = CreateSubDirectory("DummyLib.lib");

            var paths = SearchPathsFrom(Generate(libRoot));

            int bundle = paths.IndexOf(BundleDir);
            int extLib = paths.IndexOf(Path.Combine(extDir, "lib"));
            int libExt = paths.IndexOf(libRoot);
            int pyrevitLib = paths.FindIndex(p => p.EndsWith("pyrevitlib"));

            Assert.Multiple(() => {
                Assert.That(bundle, Is.EqualTo(0));
                Assert.That(extLib, Is.GreaterThan(bundle), "ext lib should follow the script dir");
                Assert.That(libExt, Is.GreaterThan(extLib), "library extensions come after lib folders");
                Assert.That(pyrevitLib, Is.GreaterThan(libExt), "pyrevitlib comes after library extensions");
            });
        }
    }
}
