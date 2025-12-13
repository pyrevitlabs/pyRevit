using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class BundleTooltipFixTest : TempFileTestBase
    {
        [Test]
        public void TestTooltipParsingFix()
        {
            TestContext.Out.WriteLine("=== Testing Tooltip Parsing Fix ===");
            
            // Create a temporary test directory structure using unique temp directory
            var testExtensionDir = Path.Combine(TestTempDir, "TestExt.extension");
            var testTabDir = Path.Combine(testExtensionDir, "TestTab.tab");
            var testPanelDir = Path.Combine(testTabDir, "TestPanel.panel");
            var testButtonDir = Path.Combine(testPanelDir, "TestButton.panelbutton");
            
            // Create directory structure
            Directory.CreateDirectory(testButtonDir);
            
            // Create a test script
            var scriptPath = Path.Combine(testButtonDir, "script.py");
            File.WriteAllText(scriptPath, "# Test script");
            
            // Create bundle.yaml with plural "tooltips"
            var bundlePath = Path.Combine(testButtonDir, "bundle.yaml");
            var bundleContent = @"title:
  en_us: Test Panel Button
tooltips:
  en_us: >-
    This is a test tooltip for the panel button.
    It should be parsed correctly from the bundle file.
author: Test Framework
";
            File.WriteAllText(bundlePath, bundleContent);
            
            TestContext.Out.WriteLine($"Created test extension at: {testExtensionDir}");
            TestContext.Out.WriteLine($"Bundle content:\n{bundleContent}");
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { testExtensionDir });
            var extension = extensions.FirstOrDefault();
            
            Assert.IsNotNull(extension, "Should parse test extension");
            TestContext.Out.WriteLine($"Extension parsed: {extension.Name}");
            
            // Find the test button
            var testButton = FindComponentRecursively(extension, "TestButton");
            Assert.IsNotNull(testButton, "Should find test button");
            
            TestContext.Out.WriteLine($"Found button: {testButton.DisplayName}");
            TestContext.Out.WriteLine($"Button type: {testButton.Type}");
            TestContext.Out.WriteLine($"Bundle file: {testButton.BundleFile}");
            TestContext.Out.WriteLine($"Title: '{testButton.Title}'");
            TestContext.Out.WriteLine($"Tooltip: '{testButton.Tooltip}'");
            TestContext.Out.WriteLine($"Author: '{testButton.Author}'");
            
            // Verify parsing results
            Assert.AreEqual(CommandComponentType.PanelButton, testButton.Type);
            Assert.AreEqual("Test Panel Button", testButton.Title);
            Assert.AreEqual("Test Framework", testButton.Author);
            
            // The key test - tooltip should be parsed correctly
            Assert.IsNotNull(testButton.Tooltip, "Tooltip should not be null");
            Assert.IsNotEmpty(testButton.Tooltip, "Tooltip should not be empty");
            Assert.IsTrue(testButton.Tooltip.Contains("test tooltip"), 
                         $"Tooltip should contain expected content, but was: '{testButton.Tooltip}'");
            Assert.IsTrue(testButton.Tooltip.Contains("panel button"), 
                         $"Tooltip should contain 'panel button', but was: '{testButton.Tooltip}'");
            
            TestContext.Out.WriteLine("? Tooltip parsing fix verified successfully!");
            Assert.Pass("Tooltip parsing fix test completed successfully");
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
    }
}