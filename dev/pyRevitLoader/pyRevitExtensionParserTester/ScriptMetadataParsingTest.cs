using pyRevitExtensionParser;
using pyRevitExtensionParserTest;
using pyRevitExtensionParserTest.TestHelpers;
using pyRevitAssemblyBuilder.AssemblyMaker;
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
        public void TestLoggingLevelConfigFromIni()
        {
            var configPath = Path.Combine(TestTempDir, "pyRevit_config_logging.ini");

            // Default: Quiet (0) when nothing is set
            File.WriteAllText(configPath, "");
            Assert.AreEqual(0, PyRevitConfig.Load(configPath).LoggingLevel, "Default should be 0 (Quiet)");

            // Verbose only → 1
            File.WriteAllText(configPath, "[core]\nverbose = true\ndebug = false");
            Assert.AreEqual(1, PyRevitConfig.Load(configPath).LoggingLevel, "verbose=true should give 1");

            // Debug → 2 (takes priority)
            File.WriteAllText(configPath, "[core]\nverbose = true\ndebug = true");
            Assert.AreEqual(2, PyRevitConfig.Load(configPath).LoggingLevel, "debug=true should give 2");

            // Explicit Quiet
            File.WriteAllText(configPath, "[core]\nverbose = false\ndebug = false");
            Assert.AreEqual(0, PyRevitConfig.Load(configPath).LoggingLevel, "Both false should give 0");

            Assert.Pass("LoggingLevel config parsing validated successfully.");
        }

        [Test]
        public void TestTelemetryConfigFromIni()
        {
            var configPath = Path.Combine(TestTempDir, "pyRevit_config_telem.ini");

            // Defaults: all false / empty when section is absent
            File.WriteAllText(configPath, "");
            var cfg0 = PyRevitConfig.Load(configPath);
            Assert.IsFalse(cfg0.TelemetryState, "Default TelemetryState should be false");
            Assert.IsTrue(cfg0.TelemetryUTCTimeStamps, "Default TelemetryUTCTimeStamps should be true");
            Assert.AreEqual(string.Empty, cfg0.TelemetryFilePath, "Default TelemetryFilePath should be empty");
            Assert.AreEqual(string.Empty, cfg0.TelemetryServerUrl, "Default TelemetryServerUrl should be empty");
            Assert.IsFalse(cfg0.TelemetryIncludeHooks, "Default TelemetryIncludeHooks should be false");
            Assert.IsFalse(cfg0.AppTelemetryState, "Default AppTelemetryState should be false");
            Assert.AreEqual(string.Empty, cfg0.AppTelemetryServerUrl, "Default AppTelemetryServerUrl should be empty");
            Assert.AreEqual(string.Empty, cfg0.AppTelemetryEventFlags, "Default AppTelemetryEventFlags should be empty");

            // Set values and verify read-back
            var iniContent = string.Join("\n", new[] {
                "[telemetry]",
                "active = true",
                "utc_timestamps = true",
                "telemetry_file_dir = C:\\logs",
                "telemetry_server_url = https://telem.example.com",
                "include_hooks = true",
                "active_app = true",
                "apptelemetry_server_url = https://apptelm.example.com",
                "apptelemetry_event_flags = 255",
            });
            File.WriteAllText(configPath, iniContent);
            var cfg1 = PyRevitConfig.Load(configPath);
            Assert.IsTrue(cfg1.TelemetryState);
            Assert.IsTrue(cfg1.TelemetryUTCTimeStamps);
            Assert.AreEqual("C:\\logs", cfg1.TelemetryFilePath);
            Assert.AreEqual("https://telem.example.com", cfg1.TelemetryServerUrl);
            Assert.IsTrue(cfg1.TelemetryIncludeHooks);
            Assert.IsTrue(cfg1.AppTelemetryState);
            Assert.AreEqual("https://apptelm.example.com", cfg1.AppTelemetryServerUrl);
            Assert.AreEqual("255", cfg1.AppTelemetryEventFlags);

            // Write-then-read round-trip
            var configPath2 = Path.Combine(TestTempDir, "pyRevit_config_telem_rw.ini");
            File.WriteAllText(configPath2, "");
            var cfgRw = PyRevitConfig.Load(configPath2);
            cfgRw.TelemetryState = true;
            cfgRw.TelemetryServerUrl = "https://rw.example.com";
            Assert.IsTrue(PyRevitConfig.Load(configPath2).TelemetryState);
            Assert.AreEqual("https://rw.example.com", PyRevitConfig.Load(configPath2).TelemetryServerUrl);

            Assert.Pass("Telemetry config parsing validated successfully.");
        }

        [Test]
        public void TestFileLoggingAndAutoUpdateConfigFromIni()
        {
            var configPath = Path.Combine(TestTempDir, "pyRevit_config_misc.ini");

            // Defaults
            File.WriteAllText(configPath, "");
            var cfg0 = PyRevitConfig.Load(configPath);
            Assert.IsFalse(cfg0.FileLogging, "Default FileLogging should be false");
            Assert.IsFalse(cfg0.AutoUpdate, "Default AutoUpdate should be false");
            Assert.AreEqual(string.Empty, cfg0.OutputStyleSheet, "Default OutputStyleSheet should be empty");

            // Set values
            File.WriteAllText(configPath, "[core]\nfilelogging = true\nautoupdate = true\noutputstylesheet = C:\\style.css");
            var cfg1 = PyRevitConfig.Load(configPath);
            Assert.IsTrue(cfg1.FileLogging);
            Assert.IsTrue(cfg1.AutoUpdate);
            Assert.AreEqual("C:\\style.css", cfg1.OutputStyleSheet);

            // Write-then-read round-trip for OutputStyleSheet
            var configPath2 = Path.Combine(TestTempDir, "pyRevit_config_misc_rw.ini");
            File.WriteAllText(configPath2, "");
            var cfgRw = PyRevitConfig.Load(configPath2);
            cfgRw.OutputStyleSheet = "C:\\custom.css";
            Assert.AreEqual("C:\\custom.css", PyRevitConfig.Load(configPath2).OutputStyleSheet);

            Assert.Pass("FileLogging / AutoUpdate / OutputStyleSheet config parsing validated successfully.");
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
            
            // Canonical key matches pyRevitLabs / Python user_config (loadbeta, no underscore)
            File.WriteAllText(configPath, "[core]\nloadbeta = true");
            var config2 = PyRevitConfig.Load(configPath);
            Assert.IsTrue(config2.LoadBeta, "LoadBeta should be true when loadbeta is set");
            
            File.WriteAllText(configPath, "[core]\nloadbeta = false");
            var config3 = PyRevitConfig.Load(configPath);
            Assert.IsFalse(config3.LoadBeta, "LoadBeta should be false when loadbeta is false");
            
            File.WriteAllText(configPath, "[core]\nloadbeta = TRUE");
            var config4 = PyRevitConfig.Load(configPath);
            Assert.IsTrue(config4.LoadBeta, "LoadBeta should be case-insensitive for loadbeta");

            // Legacy underscore key (older C# PyRevitConfig writer)
            File.WriteAllText(configPath, "[core]\nload_beta = true");
            var config5 = PyRevitConfig.Load(configPath);
            Assert.IsTrue(config5.LoadBeta, "LoadBeta should read legacy load_beta when loadbeta is absent");

            // Setter writes canonical key and removes legacy duplicate
            File.WriteAllText(configPath, "[core]\nload_beta = true\nloadbeta = false");
            var config6 = PyRevitConfig.Load(configPath);
            Assert.IsFalse(config6.LoadBeta, "Canonical loadbeta should win when both keys exist");
            config6.LoadBeta = true;
            var iniText = File.ReadAllText(configPath);
            StringAssert.DoesNotContain("load_beta", iniText);
            StringAssert.Contains("loadbeta", iniText);
            Assert.IsTrue(PyRevitConfig.Load(configPath).LoadBeta, "After setter, only loadbeta should remain and read as true");

            File.WriteAllText(configPath, "[core]\nloadbeta = 1");
            Assert.IsTrue(PyRevitConfig.Load(configPath).LoadBeta, "LoadBeta should accept numeric 1");
            File.WriteAllText(configPath, "[core]\nloadbeta = \"true\"");
            Assert.IsTrue(PyRevitConfig.Load(configPath).LoadBeta, "LoadBeta should accept quoted true");

            Assert.Pass("LoadBeta config parsing validated successfully.");
        }

        [Test]
        public void TestRocketModeEngineConfigs()
        {
            var testCases = new[]
            {
                new { Name = "RocketMode_Off_CompatibleExt", RocketMode = false, Compatible = true, ExplicitClean = false, ExpectedClean = true },
                new { Name = "RocketMode_On_CompatibleExt", RocketMode = true, Compatible = true, ExplicitClean = false, ExpectedClean = false },
                new { Name = "RocketMode_On_IncompatibleExt", RocketMode = true, Compatible = false, ExplicitClean = false, ExpectedClean = true },
                new { Name = "RocketMode_On_CompatibleExt_ExplicitClean", RocketMode = true, Compatible = true, ExplicitClean = true, ExpectedClean = true },
                new { Name = "RocketMode_Off_IncompatibleExt", RocketMode = false, Compatible = false, ExplicitClean = false, ExpectedClean = true },
            };

            foreach (var tc in testCases)
            {
                var extensionDir = Path.Combine(TestTempDir, $"{tc.Name}.extension");
                var bundleDir = Path.Combine(extensionDir, "TestPanel.panel", "TestButton.pushbutton");
                Directory.CreateDirectory(bundleDir);

                var scriptContent = new StringBuilder();
                scriptContent.AppendLine("__title__ = 'Test Button'");
                if (tc.ExplicitClean)
                {
                    scriptContent.AppendLine("__cleanengine__ = True");
                }
                File.WriteAllText(Path.Combine(bundleDir, "script.py"), scriptContent.ToString());

                if (tc.Compatible)
                {
                    var extensionJson = "{ \"rocket_mode_compatible\": \"True\" }";
                    File.WriteAllText(Path.Combine(extensionDir, "extension.json"), extensionJson);
                }

                var extensions = ParseInstalledExtensions(extensionDir).ToList();
                Assert.AreEqual(1, extensions.Count, $"{tc.Name}: Expected 1 extension");
                var extension = extensions.First();

                Assert.AreEqual(tc.Compatible, extension.RocketModeCompatible, 
                    $"{tc.Name}: RocketModeCompatible should be {tc.Compatible}");

                var button = FindComponentRecursively(extension, "TestButton");
                Assert.IsNotNull(button, $"{tc.Name}: TestButton not found");

                var engineCfgs = pyRevitAssemblyBuilder.AssemblyMaker.CommandGenerationUtilities.BuildEngineConfigs(
                    button, button.ScriptPath, extension, tc.RocketMode);

                TestContext.Out.WriteLine($"{tc.Name}: RocketMode={tc.RocketMode}, Compatible={tc.Compatible}, ExplicitClean={tc.ExplicitClean}");
                TestContext.Out.WriteLine($"  Engine Configs: {engineCfgs}");

                Assert.IsTrue(engineCfgs.Contains($"\"clean\":{tc.ExpectedClean.ToString().ToLower()}"),
                    $"{tc.Name}: Expected clean={tc.ExpectedClean}, got: {engineCfgs}");

                Directory.Delete(extensionDir, true);
            }

            Assert.Pass("Rocket mode engine configs validated successfully.");
        }

        [Test]
        public void TestRocketModeCompatibilityFromExtensionJson()
        {
            var extensionDir = Path.Combine(TestTempDir, "RocketModeCompatibilityTest.extension");
            var bundleDir = Path.Combine(extensionDir, "TestPanel.panel", "TestButton.pushbutton");
            Directory.CreateDirectory(bundleDir);

            File.WriteAllText(Path.Combine(bundleDir, "script.py"), "__title__ = 'Test'");
            File.WriteAllText(Path.Combine(extensionDir, "extension.json"), "{ \"rocket_mode_compatible\": \"True\" }");

            var extensions = ParseInstalledExtensions(extensionDir).ToList();
            Assert.AreEqual(1, extensions.Count);
            var extension = extensions.First();

            Assert.IsTrue(extension.RocketModeCompatible, "Extension should be rocket mode compatible");

            Directory.Delete(extensionDir, true);
        }

        [Test]
        public void TestPyRevitCoreAlwaysRocketModeCompatible()
        {
            var extensionDir = Path.Combine(TestTempDir, "pyRevitCore.extension");
            var bundleDir = Path.Combine(extensionDir, "TestPanel.panel", "TestButton.pushbutton");
            Directory.CreateDirectory(bundleDir);

            File.WriteAllText(Path.Combine(bundleDir, "script.py"), "__title__ = 'Test'");
            // No extension.json - pyRevitCore should still be compatible

            var extensions = ParseInstalledExtensions(extensionDir).ToList();
            Assert.AreEqual(1, extensions.Count);
            var extension = extensions.First();

            Assert.IsTrue(extension.RocketModeCompatible, "pyRevitCore should always be rocket mode compatible");

            Directory.Delete(extensionDir, true);
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
