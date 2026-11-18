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
    /// A command's <c>lib</c> and <c>bin</c> folders come from the extension, the command's ancestors and the
    /// command itself, never from another bundle. The loader used to add the folders of every component its
    /// depth-first search passed on the way to the command, so a command that shipped a module also found in
    /// an earlier sibling's <c>lib</c> imported the sibling's copy.
    /// </summary>
    /// <remarks>
    /// Every component of the fixture has a <c>lib</c> and a <c>bin</c> folder. The layouts put
    /// <c>Before.panel</c> ahead of <c>Main.panel</c>, and <c>Earlier</c> and <c>Group</c> (holding
    /// <c>Nested</c>) ahead of <c>Target</c>, which comes before <c>Later</c>.
    /// </remarks>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    [Category("Regression")]
    public class CommandAncestorFoldersTests : TempFileTestBase
    {
        private const string VerbatimStringArgument = "@\"((?:[^\"]|\"\")*)\"";

        private ParsedExtension _extension = null!;

        private string ExtensionDir => Path.Combine(TestTempDir, "Folders.extension");

        private string TabDir => Path.Combine(ExtensionDir, "Folders.tab");

        private string BeforePanelDir => Path.Combine(TabDir, "Before.panel");

        private string OtherDir => Path.Combine(BeforePanelDir, "Other.pushbutton");

        private string PanelDir => Path.Combine(TabDir, "Main.panel");

        private string EarlierDir => Path.Combine(PanelDir, "Earlier.pushbutton");

        private string GroupDir => Path.Combine(PanelDir, "Group.pulldown");

        private string NestedDir => Path.Combine(GroupDir, "Nested.pushbutton");

        private string TargetDir => Path.Combine(PanelDir, "Target.pushbutton");

        private string LaterDir => Path.Combine(PanelDir, "Later.pushbutton");

        [SetUp]
        public void CreateExtension()
        {
            foreach (var command in new[] { OtherDir, EarlierDir, NestedDir, TargetDir, LaterDir })
            {
                Directory.CreateDirectory(command);
                File.WriteAllText(Path.Combine(command, "script.py"), "pass");
            }

            File.WriteAllText(Path.Combine(TabDir, "bundle.yaml"), "layout:\n  - Before\n  - Main\n");
            File.WriteAllText(Path.Combine(PanelDir, "bundle.yaml"),
                "layout:\n  - Earlier\n  - Group\n  - Target\n  - Later\n");

            var components = new[]
            {
                ExtensionDir, TabDir, BeforePanelDir, OtherDir, PanelDir,
                EarlierDir, GroupDir, NestedDir, TargetDir, LaterDir,
            };
            foreach (var component in components)
            {
                Directory.CreateDirectory(Lib(component));
                Directory.CreateDirectory(Bin(component));
            }

            _extension = ParseInstalledExtensions(new[] { ExtensionDir }).Single();
        }

        [Test]
        public void LibraryPaths_AreTheExtensionAncestorAndOwnLibFolders()
        {
            var paths = _extension.CollectLibraryPaths(Command(TargetDir));

            Assert.That(paths, Is.EqualTo(new[]
            {
                Lib(ExtensionDir), Lib(TabDir), Lib(PanelDir), Lib(TargetDir),
            }));
        }

        [Test]
        public void BinaryPaths_AreTheExtensionAncestorAndOwnBinFoldersThenTheBundle()
        {
            var paths = _extension.CollectBinaryPaths(Command(TargetDir));

            Assert.That(paths, Is.EqualTo(new[]
            {
                Bin(ExtensionDir), Bin(TabDir), Bin(PanelDir), Bin(TargetDir), TargetDir,
            }));
        }

        [Test]
        public void CommandInAPulldown_GetsThePulldownFoldersButNotThoseOfItsSiblings()
        {
            var nested = Command(NestedDir);

            Assert.Multiple(() =>
            {
                Assert.That(_extension.CollectLibraryPaths(nested), Is.EqualTo(new[]
                {
                    Lib(ExtensionDir), Lib(TabDir), Lib(PanelDir), Lib(GroupDir), Lib(NestedDir),
                }));
                Assert.That(_extension.CollectBinaryPaths(nested), Is.EqualTo(new[]
                {
                    Bin(ExtensionDir), Bin(TabDir), Bin(PanelDir), Bin(GroupDir), Bin(NestedDir), NestedDir,
                }));
            });
        }

        [Test]
        public void CompiledSearchPaths_HoldOnlyTheCommandsOwnAndAncestorFolders()
        {
            var target = Command(TargetDir);
            var code = new RoslynCommandTypeGenerator(new MockPythonLogger())
                .GenerateExtensionCode(_extension, "2024", Array.Empty<ParsedExtension>());

            var fixtureFolders = CompiledSearchPaths(code, target.ScriptPath)
                .Where(p => p.StartsWith(TestTempDir, StringComparison.OrdinalIgnoreCase))
                .ToList();

            Assert.That(fixtureFolders, Is.EqualTo(new[]
            {
                TargetDir,
                Lib(ExtensionDir), Lib(TabDir), Lib(PanelDir), Lib(TargetDir),
                Bin(ExtensionDir), Bin(TabDir), Bin(PanelDir), Bin(TargetDir),
            }));
        }

        [Test]
        public void BundleModule_ResolvesFromTheCommandsBinNotAnEarlierSiblings()
        {
            File.WriteAllText(Path.Combine(Bin(EarlierDir), "Shared.dll"), string.Empty);
            var ownModule = Path.Combine(Bin(TargetDir), "Shared.dll");
            File.WriteAllText(ownModule, string.Empty);

            Assert.That(_extension.FindModuleDll("Shared.dll", Command(TargetDir)), Is.EqualTo(ownModule));
        }

        [Test]
        public void ComponentOutsideTheExtensionTree_GetsTheExtensionAndItsOwnFolders()
        {
            var strayDir = CreateSubDirectory("Stray.pushbutton");
            Directory.CreateDirectory(Lib(strayDir));
            Directory.CreateDirectory(Bin(strayDir));
            var stray = new ParsedComponent { Directory = strayDir };

            Assert.Multiple(() =>
            {
                Assert.That(_extension.CollectLibraryPaths(stray), Is.EqualTo(new[]
                {
                    Lib(ExtensionDir), Lib(strayDir),
                }));
                Assert.That(_extension.CollectBinaryPaths(stray), Is.EqualTo(new[]
                {
                    Bin(ExtensionDir), Bin(strayDir), strayDir,
                }));
            });
        }

        private ParsedComponent Command(string bundleDir)
        {
            return _extension.CollectCommandComponents().Single(c => c.Directory == bundleDir);
        }

        private static string Lib(string componentDir) => Path.Combine(componentDir, "lib");

        private static string Bin(string componentDir) => Path.Combine(componentDir, "bin");

        private static List<string> CompiledSearchPaths(string generatedCode, string scriptPath)
        {
            var scriptArgument = Regex.Escape(scriptPath.Replace("\"", "\"\""));
            var baseCall = Regex.Match(generatedCode,
                $"base\\(\\s*@\"{scriptArgument}\",\\s*{VerbatimStringArgument},\\s*{VerbatimStringArgument}");
            Assert.That(baseCall.Success, Is.True, "no command constructor for " + scriptPath);

            return baseCall.Groups[2].Value
                .Replace("\"\"", "\"")
                .Split(';')
                .Where(p => !string.IsNullOrEmpty(p))
                .ToList();
        }
    }
}
