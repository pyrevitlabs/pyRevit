using System;
using System.IO;
using System.Linq;
using System.Text;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class Tests : TempFileTestBase
    {
        private IEnumerable<ParsedExtension>? _installedExtensions;
        private string? _testExtensionPath;

        [SetUp]
        public void Setup()
        {
            // Create comprehensive test extension on-the-fly
            _testExtensionPath = TestExtensionFactory.CreateComprehensiveTestExtension(TestTempDir);
            _installedExtensions = ParseInstalledExtensions(new[] { _testExtensionPath });
        }

        [Test]
        public void ParsingTest()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    TestContext.Out.WriteLine($"Parsed extension: {parsedExtension.Name}");
                }
                Assert.Pass("Installed extensions found.");
            }
            else
            {
                Assert.Fail("No installed extensions found.");
            }
        }

        [Test]
        public void ParsingExtensionsTest()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintComponentsRecursively(parsedExtension);
                }
                Assert.Pass("Installed extensions found.");
            }
            else
            {
                Assert.Fail("No installed extensions found.");
            }
        }


        [Test]
        public void ParsingScriptData()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintScriptDataRecursively(parsedExtension);
                }
                Assert.Pass("Script data parsing completed.");
            }
            else
            {
                Assert.Fail("No installed extensions found.");
            }
        }

        public void PrintComponentsRecursively(ParsedComponent parsedComponent, int level = 0)
        {
            var indent = new string('-', level * 2);
            TestContext.Out.WriteLine($"{indent}- ({parsedComponent.Name}) - {parsedComponent.DisplayName}");
            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintComponentsRecursively(child, level + 1);
                }
            }
        }
        
        public void PrintScriptDataRecursively(ParsedComponent parsedComponent, int level = 0)
        {
            // Only print components that have script files
            if (!string.IsNullOrEmpty(parsedComponent.ScriptPath))
            {
                var indent = new string('-', level * 2);
                TestContext.Out.WriteLine($"{indent}[SCRIPT] {parsedComponent.Name}");
                TestContext.Out.WriteLine($"{indent}  Display Name: {parsedComponent.DisplayName ?? "N/A"}");
                TestContext.Out.WriteLine($"{indent}  Script Path: {parsedComponent.ScriptPath}");
                TestContext.Out.WriteLine($"{indent}  Title: {parsedComponent.Title ?? "N/A"}");
                TestContext.Out.WriteLine($"{indent}  Tooltip: {parsedComponent.Tooltip ?? "N/A"}");
                TestContext.Out.WriteLine($"{indent}  Author: {parsedComponent.Author ?? "N/A"}");
                TestContext.Out.WriteLine($"{indent}  Component Type: {parsedComponent.Type}");
                
                // Special debug for problematic components
                if (parsedComponent.Name.Contains("About") || parsedComponent.Name.Contains("Settings") || 
                    parsedComponent.Name.Contains("ManagePackages") || parsedComponent.Name.Contains("Tag"))
                {
                    TestContext.Out.WriteLine($"{indent}  [DEBUG] Problematic component detected!");
                    TestContext.Out.WriteLine($"{indent}  [DEBUG] Bundle File: {parsedComponent.BundleFile ?? "None"}");
                    TestContext.Out.WriteLine($"{indent}  [DEBUG] Tooltip Length: {parsedComponent.Tooltip?.Length ?? 0}");
                    TestContext.Out.WriteLine($"{indent}  [DEBUG] Tooltip Contains Newlines: {(parsedComponent.Tooltip?.Contains('\n') ?? false)}");
                    TestContext.Out.WriteLine($"{indent}  [DEBUG] Tooltip Contains 'en_us': {(parsedComponent.Tooltip?.Contains("en_us") ?? false)}");
                    
                    if (!string.IsNullOrEmpty(parsedComponent.BundleFile))
                    {
                        try
                        {
                            var bundleData = BundleParser.BundleYamlParser.Parse(parsedComponent.BundleFile);
                            TestContext.Out.WriteLine($"{indent}  [DEBUG] Bundle Tooltips Count: {bundleData.Tooltips?.Count ?? 0}");
                            if (bundleData.Tooltips?.Count > 0)
                            {
                                foreach (var kvp in bundleData.Tooltips)
                                {
                                    TestContext.Out.WriteLine($"{indent}  [DEBUG] Bundle Tooltip [{kvp.Key}]: {kvp.Value.Substring(0, Math.Min(50, kvp.Value.Length))}...");
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            TestContext.Out.WriteLine($"{indent}  [DEBUG] Bundle parse error: {ex.Message}");
                        }
                    }
                }
                
                TestContext.Out.WriteLine($"{indent}  --------------------------------");
            }

            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintScriptDataRecursively(child, level + 1);
                }
            }
        }

        [Test]
        public void TestPulldownTooltipParsing()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    var pulldownComponent = FindComponentRecursively(parsedExtension, "TestPulldown");
                    if (pulldownComponent != null)
                    {
                        TestContext.Out.WriteLine("=== Test Pulldown Bundle Parsing Results ===");
                        TestContext.Out.WriteLine($"Component: {pulldownComponent.Name}");
                        TestContext.Out.WriteLine($"Display Name: {pulldownComponent.DisplayName}");
                        TestContext.Out.WriteLine($"Bundle File: {pulldownComponent.BundleFile}");
                        TestContext.Out.WriteLine($"Tooltip: {pulldownComponent.Tooltip}");
                        TestContext.Out.WriteLine($"Type: {pulldownComponent.Type}");
                        
                        // Verify the component was parsed correctly
                        Assert.That(pulldownComponent.Type, Is.EqualTo(CommandComponentType.PullDown),
                                        "Component should be PullDown type");
                        Assert.IsNotNull(pulldownComponent.Tooltip, "Tooltip should not be null");
                        
                        // Should not contain YAML syntax
                        Assert.IsFalse(pulldownComponent.Tooltip.Contains("en_us:"), "Tooltip should not contain YAML syntax");
                        Assert.IsFalse(pulldownComponent.Tooltip.Contains(">-"), "Tooltip should not contain YAML folding indicators");
                        
                        // Should contain the actual content
                        Assert.IsTrue(pulldownComponent.Tooltip.Contains("This is a test tooltip for the pulldown button"), 
                                     $"Should contain the pulldown tooltip content, but was: '{pulldownComponent.Tooltip}'");
                        
                        Assert.Pass("Pulldown tooltip parsing test completed successfully.");
                        return;
                    }
                }
                Assert.Fail("TestPulldown component not found in parsed extensions");
            }
            else
            {
                Assert.Fail("No installed extensions found.");
            }
        }

        [Test]
        public void TestMultilineTooltipParsing()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    var tooltipComponent = FindComponentRecursively(parsedExtension, "TestTooltip");
                    if (tooltipComponent != null)
                    {
                        TestContext.Out.WriteLine("=== Test Multiline Tooltip Bundle Parsing Results ===");
                        TestContext.Out.WriteLine($"Component: {tooltipComponent.Name}");
                        TestContext.Out.WriteLine($"Display Name: {tooltipComponent.DisplayName}");
                        TestContext.Out.WriteLine($"Bundle File: {tooltipComponent.BundleFile}");
                        TestContext.Out.WriteLine($"Tooltip: {tooltipComponent.Tooltip}");
                        TestContext.Out.WriteLine($"Type: {tooltipComponent.Type}");
                        
                        // Verify the component was parsed correctly
                        Assert.IsNotNull(tooltipComponent.Tooltip, "Tooltip should not be null");
                        
                        // Should not contain YAML syntax
                        Assert.IsFalse(tooltipComponent.Tooltip.Contains("en_us:"), "Tooltip should not contain YAML syntax");
                        Assert.IsFalse(tooltipComponent.Tooltip.Contains(">-"), "Tooltip should not contain YAML folding indicators");
                        Assert.IsFalse(tooltipComponent.Tooltip.Contains("ru:"), "Tooltip should not contain YAML syntax");
                        
                        // Should contain the actual content
                        Assert.IsTrue(tooltipComponent.Tooltip.Contains("This is a test tooltip in English"), 
                                     $"Should contain the English content, but was: '{tooltipComponent.Tooltip}'");
                        
                        Assert.Pass("Multiline tooltip parsing test completed successfully.");
                        return;
                    }
                }
                Assert.Fail("TestTooltip component not found in parsed extensions");
            }
            else
            {
                Assert.Fail("No installed extensions found.");
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
    }
}
