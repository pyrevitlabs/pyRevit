using pyRevitExtensionParser;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class PanelBackgroundTests
    {
        private IEnumerable<ParsedExtension>? _installedExtensions;
        
        [SetUp]
        public void Setup()
        {
            _installedExtensions = ParseInstalledExtensions();
        }

        [Test]
        public void TestPanelWithMultilineBackgroundParsing()
        {
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

            TestContext.Out.WriteLine("=== Testing Panel With Multi-line Background ===");
            TestContext.Out.WriteLine($"Test bundle path: {testBundlePath}");
            
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            
            foreach (var extension in extensions)
            {
                TestContext.Out.WriteLine($"Extension: {extension.Name}");
                
                // Find the Test Panel Colors panel
                var panel = FindComponentRecursively(extension, "TestPanelColors");
                if (panel != null)
                {
                    TestContext.Out.WriteLine($"Found Panel: {panel.DisplayName}");
                    TestContext.Out.WriteLine($"Panel Type: {panel.Type}");
                    TestContext.Out.WriteLine($"Panel Background: {panel.PanelBackground ?? "NULL"}");
                    TestContext.Out.WriteLine($"Title Background: {panel.TitleBackground ?? "NULL"}");
                    TestContext.Out.WriteLine($"Slideout Background: {panel.SlideoutBackground ?? "NULL"}");
                    
                    // Verify multi-line background format was parsed correctly
                    Assert.AreEqual(CommandComponentType.Panel, panel.Type);
                    Assert.AreEqual("#BB005591", panel.PanelBackground, "Panel background should be '#BB005591'");
                    Assert.AreEqual("#E2A000", panel.TitleBackground, "Title background should be '#E2A000'");
                    Assert.AreEqual("#E25200", panel.SlideoutBackground, "Slideout background should be '#E25200'");
                    
                    return; // Test passed
                }
            }
            
            Assert.Fail("Test Panel Colors panel not found");
        }

        [Test]
        public void TestPanelWithSingleLineBackgroundParsing()
        {
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

            TestContext.Out.WriteLine("=== Testing Panel With Single-line Background ===");
            TestContext.Out.WriteLine($"Test bundle path: {testBundlePath}");
            
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            
            foreach (var extension in extensions)
            {
                TestContext.Out.WriteLine($"Extension: {extension.Name}");
                
                // Find the Test Panel Background panel
                var panel = FindComponentRecursively(extension, "TestPanelBackground");
                if (panel != null)
                {
                    TestContext.Out.WriteLine($"Found Panel: {panel.DisplayName}");
                    TestContext.Out.WriteLine($"Panel Type: {panel.Type}");
                    TestContext.Out.WriteLine($"Panel Background: {panel.PanelBackground ?? "NULL"}");
                    TestContext.Out.WriteLine($"Title Background: {panel.TitleBackground ?? "NULL"}");
                    TestContext.Out.WriteLine($"Slideout Background: {panel.SlideoutBackground ?? "NULL"}");
                    
                    // Verify single-line background format was parsed correctly
                    Assert.AreEqual(CommandComponentType.Panel, panel.Type);
                    Assert.AreEqual("#BB005591", panel.PanelBackground, "Panel background should be '#BB005591'");
                    Assert.IsNull(panel.TitleBackground, "Title background should be null for single-line format");
                    Assert.IsNull(panel.SlideoutBackground, "Slideout background should be null for single-line format");
                    
                    return; // Test passed
                }
            }
            
            Assert.Fail("Test Panel Background panel not found");
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
