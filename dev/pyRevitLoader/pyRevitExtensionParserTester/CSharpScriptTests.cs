using System.IO;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class CSharpScriptTests
    {
        [Test]
        public void TestCSharpScriptDetection()
        {
            // Test that the parser can detect C# scripts in pyRevitDevTools extension
            var extensionPath = TestConfiguration.TestExtensionPath;

            if (!Directory.Exists(extensionPath))
            {
                Assert.Inconclusive("pyRevitDevTools extension directory not found at: " + extensionPath);
                return;
            }

            var extensions = ParseInstalledExtensions(new[] { extensionPath });
            
            // Find the pyRevitDevTools extension
            var devToolsExtension = extensions.FirstOrDefault(e => e.Name == "pyRevitDevTools");
            
            if (devToolsExtension == null)
            {
                Assert.Inconclusive("pyRevitDevTools extension not found");
                return;
            }

            // Find C# script components
            var csharpComponents = FindCSharpScripts(devToolsExtension);
            
            TestContext.Out.WriteLine($"Found {csharpComponents.Count} C# script components:");
            foreach (var component in csharpComponents)
            {
                TestContext.Out.WriteLine($"  - {component.Name}: {component.ScriptPath}");
            }

            Assert.IsTrue(csharpComponents.Count > 0, 
                "Should find at least one C# script component in pyRevitDevTools extension");
            
            // Verify that the script paths end with .cs
            foreach (var component in csharpComponents)
            {
                Assert.IsTrue(component.ScriptPath.EndsWith(".cs", StringComparison.OrdinalIgnoreCase),
                    $"C# script path should end with .cs: {component.ScriptPath}");
            }
        }

        [Test]
        public void TestSpecificCSharpScript()
        {
            // Test the specific C# script mentioned in the user's request
            var extensionPath = TestConfiguration.TestExtensionPath;
            var scriptPath = Path.Combine(extensionPath, "pyRevitDev.tab", "Debug.panel", "Bundle Tests.pulldown", "Test C# Script.pushbutton");
            
            if (!Directory.Exists(scriptPath))
            {
                Assert.Inconclusive("Test C# Script directory not found at: " + scriptPath);
                return;
            }

            var scriptFile = Path.Combine(scriptPath, "script.cs");
            Assert.IsTrue(File.Exists(scriptFile), "script.cs should exist in the Test C# Script button");

            // Parse the extension containing this script
            var extensions = ParseInstalledExtensions(new[] { extensionPath });
            
            var devToolsExtension = extensions.FirstOrDefault(e => e.Name == "pyRevitDevTools");
            Assert.IsNotNull(devToolsExtension, "pyRevitDevTools extension should be parsed");

            // Find the Test C# Script component
            var testCSharpComponent = FindComponentByName(devToolsExtension, "TestCSharpScript");
            
            if (testCSharpComponent == null)
            {
                // Try alternative naming
                testCSharpComponent = FindComponentByPath(devToolsExtension, scriptPath);
            }

            Assert.IsNotNull(testCSharpComponent, "Test C# Script component should be found");
            Assert.IsNotNull(testCSharpComponent.ScriptPath, "Script path should not be null");
            Assert.IsTrue(testCSharpComponent.ScriptPath.EndsWith("script.cs", StringComparison.OrdinalIgnoreCase),
                $"Script path should end with script.cs, but got: {testCSharpComponent.ScriptPath}");
            
            TestContext.Out.WriteLine($"Successfully found Test C# Script component:");
            TestContext.Out.WriteLine($"  Name: {testCSharpComponent.Name}");
            TestContext.Out.WriteLine($"  Display Name: {testCSharpComponent.DisplayName}");
            TestContext.Out.WriteLine($"  Script Path: {testCSharpComponent.ScriptPath}");
            TestContext.Out.WriteLine($"  Type: {testCSharpComponent.Type}");
        }

        [Test]
        public void TestMultipleScriptTypes()
        {
            // Test that the parser can handle various script types
            var extensionPath = TestConfiguration.TestExtensionPath;

            if (!Directory.Exists(extensionPath))
            {
                Assert.Inconclusive("pyRevitDevTools extension directory not found at: " + extensionPath);
                return;
            }

            var extensions = ParseInstalledExtensions(new[] { extensionPath });
            
            var allScripts = new System.Collections.Generic.List<ParsedComponent>();
            foreach (var ext in extensions)
            {
                allScripts.AddRange(FindAllScripts(ext));
            }

            var scriptsByType = allScripts
                .Where(c => !string.IsNullOrEmpty(c.ScriptPath))
                .GroupBy(c => Path.GetExtension(c.ScriptPath).ToLower())
                .OrderByDescending(g => g.Count());

            TestContext.Out.WriteLine("Script types found:");
            foreach (var group in scriptsByType)
            {
                TestContext.Out.WriteLine($"  {group.Key}: {group.Count()} scripts");
            }

            // Verify we found at least some .cs scripts
            var csScripts = allScripts.Count(c => c.ScriptPath?.EndsWith(".cs", StringComparison.OrdinalIgnoreCase) == true);
            TestContext.Out.WriteLine($"\nTotal C# scripts found: {csScripts}");
            
            Assert.IsTrue(csScripts > 0, "Should find at least one C# script");
        }

        private System.Collections.Generic.List<ParsedComponent> FindCSharpScripts(ParsedComponent component)
        {
            var results = new System.Collections.Generic.List<ParsedComponent>();
            
            if (!string.IsNullOrEmpty(component.ScriptPath) && 
                component.ScriptPath.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
            {
                results.Add(component);
            }

            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    results.AddRange(FindCSharpScripts(child));
                }
            }

            return results;
        }

        private System.Collections.Generic.List<ParsedComponent> FindAllComponents(ParsedComponent component)
        {
            var results = new System.Collections.Generic.List<ParsedComponent>();
            results.Add(component);

            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    results.AddRange(FindAllComponents(child));
                }
            }

            return results;
        }

        private System.Collections.Generic.List<ParsedComponent> FindAllScripts(ParsedComponent component)
        {
            var results = new System.Collections.Generic.List<ParsedComponent>();
            
            if (!string.IsNullOrEmpty(component.ScriptPath))
            {
                results.Add(component);
            }

            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    results.AddRange(FindAllScripts(child));
                }
            }

            return results;
        }

        private ParsedComponent? FindComponentByName(ParsedComponent component, string name)
        {
            if (component.Name.Replace(" ", "").Equals(name, StringComparison.OrdinalIgnoreCase))
            {
                return component;
            }

            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    var result = FindComponentByName(child, name);
                    if (result != null)
                        return result;
                }
            }

            return null!;
        }

        private ParsedComponent? FindComponentByPath(ParsedComponent component, string path)
        {
            if (component.Directory != null && 
                Path.GetFullPath(component.Directory).Equals(Path.GetFullPath(path), StringComparison.OrdinalIgnoreCase))
            {
                return component;
            }

            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    var result = FindComponentByPath(child, path);
                    if (result != null)
                        return result;
                }
            }

            return null;
        }

        [Test]
        public void TestCSharpScriptModuleLoading()
        {
            // Test that modules are parsed and can be found
            var extensionPath = TestConfiguration.TestExtensionPath;

            if (!Directory.Exists(extensionPath))
            {
                Assert.Inconclusive("pyRevitDevTools extension directory not found at: " + extensionPath);
                return;
            }

            var extensions = ParseInstalledExtensions(new[] { extensionPath });
            var devToolsExtension = extensions.FirstOrDefault(e => e.Name == "pyRevitDevTools");
            
            if (devToolsExtension == null)
            {
                Assert.Inconclusive("pyRevitDevTools extension not found");
                return;
            }

            // Find the Test C# Script component
            var scriptPath = Path.Combine(extensionPath, "pyRevitDev.tab", "Debug.panel", "Bundle Tests.pulldown", "Test C# Script.pushbutton");
            var testCSharpScript = FindComponentByPath(devToolsExtension, scriptPath);
            
            if (testCSharpScript == null)
            {
                testCSharpScript = FindComponentByName(devToolsExtension, "TestCSharpScript");
            }
            
            if (testCSharpScript == null)
            {
                Assert.Inconclusive("Test C# Script component not found");
                return;
            }

            TestContext.Out.WriteLine($"Found component: {testCSharpScript.Name}");
            TestContext.Out.WriteLine($"Modules count: {testCSharpScript.Modules.Count}");
            
            foreach (var module in testCSharpScript.Modules)
            {
                TestContext.Out.WriteLine($"  Module: {module}");
                
                // Test FindModuleDll method
                var modulePath = devToolsExtension.FindModuleDll(module, testCSharpScript);
                TestContext.Out.WriteLine($"  Found at: {modulePath ?? "NOT FOUND"}");
                
                if (modulePath != null)
                {
                    Assert.IsTrue(File.Exists(modulePath), 
                        $"Module file should exist: {modulePath}");
                }
            }
            
            Assert.IsTrue(testCSharpScript.Modules.Count > 0, 
                "Test C# Script should have at least one module (Markdown.dll)");
        }

        [Test]
        public void TestLinkButtonDetection()
        {
            // Test that the parser can detect LinkButton bundles
            var devToolsPath = TestConfiguration.TestExtensionPath;

            TestContext.Out.WriteLine($"Looking for pyRevitDevTools at: {devToolsPath}");

            if (!Directory.Exists(devToolsPath))
            {
                Assert.Inconclusive("pyRevitDevTools extension directory not found at: " + devToolsPath);
                return;
            }

            var extensions = ParseInstalledExtensions(new[] { devToolsPath });
            
            TestContext.Out.WriteLine($"Found {extensions.Count()} extensions");
            foreach (var ext in extensions)
            {
                TestContext.Out.WriteLine($"  - {ext.Name}");
            }
            
            // Find the pyRevitDevTools extension
            var devToolsExtension = extensions.FirstOrDefault(e => e.Name == "pyRevitDevTools");
            
            if (devToolsExtension == null)
            {
                Assert.Inconclusive($"pyRevitDevTools extension not found. Found extensions: {string.Join(", ", extensions.Select(e => e.Name))}");
                return;
            }

            TestContext.Out.WriteLine("=== Testing LinkButton Detection ===");
            TestContext.Out.WriteLine($"Extension: {devToolsExtension.Name}");
            
            // Look for the Test Link Button
            var linkButton = FindComponentByName(devToolsExtension, "TestLinkButton");
            
            if (linkButton == null)
            {
                // Try alternate search
                TestContext.Out.WriteLine("Searching for LinkButton components...");
                linkButton = FindAllComponents(devToolsExtension)
                    .FirstOrDefault(c => c.Type == CommandComponentType.LinkButton);
            }
            
            Assert.IsNotNull(linkButton, "Should find the Test Link Button component");
            
            TestContext.Out.WriteLine($"Found LinkButton: {linkButton.DisplayName}");
            TestContext.Out.WriteLine($"Type: {linkButton.Type}");
            TestContext.Out.WriteLine($"Directory: {linkButton.Directory}");
            TestContext.Out.WriteLine($"BundleFile: {linkButton.BundleFile}");
            
            // Verify it's a LinkButton type
            Assert.AreEqual(CommandComponentType.LinkButton, linkButton.Type, 
                "Component should be of type LinkButton");
            
            // Verify bundle.yaml exists and was parsed
            Assert.IsNotNull(linkButton.BundleFile, "LinkButton should have a bundle.yaml file");
            Assert.IsTrue(File.Exists(linkButton.BundleFile), 
                "Bundle file should exist at: " + linkButton.BundleFile);
            
            // Verify required LinkButton properties from bundle.yaml
            TestContext.Out.WriteLine($"TargetAssembly: {linkButton.TargetAssembly ?? "NULL"}");
            TestContext.Out.WriteLine($"CommandClass: {linkButton.CommandClass ?? "NULL"}");
            TestContext.Out.WriteLine($"AvailabilityClass: {linkButton.AvailabilityClass ?? "NULL"}");
            TestContext.Out.WriteLine($"Title: {linkButton.Title ?? "NULL"}");
            TestContext.Out.WriteLine($"Tooltip: {linkButton.Tooltip ?? "NULL"}");
            TestContext.Out.WriteLine($"Author: {linkButton.Author ?? "NULL"}");
            TestContext.Out.WriteLine($"Highlight: {linkButton.Highlight ?? "NULL"}");
            
            Assert.IsNotNull(linkButton.TargetAssembly, 
                "LinkButton should have 'assembly' property from bundle.yaml");
            Assert.AreEqual("PyRevitTestBundles", linkButton.TargetAssembly, 
                "TargetAssembly should match bundle.yaml content");
            
            Assert.IsNotNull(linkButton.CommandClass, 
                "LinkButton should have 'command_class' property from bundle.yaml");
            Assert.AreEqual("PyRevitTestLinkCommand", linkButton.CommandClass, 
                "CommandClass should match bundle.yaml content");
            
            Assert.IsNotNull(linkButton.AvailabilityClass, 
                "LinkButton should have 'availability_class' property from bundle.yaml");
            Assert.AreEqual("PyRevitTestLinkCommandAvail", linkButton.AvailabilityClass, 
                "AvailabilityClass should match bundle.yaml content");
            
            // Verify title from bundle.yaml
            Assert.IsNotNull(linkButton.Title, "LinkButton should have a title");
            Assert.IsTrue(linkButton.Title.Contains("Custom Title"), 
                "Title should contain 'Custom Title' from bundle.yaml");
            
            // Verify tooltip
            Assert.IsNotNull(linkButton.Tooltip, "LinkButton should have a tooltip");
            Assert.IsTrue(linkButton.Tooltip.Contains("Link Button"), 
                "Tooltip should contain 'Link Button'");
            
            // Verify highlight
            Assert.IsNotNull(linkButton.Highlight, "LinkButton should have highlight property");
            Assert.AreEqual("new", linkButton.Highlight.ToLowerInvariant(), 
                "Highlight should be 'new'");
            
            TestContext.Out.WriteLine("LinkButton detection test passed!");
        }
    }
}
