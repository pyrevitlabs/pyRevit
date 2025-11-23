using NUnit.Framework;
using pyRevitExtensionParser;
using System.Collections.Generic;
using System.IO;
using System.Linq;
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
            var currentDir = Directory.GetCurrentDirectory();
            var repoRoot = Path.GetFullPath(Path.Combine(currentDir, "..", "..", "..", ".."));
            _extensionPath = Path.Combine(repoRoot, "extensions", "pyRevitDevTools.extension");
            
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
            
            // Find the "Test pyRevit Button" component in Bundle Tests pulldown
            var button = extension.Children
                .SelectMany(t => t.Children) // tabs
                .SelectMany(p => p.Children) // panels
                .SelectMany(pd => pd.Children) // pulldowns
                .FirstOrDefault(b => b.Name == "Test pyRevit Button");
            
            Assert.IsNotNull(button, "Test pyRevit Button not found");
            
            // Verify localized titles were parsed from script
            Assert.IsNotNull(button.LocalizedTitles);
            Assert.IsTrue(button.LocalizedTitles.Count >= 2);
            Assert.AreEqual("Test pyRevit Button (Custom)", button.LocalizedTitles["en_us"]);
            Assert.AreEqual("测试按钮", button.LocalizedTitles["chinese_s"]);
            
            // Verify default title is set (should use en_us as default)
            Assert.AreEqual("Test pyRevit Button (Custom)", button.Title);
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
            
            // Find the "Test Persistent Engine" component in Engine Tests pulldown
            var button = extension.Children
                .SelectMany(t => t.Children) // tabs
                .SelectMany(p => p.Children) // panels
                .SelectMany(pd => pd.Children) // pulldowns
                .FirstOrDefault(b => b.Name == "Test Persistent Engine");
            
            Assert.IsNotNull(button, "Test Persistent Engine button not found");
            
            // Verify simple string title still works (backward compatibility)
            Assert.AreEqual("Test Persistent Engine (NonModal)", button.Title);
            
            // LocalizedTitles should be null or empty for simple strings
            Assert.IsTrue(button.LocalizedTitles == null || button.LocalizedTitles.Count == 0);
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
            
            // Find the "Test pyRevit Bundle" component in Bundle Tests pulldown
            var button = extension.Children
                .SelectMany(t => t.Children) // tabs
                .SelectMany(p => p.Children) // panels
                .SelectMany(pd => pd.Children) // pulldowns
                .FirstOrDefault(b => b.Name == "Test pyRevit Bundle");
            
            Assert.IsNotNull(button, "Test pyRevit Bundle button not found");
            
            // Verify localized titles from bundle.yaml
            Assert.IsNotNull(button.LocalizedTitles);
            Assert.IsTrue(button.LocalizedTitles.Count >= 2);
            Assert.AreEqual("Test pyRevit Bundle (Custom Title)", button.LocalizedTitles["en_us"]);
            Assert.AreEqual("测试包", button.LocalizedTitles["chinese_s"]);
            
            // Default title should be from bundle
            Assert.AreEqual("Test pyRevit Bundle (Custom Title)", button.Title);
        }
        
        [Test]
        public void TestSetWorksetButtonFromToolsExtension()
        {
            // Test button from pyRevitTools extension: "Set Workset" has bundle.yaml with localized titles
            // bundle.yaml contains multiple languages: en_us, ru, fr_fr, de_de
            
            var currentDir = Directory.GetCurrentDirectory();
            var repoRoot = Path.GetFullPath(Path.Combine(currentDir, "..", "..", "..", ".."));
            var toolsExtensionPath = Path.Combine(repoRoot, "extensions", "pyRevitTools.extension");
            
            if (!Directory.Exists(toolsExtensionPath))
            {
                Assert.Inconclusive($"pyRevitTools extension not found at: {toolsExtensionPath}");
            }
            
            // Parse the pyRevitTools extension
            var extensions = ParseInstalledExtensions(new[] { toolsExtensionPath });
            
            Assert.AreEqual(1, extensions.Count());
            var extension = extensions.First();
            
            // Find the "Set Workset" button in Selection panel
            var button = extension.Children
                .SelectMany(t => t.Children) // tabs
                .SelectMany(p => p.Children) // panels
                .FirstOrDefault(b => b.Name == "Set Workset");
            
            Assert.IsNotNull(button, "Set Workset button not found");
            
            // Verify localized titles from bundle.yaml
            Assert.IsNotNull(button.LocalizedTitles);
            Assert.IsTrue(button.LocalizedTitles.Count >= 4);
            Assert.AreEqual("Set\n\nWorkset", button.LocalizedTitles["en_us"]);
            Assert.AreEqual("Задать\n\nраб. набор", button.LocalizedTitles["ru"]);
            Assert.AreEqual("Active\n\nSous-Projet", button.LocalizedTitles["fr_fr"]);
            Assert.AreEqual("Set\n\nWorkset", button.LocalizedTitles["de_de"]);
            
            // Verify localized tooltips
            Assert.IsNotNull(button.LocalizedTooltips);
            Assert.IsTrue(button.LocalizedTooltips.Count >= 4);
            Assert.AreEqual("Sets the active workset from the selection", button.LocalizedTooltips["en_us"]);
            Assert.AreEqual("Устанавливает текущий рабочий набор из выделения.", button.LocalizedTooltips["ru"]);
        }
    }
}
