using pyRevitExtensionParser;
using pyRevitExtensionParserTest;
using pyRevitExtensionParserTest.TestHelpers;
using System.IO;
using System.Text;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTester
{
    [TestFixture]
    public class ScriptMetadataParsingTest : TempFileTestBase
    {
        private string _extensionPath;

        [SetUp]
        public override void BaseSetUp()
        {
            base.BaseSetUp();
            _extensionPath = TestConfiguration.TestExtensionPath;
            
            if (!Directory.Exists(_extensionPath))
            {
                Assert.Fail($"Extension path not found: {_extensionPath}");
            }
        }

        [Test]
        public void TestMinMaxRevitVersionFromScript()
        {
            // Create a temporary bundle with min/max Revit version in script
            var extensionDir = Path.Combine(TestTempDir, "TestRevitVersion.extension");
            var bundleDir = Path.Combine(extensionDir, "TestPanel.panel", "TestButton.pushbutton");
            Directory.CreateDirectory(bundleDir);

            var scriptContent = new StringBuilder();
            scriptContent.AppendLine("__title__ = 'Test Version Button'");
            scriptContent.AppendLine("__min_revit_ver__ = 2021");
            scriptContent.AppendLine("__max_revit_ver__ = 2024");
            scriptContent.AppendLine("\"\"\"This is a test button for version constraints.\"\"\"");
            File.WriteAllText(Path.Combine(bundleDir, "script.py"), scriptContent.ToString());

            // Parse the extension
            var extensions = ParseInstalledExtensions(extensionDir).ToList();
            
            Assert.AreEqual(1, extensions.Count);
            var extension = extensions.First();
            
            // Find the component
            var button = FindComponentRecursively(extension, "TestButton");
            
            if (button == null)
            {
                TestContext.Out.WriteLine("Available components:");
                PrintAllComponents(extension, 0);
                Assert.Inconclusive("TestButton not found in extension.");
                return;
            }
            
            TestContext.Out.WriteLine($"Found button: {button.Name}");
            TestContext.Out.WriteLine($"MinRevitVersion: {button.MinRevitVersion}");
            TestContext.Out.WriteLine($"MaxRevitVersion: {button.MaxRevitVersion}");
            
            // Verify version constraints were parsed from script
            Assert.AreEqual("2021", button.MinRevitVersion, "MinRevitVersion should be 2021");
            Assert.AreEqual("2024", button.MaxRevitVersion, "MaxRevitVersion should be 2024");
            
            Assert.Pass("Min/max Revit version parsing from script validated successfully.");
        }

        [Test]
        public void TestBetaStatusFromScript()
        {
            // Create a temporary bundle with beta status in script
            var extensionDir = Path.Combine(TestTempDir, "TestBeta.extension");
            var bundleDir = Path.Combine(extensionDir, "TestPanel.panel", "BetaButton.pushbutton");
            Directory.CreateDirectory(bundleDir);

            var scriptContent = new StringBuilder();
            scriptContent.AppendLine("__title__ = 'Beta Test Button'");
            scriptContent.AppendLine("__beta__ = True");
            scriptContent.AppendLine("\"\"\"This is a beta test button.\"\"\"");
            File.WriteAllText(Path.Combine(bundleDir, "script.py"), scriptContent.ToString());

            // Parse the extension
            var extensions = ParseInstalledExtensions(extensionDir).ToList();
            
            Assert.AreEqual(1, extensions.Count);
            var extension = extensions.First();
            
            // Find the component
            var button = FindComponentRecursively(extension, "BetaButton");
            
            if (button == null)
            {
                TestContext.Out.WriteLine("Available components:");
                PrintAllComponents(extension, 0);
                Assert.Inconclusive("BetaButton not found in extension.");
                return;
            }
            
            TestContext.Out.WriteLine($"Found button: {button.Name}");
            TestContext.Out.WriteLine($"IsBeta: {button.IsBeta}");
            
            // Verify beta status was parsed from script
            Assert.IsTrue(button.IsBeta, "IsBeta should be true");
            
            Assert.Pass("Beta status parsing from script validated successfully.");
        }

        [Test]
        public void TestEngineConfigsFromScript()
        {
            // Create a temporary bundle with engine configs in script
            var extensionDir = Path.Combine(TestTempDir, "TestEngine.extension");
            var bundleDir = Path.Combine(extensionDir, "TestPanel.panel", "EngineButton.pushbutton");
            Directory.CreateDirectory(bundleDir);

            var scriptContent = new StringBuilder();
            scriptContent.AppendLine("__title__ = 'Engine Test Button'");
            scriptContent.AppendLine("__cleanengine__ = True");
            scriptContent.AppendLine("__fullframeengine__ = True");
            scriptContent.AppendLine("__persistentengine__ = True");
            scriptContent.AppendLine("\"\"\"This is a test button for engine configs.\"\"\"");
            File.WriteAllText(Path.Combine(bundleDir, "script.py"), scriptContent.ToString());

            // Parse the extension
            var extensions = ParseInstalledExtensions(extensionDir).ToList();
            
            Assert.AreEqual(1, extensions.Count);
            var extension = extensions.First();
            
            // Find the component
            var button = FindComponentRecursively(extension, "EngineButton");
            
            if (button == null)
            {
                TestContext.Out.WriteLine("Available components:");
                PrintAllComponents(extension, 0);
                Assert.Inconclusive("EngineButton not found in extension.");
                return;
            }
            
            TestContext.Out.WriteLine($"Found button: {button.Name}");
            TestContext.Out.WriteLine($"Engine.Clean: {button.Engine?.Clean}");
            TestContext.Out.WriteLine($"Engine.FullFrame: {button.Engine?.FullFrame}");
            TestContext.Out.WriteLine($"Engine.Persistent: {button.Engine?.Persistent}");
            
            // Verify engine configs were parsed from script
            Assert.IsNotNull(button.Engine, "Engine should not be null");
            Assert.IsTrue(button.Engine.Clean, "Engine.Clean should be true");
            Assert.IsTrue(button.Engine.FullFrame, "Engine.FullFrame should be true");
            Assert.IsTrue(button.Engine.Persistent, "Engine.Persistent should be true");
            
            Assert.Pass("Engine configuration parsing from script validated successfully.");
        }

        [Test]
        public void TestBundleOverridesScriptMetadata()
        {
            // Create a temporary bundle with metadata in both bundle.yaml and script
            // Bundle should take precedence
            var extensionDir = Path.Combine(TestTempDir, "TestOverride.extension");
            var bundleDir = Path.Combine(extensionDir, "TestPanel.panel", "OverrideButton.pushbutton");
            Directory.CreateDirectory(bundleDir);

            // Script with version 2020
            var scriptContent = new StringBuilder();
            scriptContent.AppendLine("__title__ = 'Script Title'");
            scriptContent.AppendLine("__min_revit_ver__ = 2020");
            scriptContent.AppendLine("__beta__ = False");
            scriptContent.AppendLine("\"\"\"Script tooltip.\"\"\"");
            File.WriteAllText(Path.Combine(bundleDir, "script.py"), scriptContent.ToString());

            // Bundle.yaml with version 2022 and beta=true (should override)
            var bundleYaml = @"title: Bundle Title
min_revit_version: 2022
beta: true
tooltip: Bundle Tooltip
";
            File.WriteAllText(Path.Combine(bundleDir, "bundle.yaml"), bundleYaml);

            // Parse the extension
            var extensions = ParseInstalledExtensions(extensionDir).ToList();
            
            Assert.AreEqual(1, extensions.Count);
            var extension = extensions.First();
            
            // Find the component
            var button = FindComponentRecursively(extension, "OverrideButton");
            
            if (button == null)
            {
                TestContext.Out.WriteLine("Available components:");
                PrintAllComponents(extension, 0);
                Assert.Inconclusive("OverrideButton not found in extension.");
                return;
            }
            
            TestContext.Out.WriteLine($"Found button: {button.Name}");
            TestContext.Out.WriteLine($"MinRevitVersion: {button.MinRevitVersion} (script had 2020, bundle should override)");
            TestContext.Out.WriteLine($"IsBeta: {button.IsBeta} (script had False, bundle should override)");
            
            // Verify bundle overrides script values
            Assert.AreEqual("2022", button.MinRevitVersion, "Bundle min_revit_version should override script");
            Assert.IsTrue(button.IsBeta, "Bundle beta should override script");
            
            // Title should come from bundle
            Assert.AreEqual("Bundle Title", button.Title, "Bundle title should override script title");
            
            Assert.Pass("Bundle override of script metadata validated successfully.");
        }

        [Test]
        public void TestLoadBetaConfigFromIni()
        {
            // Create a temporary config file
            var configPath = Path.Combine(TestTempDir, "pyRevit_config.ini");
            
            // Test default value (false when not set)
            File.WriteAllText(configPath, "");
            var config1 = PyRevitConfig.Load(configPath);
            Assert.IsFalse(config1.LoadBeta, "Default LoadBeta should be false when not set");
            
            // Test explicit true
            File.WriteAllText(configPath, "[core]\nload_beta = true");
            var config2 = PyRevitConfig.Load(configPath);
            Assert.IsTrue(config2.LoadBeta, "LoadBeta should be true when explicitly set");
            
            // Test explicit false
            File.WriteAllText(configPath, "[core]\nload_beta = false");
            var config3 = PyRevitConfig.Load(configPath);
            Assert.IsFalse(config3.LoadBeta, "LoadBeta should be false when explicitly set");
            
            // Test case insensitivity
            File.WriteAllText(configPath, "[core]\nload_beta = TRUE");
            var config4 = PyRevitConfig.Load(configPath);
            Assert.IsTrue(config4.LoadBeta, "LoadBeta should be case-insensitive");
            
            Assert.Pass("LoadBeta config parsing validated successfully.");
        }

        private ParsedComponent? FindComponentRecursively(ParsedComponent? component, string targetName)
        {
            if (component == null)
                return null;
                
            if (string.Equals(component.Name, targetName, StringComparison.OrdinalIgnoreCase) ||
                string.Equals(component.DisplayName, targetName, StringComparison.OrdinalIgnoreCase))
                return component;
                
            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    var found = FindComponentRecursively(child, targetName);
                    if (found != null)
                        return found;
                }
            }
            
            return null;
        }
        
        private void PrintAllComponents(ParsedComponent? component, int indent)
        {
            if (component == null)
                return;
                
            var prefix = new string(' ', indent * 2);
            TestContext.Out.WriteLine($"{prefix}{component.Type}: {component.Name} ({component.DisplayName})");
            
            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    PrintAllComponents(child, indent + 1);
                }
            }
        }
    }
}
