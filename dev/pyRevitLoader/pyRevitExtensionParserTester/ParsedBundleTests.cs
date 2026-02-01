using pyRevitExtensionParser;
using System.IO;
using System.Linq;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
	internal class ParsedBundleTests
	{
        private IEnumerable<ParsedExtension>? _installedExtensions;
        
        [SetUp]
        public void Setup()
        {
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "..", "..", "..", "..", "..", "..", "extensions", "pyRevitDevTools.extension");
            _installedExtensions = ParseInstalledExtensions(new[] { testBundlePath });
        }

        [Test]
        public void ParsingBundleFiles()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintBundleDataRecursively(parsedExtension);
                }
                Assert.Pass("Bundle file parsing completed.");
            }
            else
            {
                Assert.Fail("No installed extensions found.");
            }
        }

        [Test]
        public void ParseBundleLayouts()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintLayoutRecursively(parsedExtension);
                }
                Assert.Pass("...");
            }
            else
            {
                Assert.Fail("...");
            }
        }
        public void PrintBundleDataRecursively(ParsedComponent parsedComponent, int level = 0)
        {
            // Only print components that have bundle files
            if (!string.IsNullOrEmpty(parsedComponent.BundleFile))
            {
                var indent = new string('-', level * 2);
                TestContext.Out.WriteLine($"{indent}[BUNDLE] {parsedComponent.Name}");
                TestContext.Out.WriteLine($"{indent}  Display Name: {parsedComponent.DisplayName ?? "N/A"}");
                TestContext.Out.WriteLine($"{indent}  Bundle File: {parsedComponent.BundleFile}");
                
                try
                {
                    var bundleData = BundleParser.BundleYamlParser.Parse(parsedComponent.BundleFile);
                    
                    if (bundleData.Titles?.Count > 0)
                    {
                        TestContext.Out.WriteLine($"{indent}  Bundle Titles:");
                        foreach (var title in bundleData.Titles)
                        {
                            TestContext.Out.WriteLine($"{indent}    {title.Key}: {title.Value}");
                        }
                    }
                    
                    if (bundleData.Tooltips?.Count > 0)
                    {
                        TestContext.Out.WriteLine($"{indent}  Bundle Tooltips:");
                        foreach (var tooltip in bundleData.Tooltips)
                        {
                            // Truncate long tooltips for readability
                            var truncatedTooltip = tooltip.Value.Length > 100 
                                ? tooltip.Value.Substring(0, 100) + "..." 
                                : tooltip.Value;
                            TestContext.Out.WriteLine($"{indent}    {tooltip.Key}: {truncatedTooltip}");
                        }
                    }
                    
                    if (!string.IsNullOrEmpty(bundleData.Author))
                    {
                        TestContext.Out.WriteLine($"{indent}  Bundle Author: {bundleData.Author}");
                    }

                    if (bundleData.LayoutOrder?.Count > 0)
                    {
                        TestContext.Out.WriteLine($"{indent}  Layout Order: [{string.Join(", ", bundleData.LayoutOrder)}]");
                    }

                    if (!string.IsNullOrEmpty(bundleData.MinRevitVersion))
                    {
                        TestContext.Out.WriteLine($"{indent}  Min Revit Version: {bundleData.MinRevitVersion}");
                    }
                    
                    // Print context information
                    if (!string.IsNullOrEmpty(bundleData.Context))
                    {
                        TestContext.Out.WriteLine($"{indent}  Context (raw): {bundleData.Context}");
                    }
                    if (bundleData.ContextItems?.Count > 0)
                    {
                        TestContext.Out.WriteLine($"{indent}  Context Items: [{string.Join(", ", bundleData.ContextItems)}]");
                    }
                    if (bundleData.ContextRules?.Count > 0)
                    {
                        TestContext.Out.WriteLine($"{indent}  Context Rules:");
                        foreach (var rule in bundleData.ContextRules)
                        {
                            TestContext.Out.WriteLine($"{indent}    {rule.RuleType}: [{string.Join(", ", rule.Items)}]");
                        }
                    }
                    var formattedContext = bundleData.GetFormattedContext();
                    TestContext.Out.WriteLine($"{indent}  Context (formatted): {formattedContext}");
                }
                catch (System.Exception ex)
                {
                    TestContext.Out.WriteLine($"{indent}  [BUNDLE PARSE ERROR]: {ex.Message}");
                }
                
                TestContext.Out.WriteLine($"{indent}  --------------------------------");
            }

            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintBundleDataRecursively(child, level + 1);
                }
            }
        }
        public void PrintLayoutRecursively(ParsedComponent parsedComponent)
        {
            TestContext.Out.WriteLine($"{parsedComponent.Name}");
            if (parsedComponent.LayoutOrder == null)
            {
                TestContext.Out.WriteLine($"-- No layout order");
            }
            else
            {
                foreach (var str in parsedComponent.LayoutOrder)
                {
                    TestContext.Out.WriteLine($"-- {str}");
                }
            }

            TestContext.Out.WriteLine($"*******************************");

            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintLayoutRecursively(child);
                }
            }
        }

        [Test]
        public void TestContextListParsing()
        {
            // Test parsing context as a list (from Test pyRevit Bundle.pushbutton)
            var yamlContent = @"title:
  en_us: Test Context
context:
  - OST_Walls
  - OST_TextNotes
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);
            
            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);
                
                TestContext.Out.WriteLine($"Context (raw): {bundle.Context ?? "null"}");
                TestContext.Out.WriteLine($"Context Items: [{string.Join(", ", bundle.ContextItems)}]");
                TestContext.Out.WriteLine($"Context (formatted): {bundle.GetFormattedContext()}");
                
                Assert.That(bundle.ContextItems, Has.Count.EqualTo(2));
                Assert.That(bundle.ContextItems, Contains.Item("OST_Walls"));
                Assert.That(bundle.ContextItems, Contains.Item("OST_TextNotes"));
                Assert.That(bundle.GetFormattedContext(), Is.EqualTo("(OST_Walls&OST_TextNotes)"));
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestContextSimpleStringParsing()
        {
            // Test parsing context as a simple string
            var yamlContent = @"title:
  en_us: Test Context
context: zero-doc
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);
            
            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);
                
                TestContext.Out.WriteLine($"Context (raw): {bundle.Context ?? "null"}");
                TestContext.Out.WriteLine($"Context (formatted): {bundle.GetFormattedContext()}");
                
                Assert.That(bundle.Context, Is.EqualTo("zero-doc"));
                Assert.That(bundle.GetFormattedContext(), Is.EqualTo("(zero-doc)"));
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestContextRulesParsing()
        {
            // Test parsing context with rules (any:, all:, etc.)
            var yamlContent = @"title:
  en_us: Test Context Rules
context:
  any:
    - OST_Walls
    - OST_Doors
  not_all:
    - OST_TextNotes
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);
            
            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);
                
                TestContext.Out.WriteLine($"Context Rules Count: {bundle.ContextRules?.Count ?? 0}");
                if (bundle.ContextRules != null)
                {
                    foreach (var rule in bundle.ContextRules)
                    {
                        TestContext.Out.WriteLine($"  Rule: {rule.RuleType} -> [{string.Join(", ", rule.Items)}]");
                        TestContext.Out.WriteLine($"  Formatted: {rule.ToFormattedString()}");
                    }
                }
                TestContext.Out.WriteLine($"Context (formatted): {bundle.GetFormattedContext()}");
                
                Assert.That(bundle.ContextRules, Has.Count.EqualTo(2));
                
                var anyRule = bundle.ContextRules.FirstOrDefault(r => r.RuleType == "any");
                Assert.That(anyRule, Is.Not.Null);
                Assert.That(anyRule.Items, Contains.Item("OST_Walls"));
                Assert.That(anyRule.Items, Contains.Item("OST_Doors"));
                Assert.That(anyRule.ToFormattedString(), Is.EqualTo("(OST_Walls|OST_Doors)"));
                
                var notAllRule = bundle.ContextRules.FirstOrDefault(r => r.RuleType == "not_all");
                Assert.That(notAllRule, Is.Not.Null);
                Assert.That(notAllRule.Items, Contains.Item("OST_TextNotes"));
                Assert.That(notAllRule.ToFormattedString(), Is.EqualTo("!(OST_TextNotes)"));
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestDefaultContextWhenNotSpecified()
        {
            // Test that context is null when not specified (no availability class will be created)
            var yamlContent = @"title:
  en_us: Test No Context
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);
            
            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);
                
                TestContext.Out.WriteLine($"Context (raw): {bundle.Context ?? "null"}");
                TestContext.Out.WriteLine($"Context (formatted): {bundle.GetFormattedContext() ?? "null"}");
                
                Assert.That(bundle.Context, Is.Null.Or.Empty);
                Assert.That(bundle.GetFormattedContext(), Is.Null);
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestGeneratedCodeContainsContextInAvailabilityClass()
        {
            // Test that the generated C# code includes the context in the availability class constructor
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "..", "..", "..", "..", "..", "..", "extensions", "pyRevitDevTools.extension");
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            var extension = extensions.First();
            
            // Find the Test pyRevit Bundle component by DisplayName
            var allComponents = GetAllComponentsFlat(extension);
            var testBundleButton = allComponents.FirstOrDefault(c => c.DisplayName == "Test pyRevit Bundle");
            
            Assert.That(testBundleButton, Is.Not.Null, "Test pyRevit Bundle should be found");
            Assert.That(testBundleButton.Context, Is.Not.Null.And.Not.Empty, "Context should be set on component");
            
            TestContext.Out.WriteLine($"Component Name: {testBundleButton.Name}");
            TestContext.Out.WriteLine($"Component UniqueId: {testBundleButton.UniqueId}");
            TestContext.Out.WriteLine($"Component Context: {testBundleButton.Context}");
            
            // Generate code
            var codeGenerator = new pyRevitAssemblyBuilder.AssemblyMaker.RoslynCommandTypeGenerator();
            var generatedCode = codeGenerator.GenerateExtensionCode(extension, "2024");
            
            // Sanitize the class name to match what's generated
            var expectedClassName = SanitizeClassName(testBundleButton.UniqueId);
            var expectedAvailClassName = $"{expectedClassName}_avail";
            
            TestContext.Out.WriteLine($"Expected class name: {expectedClassName}");
            TestContext.Out.WriteLine($"Expected avail class name: {expectedAvailClassName}");
            
            // Check that the availability class exists with correct context
            Assert.That(generatedCode, Does.Contain($"public class {expectedAvailClassName} : ScriptCommandExtendedAvail"),
                "Generated code should contain availability class");
            
            // Check that the context is passed correctly (should contain OST_Walls)
            Assert.That(generatedCode, Does.Contain("(OST_Walls&OST_TextNotes)"),
                "Generated code should contain the formatted context string");
            
            // Print the relevant section of generated code for debugging
            var lines = generatedCode.Split('\n');
            var inAvailClass = false;
            for (int i = 0; i < lines.Length; i++)
            {
                if (lines[i].Contains(expectedAvailClassName))
                {
                    inAvailClass = true;
                    TestContext.Out.WriteLine($"=== Found availability class at line {i} ===");
                }
                if (inAvailClass)
                {
                    TestContext.Out.WriteLine(lines[i]);
                    if (lines[i].Trim() == "}")
                    {
                        inAvailClass = false;
                        TestContext.Out.WriteLine($"=== End of availability class ===");
                        break;
                    }
                }
            }
        }

        [Test]
        public void TestContextFromPythonScript()
        {
            // Test that context is parsed correctly from script.py __context__ variable
            // This tests the "Test pyRevit Button.pushbutton" which has __context__ = ['OST_Walls', 'OST_TextNotes']
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "..", "..", "..", "..", "..", "..", "extensions", "pyRevitDevTools.extension");
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            var extension = extensions.First();
            
            // Find the Test pyRevit Button component by DisplayName
            var allComponents = GetAllComponentsFlat(extension);
            var testButton = allComponents.FirstOrDefault(c => c.DisplayName == "Test pyRevit Button");
            
            Assert.That(testButton, Is.Not.Null, "Test pyRevit Button should be found");
            
            TestContext.Out.WriteLine($"Component Name: {testButton.Name}");
            TestContext.Out.WriteLine($"Component DisplayName: {testButton.DisplayName}");
            TestContext.Out.WriteLine($"Script Path: {testButton.ScriptPath}");
            TestContext.Out.WriteLine($"Context: {testButton.Context}");
            
            // The script.py has __context__ = ['OST_Walls', 'OST_TextNotes']
            // This should be formatted as (OST_Walls&OST_TextNotes)
            Assert.That(testButton.Context, Is.EqualTo("(OST_Walls&OST_TextNotes)"), 
                "Context should be parsed from script.py __context__ variable");
        }

        [Test]
        public void TestContextFromPythonScriptOverriddenByBundle()
        {
            // When bundle.yaml has context defined, it should take precedence over script.py
            // The Test pyRevit Bundle.pushbutton has context in bundle.yaml
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "..", "..", "..", "..", "..", "..", "extensions", "pyRevitDevTools.extension");
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            var extension = extensions.First();
            
            // Find the Test pyRevit Bundle component by DisplayName
            var allComponents = GetAllComponentsFlat(extension);
            var testBundle = allComponents.FirstOrDefault(c => c.DisplayName == "Test pyRevit Bundle");
            
            Assert.That(testBundle, Is.Not.Null, "Test pyRevit Bundle should be found");
            
            TestContext.Out.WriteLine($"Component Name: {testBundle.Name}");
            TestContext.Out.WriteLine($"Context: {testBundle.Context}");
            
            // Bundle.yaml has context: [OST_Walls, OST_TextNotes]
            Assert.That(testBundle.Context, Is.EqualTo("(OST_Walls&OST_TextNotes)"), 
                "Context should be from bundle.yaml");
        }

        private static IEnumerable<ParsedComponent> GetAllComponentsFlat(ParsedComponent component)
        {
            yield return component;
            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    foreach (var descendant in GetAllComponentsFlat(child))
                    {
                        yield return descendant;
                    }
                }
            }
        }

        private static string SanitizeClassName(string name)
        {
            var sb = new System.Text.StringBuilder();
            foreach (char c in name)
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            return sb.ToString();
        }

	}
}
