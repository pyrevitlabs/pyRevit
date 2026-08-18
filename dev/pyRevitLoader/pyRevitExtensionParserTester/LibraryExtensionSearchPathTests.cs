using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTester
{
    [TestFixture]
    public class LibraryExtensionSearchPathTests : TempFileTestBase
    {
        [Test]
        public void Collect_IncludesRootAndNestedLibWhenPresent()
        {
            var libRoot = CreateSubDirectory("DummyLib.lib");
            var nested = Path.Combine(libRoot, "lib");
            Directory.CreateDirectory(nested);

            var paths = LibraryExtensionSearchPaths.Collect(new[]
            {
                new ParsedExtension { Directory = libRoot }
            });

            CollectionAssert.AreEqual(
                new[] { libRoot, nested }.Select(Path.GetFullPath),
                paths.Select(Path.GetFullPath));
        }

        [Test]
        public void Collect_RootOnlyWhenNestedLibMissing()
        {
            var libRoot = CreateSubDirectory("DummyLib.lib");

            var paths = LibraryExtensionSearchPaths.Collect(new[]
            {
                new ParsedExtension { Directory = libRoot }
            });

            CollectionAssert.AreEqual(new[] { libRoot }, paths);
        }

        [Test]
        public void CacheSeed_ChangesWhenNestedLibAppears()
        {
            var libRoot = CreateSubDirectory("DummyLib.lib");
            var libs = new List<ParsedExtension>
            {
                new ParsedExtension { Directory = libRoot }
            };

            var before = LibraryExtensionSearchPaths.CacheSeed(libs);
            Directory.CreateDirectory(Path.Combine(libRoot, "lib"));
            var after = LibraryExtensionSearchPaths.CacheSeed(libs);

            Assert.AreNotEqual(before, after);
            StringAssert.Contains(Path.Combine(libRoot, "lib"), after);
        }

        [Test]
        public void GenerateExtensionCode_BakesRootAndNestedLibIntoSearchPaths()
        {
            CreateSubDirectory("DummyUi.extension/Dummy.tab/Smoke.panel/Check.pushbutton");
            CreateFile("DummyUi.extension/Dummy.tab/Smoke.panel/Check.pushbutton/script.py", "print(1)");

            var libRoot = CreateSubDirectory("DummyLib.lib");
            var nested = Path.Combine(libRoot, "lib");
            Directory.CreateDirectory(nested);

            var uiDir = Path.Combine(TestTempDir, "DummyUi.extension");
            var ui = ParseInstalledExtensions(new[] { uiDir }).First();
            var libs = new[] { new ParsedExtension { Directory = libRoot, Name = "DummyLib" } };

            var code = new RoslynCommandTypeGenerator(new MockPythonLogger())
                .GenerateExtensionCode(ui, "2024", libs);

            StringAssert.Contains(libRoot, code);
            StringAssert.Contains(nested, code);
        }

        [Test]
        public void CacheSeed_SameLibrariesDifferentOrder_AreEqual()
        {
            var libA = CreateSubDirectory("A.lib");
            var libB = CreateSubDirectory("Z.lib");
            Directory.CreateDirectory(Path.Combine(libB, "lib"));

            var a = new ParsedExtension { Directory = libA };
            var b = new ParsedExtension { Directory = libB };

            var forward = LibraryExtensionSearchPaths.CacheSeed(new[] { a, b });
            var reverse = LibraryExtensionSearchPaths.CacheSeed(new[] { b, a });

            Assert.AreEqual(forward, reverse);
        }

        [Test]
        public void Collect_NullLibraryExtensions_ReturnsEmpty()
        {
            CollectionAssert.IsEmpty(LibraryExtensionSearchPaths.Collect(null!));
            Assert.AreEqual(string.Empty, LibraryExtensionSearchPaths.CacheSeed(null!));
        }
    }
}
