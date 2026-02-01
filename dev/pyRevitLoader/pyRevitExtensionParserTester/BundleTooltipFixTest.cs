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

        [Test]
        public void TestTooltipWithColonContent()
        {
            TestContext.Out.WriteLine("=== Testing Tooltip with Colon Content (Shift-Click fix) ===");
            
            // Create a temporary test directory structure using unique temp directory
            var testExtensionDir = Path.Combine(TestTempDir, "TestExt2.extension");
            var testTabDir = Path.Combine(testExtensionDir, "TestTab.tab");
            var testPanelDir = Path.Combine(testTabDir, "TestPanel.panel");
            var testButtonDir = Path.Combine(testPanelDir, "Paste State.pushbutton");
            
            // Create directory structure
            Directory.CreateDirectory(testButtonDir);
            
            // Create a test script
            var scriptPath = Path.Combine(testButtonDir, "script.py");
            File.WriteAllText(scriptPath, "# Test script");
            
            // Create bundle.yaml with the exact tooltip structure from the issue
            var bundlePath = Path.Combine(testButtonDir, "bundle.yaml");
            var bundleContent = @"title:
  en_us: Paste State
tooltip:
  en_us: >-
    Applies the copied state to the active view

    This works in conjunction with the Copy State tool

    Shift-Click:

    Show additional options
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
            var testButton = FindComponentRecursively(extension, "PasteState");
            Assert.IsNotNull(testButton, "Should find Paste State button");
            
            TestContext.Out.WriteLine($"Found button: {testButton.DisplayName}");
            TestContext.Out.WriteLine($"Button type: {testButton.Type}");
            TestContext.Out.WriteLine($"Title: '{testButton.Title}'");
            TestContext.Out.WriteLine($"Tooltip: '{testButton.Tooltip}'");
            TestContext.Out.WriteLine($"Author: '{testButton.Author}'");
            
            // Verify parsing results
            Assert.AreEqual(CommandComponentType.PushButton, testButton.Type);
            Assert.AreEqual("Paste State", testButton.Title);
            Assert.AreEqual("Test Framework", testButton.Author);
            
            // The key test - tooltip should contain ALL content including "Shift-Click:" and "Show additional options"
            Assert.IsNotNull(testButton.Tooltip, "Tooltip should not be null");
            Assert.IsNotEmpty(testButton.Tooltip, "Tooltip should not be empty");
            
            // Check that tooltip contains the beginning
            Assert.IsTrue(testButton.Tooltip.Contains("Applies the copied state to the active view"), 
                         $"Tooltip should contain 'Applies the copied state', but was: '{testButton.Tooltip}'");
            
            // Check that tooltip contains "Shift-Click:" (the part that was being cut off)
            Assert.IsTrue(testButton.Tooltip.Contains("Shift-Click:"), 
                         $"Tooltip should contain 'Shift-Click:', but was: '{testButton.Tooltip}'");
            
            // Check that tooltip contains the end (Show additional options)
            Assert.IsTrue(testButton.Tooltip.Contains("Show additional options"), 
                         $"Tooltip should contain 'Show additional options', but was: '{testButton.Tooltip}'");
            
            TestContext.Out.WriteLine("? Tooltip with colon content test verified successfully!");
            Assert.Pass("Tooltip with colon content test completed successfully");
        }

[Test]
        public void TestMultilineAuthorParsing()
        {
            TestContext.Out.WriteLine("=== Testing Multiline Author Parsing ===");

            // Create a temporary test directory structure
            var testExtensionDir = Path.Combine(TestTempDir, "TestExt3.extension");
            var testTabDir = Path.Combine(testExtensionDir, "TestTab.tab");
            var testPanelDir = Path.Combine(testTabDir, "TestPanel.panel");
            var testButtonDir = Path.Combine(testPanelDir, "MultiAuthor.pushbutton");

            Directory.CreateDirectory(testButtonDir);

            var scriptPath = Path.Combine(testButtonDir, "script.py");
            File.WriteAllText(scriptPath, "# Test script");

            // Create bundle.yaml with multiline author (folded style)
            var bundlePath = Path.Combine(testButtonDir, "bundle.yaml");
            var bundleContent = @"title:
  en_us: Multi Author Test
tooltip:
  en_us: Test tooltip
author: >-
  Gui Talarico

  {{author}}

  Alex Melnikov
";
            File.WriteAllText(bundlePath, bundleContent);

            TestContext.Out.WriteLine($"Bundle content:\n{bundleContent}");

            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { testExtensionDir });
            var extension = extensions.FirstOrDefault();

            Assert.IsNotNull(extension, "Should parse test extension");

            var testButton = FindComponentRecursively(extension, "MultiAuthor");
            Assert.IsNotNull(testButton, "Should find MultiAuthor button");

            TestContext.Out.WriteLine($"Found button: {testButton.DisplayName}");
            TestContext.Out.WriteLine($"Author: '{testButton.Author}'");

            // Verify author was parsed correctly as multiline
            Assert.IsNotNull(testButton.Author, "Author should not be null");
            Assert.IsNotEmpty(testButton.Author, "Author should not be empty");

            // Author should contain all names separated by newlines
            Assert.IsTrue(testButton.Author.Contains("Gui Talarico"),
                         $"Author should contain 'Gui Talarico', but was: '{testButton.Author}'");
            Assert.IsTrue(testButton.Author.Contains("{{author}}"),
                         $"Author should contain '{{{{author}}}}', but was: '{testButton.Author}'");
            Assert.IsTrue(testButton.Author.Contains("Alex Melnikov"),
                         $"Author should contain 'Alex Melnikov', but was: '{testButton.Author}'");

            // Should NOT be the raw ">-" marker
            Assert.IsFalse(testButton.Author == ">-",
                          "Author should not be the raw multiline marker '>-'");

            TestContext.Out.WriteLine("✓ Multiline author parsing test verified successfully!");
            Assert.Pass("Multiline author parsing test completed successfully");
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