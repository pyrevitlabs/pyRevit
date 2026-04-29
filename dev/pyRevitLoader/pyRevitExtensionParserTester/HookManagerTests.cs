using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Unit tests for <see cref="HookManager"/> hook filename parsing, hook IDs (Python parity),
    /// and hook script search paths.
    /// </summary>
    [TestFixture]
    public class HookManagerTests : TempFileTestBase
    {
        // -------------------------------------------------------------------------
        // TryParseHookFileName — same rules as Python hooks._get_hook_parts()
        // -------------------------------------------------------------------------

        [TestCase("doc-opened.py", "doc-opened", "")]
        [TestCase("doc-opened.cs", "doc-opened", "")]
        [TestCase("doc-opened.vb", "doc-opened", "")]
        [TestCase("command-before-exec[ID_INPLACE_COMPONENT].py", "command-before-exec", "ID_INPLACE_COMPONENT")]
        [TestCase("my event name[TARGET_ID].cs", "my event name", "TARGET_ID")]
        public void TryParseHookFileName_ValidNames_ReturnsTrue(
            string fileName,
            string expectedEventName,
            string expectedTarget)
        {
            var ok = HookManager.TryParseHookFileName(fileName, out var eventName, out var eventTarget);
            Assert.IsTrue(ok);
            Assert.AreEqual(expectedEventName, eventName);
            Assert.AreEqual(expectedTarget, eventTarget);
        }

        [TestCase("DOC-OPENED.py")]
        [TestCase("Doc-Opened.py")]
        [TestCase("no-extension")]
        [TestCase(".py")]
        public void TryParseHookFileName_InvalidNames_ReturnsFalse(string fileName)
        {
            var ok = HookManager.TryParseHookFileName(fileName, out var eventName, out var eventTarget);
            Assert.IsFalse(ok);
            Assert.AreEqual("", eventName);
            Assert.AreEqual("", eventTarget);
        }

        // -------------------------------------------------------------------------
        // CreateHookId — matches Python hooks._create_hook_id() via SanitizeClassName
        // -------------------------------------------------------------------------

        [Test]
        public void CreateHookId_MatchesSanitizeClassNameFormula()
        {
            var ext = new ParsedExtension { UniqueId = "myuiextension" };
            const string fileName = "doc-opened.py";
            var expected = SanitizeClassName(ext.UniqueId + "_" + fileName).ToLowerInvariant();
            Assert.AreEqual(expected, HookManager.CreateHookId(ext, fileName));
        }

        [Test]
        public void CreateHookId_Golden_doc_opened_py()
        {
            var ext = new ParsedExtension { UniqueId = "myext" };
            // SanitizeClassName emits MINUS/DOT tokens; _create_hook_id ends with .lower()
            Assert.AreEqual(
                "myext_docminusopeneddotpy",
                HookManager.CreateHookId(ext, "doc-opened.py"));
        }

        [Test]
        public void CreateHookId_Golden_withBracketedTarget()
        {
            var ext = new ParsedExtension { UniqueId = "ext" };
            const string fn = "command-before-exec[ID_INPLACE_COMPONENT].py";
            Assert.AreEqual(
                SanitizeClassName("ext_" + fn).ToLowerInvariant(),
                HookManager.CreateHookId(ext, fn));
        }

        // -------------------------------------------------------------------------
        // BuildHookSearchPaths — current C# behavior (per-extension lib/bin, each
        // library extension's lib/ if present, pyrevitlib + site-packages).
        // Python extensionmgr also adds library extension *root* to module_paths;
        // hook tests here intentionally assert C# HookManager only.
        // -------------------------------------------------------------------------

        [Test]
        public void BuildHookSearchPaths_OrderAndMembership()
        {
            var extDir = CreateSubDirectory("UiExt");
            Directory.CreateDirectory(Path.Combine(extDir, "lib"));
            Directory.CreateDirectory(Path.Combine(extDir, "bin"));

            var libWithLib = CreateSubDirectory("SharedLibWithLib");
            var libWithLibLib = Path.Combine(libWithLib, "lib");
            Directory.CreateDirectory(libWithLibLib);

            var libWithoutLib = CreateSubDirectory("SharedLibNoLibSubdir");

            var pyRoot = CreateSubDirectory("FakePyRevitRoot");
            var pyrevitlib = Path.Combine(pyRoot, "pyrevitlib");
            var sitePackages = Path.Combine(pyRoot, "site-packages");
            Directory.CreateDirectory(pyrevitlib);
            Directory.CreateDirectory(sitePackages);

            var uiExt = new ParsedExtension { Directory = extDir, Name = "UiExt" };
            var libs = new List<ParsedExtension>
            {
                new ParsedExtension { Directory = libWithLib },
                new ParsedExtension { Directory = libWithoutLib }
            };

            var hookManager = new HookManager(new MockPythonLogger());
            var paths = hookManager.BuildHookSearchPaths(uiExt, libs, pyRoot);

            var normalized = paths.Select(Path.GetFullPath).ToArray();
            var expected = new[]
            {
                Path.GetFullPath(Path.Combine(extDir, "lib")),
                Path.GetFullPath(Path.Combine(extDir, "bin")),
                Path.GetFullPath(libWithLibLib),
                Path.GetFullPath(pyrevitlib),
                Path.GetFullPath(sitePackages)
            };

            CollectionAssert.AreEqual(expected, normalized);
        }

        [Test]
        public void BuildHookSearchPaths_NullLibraryExtensions_SkipsLibraryLoop()
        {
            var extDir = CreateSubDirectory("ExtOnly");
            Directory.CreateDirectory(Path.Combine(extDir, "lib"));

            var hookManager = new HookManager(new MockPythonLogger());
            var paths = hookManager.BuildHookSearchPaths(
                new ParsedExtension { Directory = extDir },
                null!,
                pyRevitRoot: null);

            Assert.AreEqual(1, paths.Length);
            Assert.AreEqual(Path.GetFullPath(Path.Combine(extDir, "lib")), Path.GetFullPath(paths[0]));
        }

        [Test]
        public void BuildHookSearchPaths_NullOrMissingPyRevitRoot_OmitsCorePaths()
        {
            var extDir = CreateSubDirectory("Ext");
            Directory.CreateDirectory(Path.Combine(extDir, "lib"));

            var hookManager = new HookManager(new MockPythonLogger());
            var paths = hookManager.BuildHookSearchPaths(
                new ParsedExtension { Directory = extDir },
                new List<ParsedExtension>(),
                pyRevitRoot: "");

            Assert.AreEqual(1, paths.Length);
        }
    }
}
