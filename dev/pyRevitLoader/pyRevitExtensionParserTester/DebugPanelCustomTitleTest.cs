using pyRevitExtensionParser;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class DebugPanelCustomTitleTest
    {
        [Test]
        public void TestDebugPanelMiscTestsCustomTitle()
        {
            // Test the actual Debug.panel from pyRevitDevTools extension
            var testBundlePath = Path.Combine(
                TestContext.CurrentContext.TestDirectory, 
                "..", "..", "..", "..", "..", "..", 
                "extensions", "pyRevitDevTools.extension"
            );
            
            if (!Directory.Exists(testBundlePath))
            {
                Assert.Inconclusive($"Test bundle path not found: {testBundlePath}");
                return;
            }

            TestContext.Out.WriteLine("=== Testing Debug Panel Custom Title ===");
            TestContext.Out.WriteLine($"Test bundle path: {testBundlePath}");
            
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            
            foreach (var extension in extensions)
            {
                TestContext.Out.WriteLine($"Extension: {extension.Name}");
                
                // Find the Debug panel
                var debugPanel = FindComponentRecursively(extension, "Debug");
                if (debugPanel != null)
                {
                    TestContext.Out.WriteLine($"Found Panel: {debugPanel.DisplayName}");
                    TestContext.Out.WriteLine($"Panel has {debugPanel.Children?.Count ?? 0} children");
                    
                    // Find "Misc Tests" pulldown
                    var miscTests = debugPanel.Children?.FirstOrDefault(c => c?.DisplayName == "Misc Tests");
                    if (miscTests != null)
                    {
                        TestContext.Out.WriteLine($"Found Misc Tests: {miscTests.DisplayName}");
                        TestContext.Out.WriteLine($"Title: '{miscTests.Title}'");
                        
                        // Verify the custom title was applied
                        Assert.IsNotNull(miscTests.Title, "Misc Tests should have a custom title");
                        Assert.AreEqual("Third-Party\nUnit Tests", miscTests.Title, 
                            "Custom title should be 'Third-Party\\nUnit Tests' with newline");
                        
                        TestContext.Out.WriteLine("✓ Custom title correctly applied!");
                        return; // Test passed
                    }
                    else
                    {
                        TestContext.Out.WriteLine("Misc Tests not found in Debug panel");
                        if (debugPanel.Children != null)
                        {
                            TestContext.Out.WriteLine("Available children:");
                            foreach (var child in debugPanel.Children)
                            {
                                TestContext.Out.WriteLine($"  - {child?.DisplayName} (Type: {child?.Type})");
                            }
                        }
                    }
                }
            }
            
            Assert.Fail("Debug panel or Misc Tests component not found");
        }

        // Helper method to find a component recursively
        private ParsedComponent? FindComponentRecursively(ParsedExtension extension, string name)
        {
            return FindComponentRecursively(extension.Children, name);
        }
        
        private ParsedComponent? FindComponentRecursively(List<ParsedComponent>? components, string name)
        {
            if (components == null) return null;
            
            foreach (var component in components)
            {
                if (component.Name.Equals(name, StringComparison.OrdinalIgnoreCase))
                    return component;
                    
                var found = FindComponentRecursively(component.Children, name);
                if (found != null)
                    return found;
            }
            
            return null;
        }
    }
}
