using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;
using System.Linq;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class UrlButtonTests
    {
        [Test]
        public void TestUrlButtonParsing()
        {
            // Parse the pyRevitDevTools extension which has URL buttons
            var devToolsPath = Path.Combine(
                TestContext.CurrentContext.TestDirectory, 
                "..", "..", "..", "..", "..", "..",
                "extensions", "pyRevitDevTools.extension");
            
            if (!Directory.Exists(devToolsPath))
            {
                Assert.Inconclusive($"pyRevitDevTools extension not found at {devToolsPath}");
                return;
            }
            
            var extensions = ParseInstalledExtensions(new[] { devToolsPath });
            var devToolsExt = extensions.FirstOrDefault();
            
            Assert.IsNotNull(devToolsExt, "Should parse pyRevitDevTools extension");
            TestContext.Out.WriteLine($"Extension: {devToolsExt.Name}");
            
            // Find the apidocs URL button
            var apidocsButton = FindComponentRecursively(devToolsExt, "apidocs");
            
            if (apidocsButton == null)
            {
                // Print all components to help debug
                TestContext.Out.WriteLine("Available components:");
                PrintAllComponents(devToolsExt, "");
                Assert.Fail("apidocs URL button not found");
            }
            
            TestContext.Out.WriteLine($"\nFound URL Button: {apidocsButton.DisplayName}");
            TestContext.Out.WriteLine($"Type: {apidocsButton.Type}");
            TestContext.Out.WriteLine($"Hyperlink: {apidocsButton.Hyperlink}");
            TestContext.Out.WriteLine($"Tooltip: {apidocsButton.Tooltip}");
            TestContext.Out.WriteLine($"Context: {apidocsButton.Context}");
            TestContext.Out.WriteLine($"BundleFile: {apidocsButton.BundleFile}");
            
            // Verify it's parsed as a URL button
            Assert.AreEqual(CommandComponentType.UrlButton, apidocsButton.Type, 
                "Button should be parsed as UrlButton type");
            
            // Verify the hyperlink is parsed
            Assert.IsNotNull(apidocsButton.Hyperlink, "Hyperlink should not be null");
            Assert.IsNotEmpty(apidocsButton.Hyperlink, "Hyperlink should not be empty");
            Assert.IsTrue(apidocsButton.Hyperlink.StartsWith("http"), 
                "Hyperlink should be a valid URL");
            
            // Verify other properties
            Assert.IsNotNull(apidocsButton.Tooltip, "Tooltip should not be null");
            Assert.AreEqual("zero-doc", apidocsButton.Context, "Context should be zero-doc");
            
            TestContext.Out.WriteLine("\n✓ URL button parsing test passed!");
        }
        
        [Test]
        public void TestMultipleUrlButtons()
        {
            var devToolsPath = Path.Combine(
                TestContext.CurrentContext.TestDirectory, 
                "..", "..", "..", "..", "..", "..",
                "extensions", "pyRevitDevTools.extension");
            
            if (!Directory.Exists(devToolsPath))
            {
                Assert.Inconclusive($"pyRevitDevTools extension not found at {devToolsPath}");
                return;
            }
            
            var extensions = ParseInstalledExtensions(new[] { devToolsPath });
            var devToolsExt = extensions.FirstOrDefault();
            
            // Count all URL buttons in the extension
            var urlButtons = GetAllComponentsFlat(devToolsExt)
                .Where(c => c.Type == CommandComponentType.UrlButton)
                .ToList();
            
            TestContext.Out.WriteLine($"Found {urlButtons.Count} URL button(s)");
            
            foreach (var btn in urlButtons)
            {
                TestContext.Out.WriteLine($"\nURL Button: {btn.DisplayName}");
                TestContext.Out.WriteLine($"  Hyperlink: {btn.Hyperlink}");
                TestContext.Out.WriteLine($"  Tooltip: {btn.Tooltip}");
                
                // Verify each URL button has a hyperlink
                Assert.IsNotNull(btn.Hyperlink, 
                    $"URL button {btn.DisplayName} should have a hyperlink");
                Assert.IsNotEmpty(btn.Hyperlink, 
                    $"URL button {btn.DisplayName} hyperlink should not be empty");
            }
            
            Assert.IsTrue(urlButtons.Count > 0, "Should find at least one URL button");
        }
        
        // Helper method to find a component recursively
        private ParsedComponent FindComponentRecursively(ParsedComponent root, string name)
        {
            if (root.Name != null && root.Name.Equals(name, System.StringComparison.OrdinalIgnoreCase))
                return root;
            
            if (root.Children != null)
            {
                foreach (var child in root.Children)
                {
                    var found = FindComponentRecursively(child, name);
                    if (found != null)
                        return found;
                }
            }
            
            return null;
        }
        
        private ParsedComponent FindComponentRecursively(ParsedExtension extension, string name)
        {
            if (extension.Children != null)
            {
                foreach (var child in extension.Children)
                {
                    var found = FindComponentRecursively(child, name);
                    if (found != null)
                        return found;
                }
            }
            return null;
        }
        
        // Helper method to get all components in a flat list
        private System.Collections.Generic.List<ParsedComponent> GetAllComponentsFlat(ParsedComponent root)
        {
            var result = new System.Collections.Generic.List<ParsedComponent> { root };
            if (root.Children != null)
            {
                foreach (var child in root.Children)
                {
                    result.AddRange(GetAllComponentsFlat(child));
                }
            }
            return result;
        }
        
        private System.Collections.Generic.List<ParsedComponent> GetAllComponentsFlat(ParsedExtension extension)
        {
            var result = new System.Collections.Generic.List<ParsedComponent>();
            if (extension.Children != null)
            {
                foreach (var child in extension.Children)
                {
                    result.AddRange(GetAllComponentsFlat(child));
                }
            }
            return result;
        }
        
        // Helper to print all components
        private void PrintAllComponents(ParsedComponent component, string indent)
        {
            TestContext.Out.WriteLine($"{indent}{component.Name} ({component.Type})");
            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    PrintAllComponents(child, indent + "  ");
                }
            }
        }
        
        private void PrintAllComponents(ParsedExtension extension, string indent)
        {
            TestContext.Out.WriteLine($"{indent}{extension.Name}");
            if (extension.Children != null)
            {
                foreach (var child in extension.Children)
                {
                    PrintAllComponents(child, indent + "  ");
                }
            }
        }
    }
}
