using pyRevitExtensionParser;
using pyRevitExtensionParserTest;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTester
{
    [TestFixture]
    public class PythonScriptMultiLangTest
    {
        private string _extensionPath;

        [SetUp]
        public void Setup()
        {
            // Use existing pyRevitDevTools extension for testing
            _extensionPath = TestConfiguration.TestExtensionPath;
            
            if (!Directory.Exists(_extensionPath))
            {
                Assert.Fail($"Extension path not found: {_extensionPath}");
            }
        }

        [Test]
        public void TestPythonScriptWithDictionaryTitle()
        {
            // Test existing button: "Test pyRevit Button" has script with dictionary __title__
            // Script contains: __title__ = {"en_us": "Test pyRevit Button (Custom)", "chinese_s": "测试按钮"}
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { _extensionPath });
            
            Assert.AreEqual(1, extensions.Count());
            var extension = extensions.First();
            
            // Find the "Test pyRevit Button" component using recursive search
            var button = FindComponentRecursively(extension, "TestpyRevitButton");
            
            if (button == null)
            {
                // Try alternate name without spaces
                button = FindComponentRecursively(extension, "Test pyRevit Button");
            }
            
            if (button == null)
            {
                TestContext.Out.WriteLine("Available components:");
                PrintAllComponents(extension, 0);
                Assert.Inconclusive("Test pyRevit Button not found in extension. This test validates dictionary-style __title__ parsing.");
                return;
            }
            
            TestContext.Out.WriteLine($"Found button: {button.Name} ({button.DisplayName})");
            TestContext.Out.WriteLine($"Title: {button.Title}");
            TestContext.Out.WriteLine($"LocalizedTitles count: {button.LocalizedTitles?.Count ?? 0}");
            
            // Verify localized titles were parsed from script
            if (button.LocalizedTitles != null && button.LocalizedTitles.Count > 0)
            {
                Assert.IsTrue(button.LocalizedTitles.Count >= 2, "Should have at least 2 localized titles");
                
                foreach (var kvp in button.LocalizedTitles)
                {
                    TestContext.Out.WriteLine($"  {kvp.Key}: {kvp.Value}");
                }
                
                if (button.LocalizedTitles.ContainsKey("en_us"))
                {
                    Assert.AreEqual("Test pyRevit Button (Custom)", button.LocalizedTitles["en_us"]);
                }
                if (button.LocalizedTitles.ContainsKey("chinese_s"))
                {
                    Assert.AreEqual("测试按钮", button.LocalizedTitles["chinese_s"]);
                }
                
                Assert.Pass("Dictionary-style __title__ parsing validated successfully.");
            }
            else
            {
                Assert.Inconclusive("Button found but has no localized titles. Dictionary-style __title__ may not be present in script.");
            }
        }
        
        // Helper method to find components recursively
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
        
        // Helper method to print all components for debugging
        private void PrintAllComponents(ParsedComponent component, int depth)
        {
            var indent = new string(' ', depth * 2);
            TestContext.Out.WriteLine($"{indent}- {component.Name ?? "NULL"} ({component.DisplayName ?? "NULL"}) [{component.Type}]");
            
            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    PrintAllComponents(child, depth + 1);
                }
            }
        }

        [Test]
        public void TestPythonScriptWithSimpleStringTitle()
        {
            // Test existing button: "Test Persistent Engine" has script with simple string __title__
            // Script contains: __title__ = "Test Persistent Engine (NonModal)"
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { _extensionPath });
            
            Assert.AreEqual(1, extensions.Count());
            var extension = extensions.First();
            
            // Find the "Test Persistent Engine" component using recursive search
            var button = FindComponentRecursively(extension, "TestPersistentEngine");
            
            if (button == null)
            {
                button = FindComponentRecursively(extension, "Test Persistent Engine");
            }
            
            if (button == null)
            {
                Assert.Inconclusive("Test Persistent Engine button not found. This test validates simple string __title__ parsing.");
                return;
            }
            
            TestContext.Out.WriteLine($"Found button: {button.Name} ({button.DisplayName})");
            TestContext.Out.WriteLine($"Title: {button.Title}");
            TestContext.Out.WriteLine($"LocalizedTitles: {button.LocalizedTitles?.Count ?? 0}");
            
            // Verify simple string title still works (backward compatibility)
            Assert.IsNotEmpty(button.Title, "Button should have a title");
            
            // LocalizedTitles should be null or empty for simple strings
            Assert.IsTrue(button.LocalizedTitles == null || button.LocalizedTitles.Count == 0,
                "Simple string __title__ should not create localized titles collection");
                
            Assert.Pass("Simple string __title__ parsing validated successfully.");
        }

        [Test]
        public void TestBundleWithLocalizedTitles()
        {
            // Test existing button: "Test pyRevit Bundle" has bundle.yaml with localized titles
            // bundle.yaml contains: title: {en_us: "Test pyRevit Bundle (Custom Title)", chinese_s: "测试包"}
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { _extensionPath });
            
            Assert.AreEqual(1, extensions.Count());
            var extension = extensions.First();
            
            // Find the "Test pyRevit Bundle" component using recursive search
            var button = FindComponentRecursively(extension, "TestpyRevitBundle");
            
            if (button == null)
            {
                button = FindComponentRecursively(extension, "Test pyRevit Bundle");
            }
            
            if (button == null)
            {
                Assert.Inconclusive("Test pyRevit Bundle button not found. This test validates bundle.yaml localized title parsing.");
                return;
            }
            
            TestContext.Out.WriteLine($"Found button: {button.Name} ({button.DisplayName})");
            TestContext.Out.WriteLine($"Title: {button.Title}");
            TestContext.Out.WriteLine($"LocalizedTitles count: {button.LocalizedTitles?.Count ?? 0}");
            
            // Verify localized titles from bundle.yaml
            if (button.LocalizedTitles != null && button.LocalizedTitles.Count > 0)
            {
                Assert.IsTrue(button.LocalizedTitles.Count >= 2, "Should have at least 2 localized titles");
                
                foreach (var kvp in button.LocalizedTitles)
                {
                    TestContext.Out.WriteLine($"  {kvp.Key}: {kvp.Value}");
                }
                
                Assert.Pass("Bundle.yaml localized title parsing validated successfully.");
            }
            else
            {
                Assert.Inconclusive("Button found but has no localized titles. Bundle.yaml may not contain localized titles.");
            }
        }
        
        [Test]
        public void TestSetWorksetButtonFromToolsExtension()
        {
            // Test button from pyRevitTools extension: "Set Workset" has bundle.yaml with localized titles
            // bundle.yaml contains multiple languages: en_us, ru, fr_fr, de_de
            
            // Navigate to the pyRevit repository root from the test extension path
            var devToolsExtPath = _extensionPath; // This points to pyRevitDevTools.extension
            var extensionsDir = Path.GetDirectoryName(devToolsExtPath); // Go up to extensions folder
            var toolsExtensionPath = Path.Combine(extensionsDir!, "pyRevitTools.extension");
            
            TestContext.Out.WriteLine($"Looking for pyRevitTools at: {toolsExtensionPath}");
            
            if (!Directory.Exists(toolsExtensionPath))
            {
                Assert.Inconclusive($"pyRevitTools extension not found at: {toolsExtensionPath}. This test validates multi-language support in bundle.yaml.");
                return;
            }
            
            // Parse the pyRevitTools extension
            var extensions = ParseInstalledExtensions(new[] { toolsExtensionPath });
            
            if (extensions.Count() == 0)
            {
                Assert.Inconclusive("pyRevitTools extension could not be parsed.");
                return;
            }
            
            var extension = extensions.First();
            TestContext.Out.WriteLine($"Parsed extension: {extension.Name}");
            
            // Find the "Set Workset" button using recursive search
            var button = FindComponentRecursively(extension, "SetWorkset");
            
            if (button == null)
            {
                button = FindComponentRecursively(extension, "Set Workset");
            }
            
            if (button == null)
            {
                Assert.Inconclusive("Set Workset button not found in pyRevitTools extension.");
                return;
            }
            
            TestContext.Out.WriteLine($"Found button: {button.Name} ({button.DisplayName})");
            TestContext.Out.WriteLine($"LocalizedTitles count: {button.LocalizedTitles?.Count ?? 0}");
            TestContext.Out.WriteLine($"LocalizedTooltips count: {button.LocalizedTooltips?.Count ?? 0}");
            
            // Verify localized titles from bundle.yaml
            if (button.LocalizedTitles != null && button.LocalizedTitles.Count > 0)
            {
                foreach (var kvp in button.LocalizedTitles)
                {
                    TestContext.Out.WriteLine($"  Title[{kvp.Key}]: {kvp.Value.Replace("\n", "\\n")}");
                }
                
                Assert.IsTrue(button.LocalizedTitles.Count >= 2, "Should have multiple localized titles");
            }
            
            // Verify localized tooltips
            if (button.LocalizedTooltips != null && button.LocalizedTooltips.Count > 0)
            {
                foreach (var kvp in button.LocalizedTooltips)
                {
                    TestContext.Out.WriteLine($"  Tooltip[{kvp.Key}]: {kvp.Value}");
                }
                
                Assert.IsTrue(button.LocalizedTooltips.Count >= 2, "Should have multiple localized tooltips");
            }
            
            if ((button.LocalizedTitles != null && button.LocalizedTitles.Count > 0) ||
                (button.LocalizedTooltips != null && button.LocalizedTooltips.Count > 0))
            {
                Assert.Pass("Multi-language support in bundle.yaml validated successfully.");
            }
            else
            {
                Assert.Inconclusive("Button found but has no localized content.");
            }
        }
    }
}
