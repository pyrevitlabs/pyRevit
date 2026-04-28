using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using System.IO;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    internal class HelpFileTests : TempFileTestBase
    {
        private IEnumerable<ParsedExtension>? _installedExtensions;

        [SetUp]
        public void Setup()
        {
            var testExtensionPath = CreateHelpFileTestExtension(TestTempDir);
            _installedExtensions = ParseInstalledExtensions(new[] { testExtensionPath });
        }

        private string CreateHelpFileTestExtension(string basePath)
        {
            var builder = new TestExtensionBuilder(basePath, "HelpFileTestExtension");
            builder.Create();

            var tabBuilder = builder.AddTab("HelpTab");
            var panelBuilder = tabBuilder.AddPanel("HelpPanel");

            // Button with only help.html file (no help_url in bundle.yaml)
            CreatePushButtonWithHelp(
                panelBuilder.PanelPath,
                "FileBasedHelp",
                "print('file based')",
                null,
                "<html><body>File Based Help</body></html>"
            );

            // Button with help_url in bundle.yaml (explicit URL, should take precedence)
            panelBuilder.AddPushButton("UrlBasedHelp", "print('url based')", @"title: URL Based Help
help_url: https://github.com/pyrevitlabs/pyRevit
");

            // Button with both help.html AND help_url (help_url should take precedence)
            CreatePushButtonWithHelp(
                panelBuilder.PanelPath,
                "PrecedenceTest",
                "print('precedence')",
                "help_url: https://explicit-url.example.com",
                "<html><body>Help File (Should NOT appear)</body></html>"
            );

            // Button with markdown help file
            CreatePushButtonWithHelp(
                panelBuilder.PanelPath,
                "MarkdownHelp",
                "print('markdown')",
                null,
                "# Markdown Help Test",
                "help.md"
            );

            // Button with localized help_url
            panelBuilder.AddPushButton("LocalizedHelp", "print('localized')", @"title: Localized Help
help_url:
  en_us: https://example.com/en/help
  fr_fr: https://example.com/fr/help
");

            // Button with no help at all
            panelBuilder.AddPushButton("NoHelp", "print('no help')", @"title: No Help Button
");

            return builder.ExtensionPath;
        }

        private string CreatePushButtonWithHelp(
            string parentDir,
            string buttonName,
            string scriptContent,
            string? bundleYaml,
            string helpContent,
            string helpFileName = "help.html")
        {
            var buttonDir = Path.Combine(parentDir, $"{buttonName}.pushbutton");
            Directory.CreateDirectory(buttonDir);

            File.WriteAllText(Path.Combine(buttonDir, "script.py"), scriptContent);

            if (!string.IsNullOrEmpty(bundleYaml))
            {
                File.WriteAllText(Path.Combine(buttonDir, "bundle.yaml"), bundleYaml);
            }

            File.WriteAllText(Path.Combine(buttonDir, helpFileName), helpContent);

            return buttonDir;
        }

        private ParsedComponent? FindComponentRecursively(ParsedComponent parent, string componentName)
        {
            if (parent.Name == componentName)
                return parent;

            if (parent.Children != null)
            {
                foreach (var child in parent.Children)
                {
                    var found = FindComponentRecursively(child, componentName);
                    if (found != null)
                        return found;
                }
            }

            return null;
        }

        [Test]
        public void TestFileBasedHelpIsDiscovered()
        {
            Assert.That(_installedExtensions, Is.Not.Null, "Extensions should be parsed");

            foreach (var extension in _installedExtensions!)
            {
                var fileBasedHelp = FindComponentRecursively(extension, "FileBasedHelp");
                Assert.That(fileBasedHelp, Is.Not.Null, "FileBasedHelp component should exist");

                TestContext.Out.WriteLine($"FileBasedHelp.HelpFile: {fileBasedHelp?.HelpFile ?? "null"}");

                Assert.That(fileBasedHelp, Is.Not.Null, "FileBasedHelp should be found");
                Assert.That(fileBasedHelp!.HelpFile, Is.Not.Null.And.Not.Empty,
                    "HelpFile should be discovered for FileBasedHelp");
                Assert.That(fileBasedHelp.HelpFile, Does.EndWith("help.html"),
                    "HelpFile should end with 'help.html'");
                Assert.That(File.Exists(fileBasedHelp.HelpFile), Is.True,
                    "HelpFile path should exist on disk");
            }
        }

        [Test]
        public void TestHelpFileHasHelpContent()
        {
            Assert.That(_installedExtensions, Is.Not.Null);

            foreach (var extension in _installedExtensions!)
            {
                var fileBasedHelp = FindComponentRecursively(extension, "FileBasedHelp");
                Assert.That(fileBasedHelp, Is.Not.Null);
                Assert.That(File.Exists(fileBasedHelp!.HelpFile), Is.True);

                var content = File.ReadAllText(fileBasedHelp.HelpFile);
                Assert.That(content, Does.Contain("File Based Help"),
                    "Help file content should be readable");
            }
        }

        [Test]
        public void TestUrlBasedHelpPrecedenceOverFile()
        {
            Assert.That(_installedExtensions, Is.Not.Null);

            foreach (var extension in _installedExtensions!)
            {
                var precedenceTest = FindComponentRecursively(extension, "PrecedenceTest");
                Assert.That(precedenceTest, Is.Not.Null, "PrecedenceTest should be found");

                TestContext.Out.WriteLine($"PrecedenceTest.HelpUrl: {precedenceTest?.HelpUrl ?? "null"}");
                TestContext.Out.WriteLine($"PrecedenceTest.HelpFile: {precedenceTest?.HelpFile ?? "null"}");

                Assert.That(precedenceTest!.HelpUrl, Is.EqualTo("https://explicit-url.example.com"),
                    "HelpUrl from bundle.yaml should be set");
                Assert.That(precedenceTest.HelpFile, Is.Not.Null.And.Not.Empty,
                    "HelpFile should still be discovered");
            }
        }

        [Test]
        public void TestGetLocalizedHelpUrlReturnsUrlWhenAvailable()
        {
            Assert.That(_installedExtensions, Is.Not.Null);

            foreach (var extension in _installedExtensions!)
            {
                var urlBasedHelp = FindComponentRecursively(extension, "UrlBasedHelp");
                Assert.That(urlBasedHelp, Is.Not.Null, "UrlBasedHelp should be found");

                var helpUrl = urlBasedHelp!.GetLocalizedHelpUrl();
                TestContext.Out.WriteLine($"UrlBasedHelp.GetLocalizedHelpUrl(): {helpUrl}");

                Assert.That(helpUrl, Is.EqualTo("https://github.com/pyrevitlabs/pyRevit"),
                    "GetLocalizedHelpUrl should return HelpUrl when set");
            }
        }

        [Test]
        public void TestGetLocalizedHelpUrlFallsBackToHelpFile()
        {
            Assert.That(_installedExtensions, Is.Not.Null);

            foreach (var extension in _installedExtensions!)
            {
                var fileBasedHelp = FindComponentRecursively(extension, "FileBasedHelp");
                Assert.That(fileBasedHelp, Is.Not.Null, "FileBasedHelp should be found");

                Assert.That(fileBasedHelp!.HelpUrl, Is.Null,
                    "HelpUrl should not be set (no help_url in bundle.yaml)");

                var helpUrl = fileBasedHelp.GetLocalizedHelpUrl();
                TestContext.Out.WriteLine($"FileBasedHelp.GetLocalizedHelpUrl(): {helpUrl ?? "null"}");

                Assert.That(helpUrl, Is.Not.Null.And.Not.Empty,
                    "GetLocalizedHelpUrl should fall back to HelpFile");
                Assert.That(helpUrl, Does.EndWith("help.html"),
                    "Fallback should be the HelpFile path");
            }
        }

        [Test]
        public void TestMarkdownHelpFileIsDiscovered()
        {
            Assert.That(_installedExtensions, Is.Not.Null);

            foreach (var extension in _installedExtensions!)
            {
                var markdownHelp = FindComponentRecursively(extension, "MarkdownHelp");
                Assert.That(markdownHelp, Is.Not.Null, "MarkdownHelp should be found");

                TestContext.Out.WriteLine($"MarkdownHelp.HelpFile: {markdownHelp?.HelpFile ?? "null"}");

                Assert.That(markdownHelp!.HelpFile, Is.Not.Null.And.Not.Empty,
                    "HelpFile should be discovered for MarkdownHelp");
                Assert.That(markdownHelp.HelpFile, Does.EndWith("help.md"),
                    "HelpFile should end with 'help.md'");
            }
        }

        [Test]
        public void TestLocalizedHelpUrlsAreParsed()
        {
            Assert.That(_installedExtensions, Is.Not.Null);

            foreach (var extension in _installedExtensions!)
            {
                var localizedHelp = FindComponentRecursively(extension, "LocalizedHelp");
                Assert.That(localizedHelp, Is.Not.Null, "LocalizedHelp should be found");

                TestContext.Out.WriteLine($"LocalizedHelp.LocalizedHelpUrls count: {localizedHelp?.LocalizedHelpUrls?.Count ?? 0}");

                Assert.That(localizedHelp!.LocalizedHelpUrls, Is.Not.Null,
                    "LocalizedHelpUrls should be populated");
                Assert.That(localizedHelp.LocalizedHelpUrls.Count, Is.EqualTo(2),
                    "Should have 2 localized help URLs");
                Assert.That(localizedHelp.LocalizedHelpUrls["en_us"], Is.EqualTo("https://example.com/en/help"));
                Assert.That(localizedHelp.LocalizedHelpUrls["fr_fr"], Is.EqualTo("https://example.com/fr/help"));
            }
        }

        [Test]
        public void TestNoHelpReturnsNull()
        {
            Assert.That(_installedExtensions, Is.Not.Null);

            foreach (var extension in _installedExtensions!)
            {
                var noHelp = FindComponentRecursively(extension, "NoHelp");
                Assert.That(noHelp, Is.Not.Null, "NoHelp should be found");

                TestContext.Out.WriteLine($"NoHelp.HelpUrl: {noHelp?.HelpUrl ?? "null"}");
                TestContext.Out.WriteLine($"NoHelp.HelpFile: {noHelp?.HelpFile ?? "null"}");
                TestContext.Out.WriteLine($"NoHelp.GetLocalizedHelpUrl(): {noHelp?.GetLocalizedHelpUrl() ?? "null"}");

                Assert.That(noHelp!.HelpUrl, Is.Null,
                    "HelpUrl should be null");
                Assert.That(noHelp.HelpFile, Is.Null.Or.Empty,
                    "HelpFile should be null/empty (no help file in directory)");
                Assert.That(noHelp.GetLocalizedHelpUrl(), Is.Null,
                    "GetLocalizedHelpUrl should return null when no help is configured");
            }
        }

        [Test]
        public void TestHelpUrlPrecedenceOverHelpFile()
        {
            Assert.That(_installedExtensions, Is.Not.Null);

            foreach (var extension in _installedExtensions!)
            {
                var precedenceTest = FindComponentRecursively(extension, "PrecedenceTest");
                Assert.That(precedenceTest, Is.Not.Null, "PrecedenceTest should be found");

                var helpUrl = precedenceTest!.GetLocalizedHelpUrl();
                TestContext.Out.WriteLine($"PrecedenceTest.GetLocalizedHelpUrl(): {helpUrl ?? "null"}");

                Assert.That(helpUrl, Is.EqualTo("https://explicit-url.example.com"),
                    "GetLocalizedHelpUrl should return HelpUrl (not HelpFile) when HelpUrl is set");
            }
        }

        [Test]
        public void TestHelpFileHasProperty()
        {
            Assert.That(_installedExtensions, Is.Not.Null);

            foreach (var extension in _installedExtensions!)
            {
                var fileBasedHelp = FindComponentRecursively(extension, "FileBasedHelp");
                Assert.That(fileBasedHelp, Is.Not.Null);

                Assert.That(fileBasedHelp!.HasHelpFile, Is.True,
                    "HasHelpFile should be true when HelpFile is set");

                var noHelp = FindComponentRecursively(extension, "NoHelp");
                Assert.That(noHelp, Is.Not.Null);

                Assert.That(noHelp!.HasHelpFile, Is.False,
                    "HasHelpFile should be false when HelpFile is not set");
            }
        }
    }
}
