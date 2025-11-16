using System;
using System.IO;
using System.Linq;
using NUnit.Framework;
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
            var extensionRoot = Path.GetFullPath(Path.Combine(
                TestContext.CurrentContext.TestDirectory,
                "..", "..", "..", "..", "..", "..",
                "extensions"));

            if (!Directory.Exists(extensionRoot))
            {
                Assert.Inconclusive("Extensions directory not found at: " + extensionRoot);
                return;
            }

            var extensions = ParseInstalledExtensions(new[] { extensionRoot });
            
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
            var scriptPath = @"C:\dev\romangolev\pyRevit\extensions\pyRevitDevTools.extension\pyRevitDev.tab\Debug.panel\Bundle Tests.pulldown\Test C# Script.pushbutton";
            
            if (!Directory.Exists(scriptPath))
            {
                Assert.Inconclusive("Test C# Script directory not found at: " + scriptPath);
                return;
            }

            var scriptFile = Path.Combine(scriptPath, "script.cs");
            Assert.IsTrue(File.Exists(scriptFile), "script.cs should exist in the Test C# Script button");

            // Parse the extension containing this script
            var extensionRoot = Path.GetFullPath(Path.Combine(scriptPath, "..", "..", "..", ".."));
            var extensions = ParseInstalledExtensions(new[] { extensionRoot });
            
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
            var extensionRoot = Path.GetFullPath(Path.Combine(
                TestContext.CurrentContext.TestDirectory,
                "..", "..", "..", "..", "..", "..",
                "extensions"));

            if (!Directory.Exists(extensionRoot))
            {
                Assert.Inconclusive("Extensions directory not found");
                return;
            }

            var extensions = ParseInstalledExtensions(new[] { extensionRoot });
            
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

        private ParsedComponent FindComponentByName(ParsedComponent component, string name)
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

            return null;
        }

        private ParsedComponent FindComponentByPath(ParsedComponent component, string path)
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
            var extensionRoot = Path.GetFullPath(Path.Combine(
                TestContext.CurrentContext.TestDirectory,
                "..", "..", "..", "..", "..", "..",
                "extensions"));

            if (!Directory.Exists(extensionRoot))
            {
                Assert.Inconclusive("Extensions directory not found at: " + extensionRoot);
                return;
            }

            var extensions = ParseInstalledExtensions(new[] { extensionRoot });
            var devToolsExtension = extensions.FirstOrDefault(e => e.Name == "pyRevitDevTools");
            
            if (devToolsExtension == null)
            {
                Assert.Inconclusive("pyRevitDevTools extension not found");
                return;
            }

            // Find the Test C# Script component
            var scriptPath = @"C:\dev\romangolev\pyRevit\extensions\pyRevitDevTools.extension\pyRevitDev.tab\Debug.panel\Bundle Tests.pulldown\Test C# Script.pushbutton";
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
    }
}
