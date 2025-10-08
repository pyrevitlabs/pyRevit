using System;
using System.IO;
using System.Linq;
using System.Text;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class Tests
    {
        private IEnumerable<ParsedExtension>? _installedExtensions;

        [SetUp]
        public void Setup()
        {
            // Collect all supported by pyRevit extensions
            _installedExtensions = ParseInstalledExtensions();
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
            // Try multiple paths to find the test resource
            var possiblePaths = new[]
            {
                @"Resources\TestBundleExtension.extension\TestBundleTab1.tab\TestPanelTwo.panel\TestPulldown.pulldown\bundle.yaml",
                Path.Combine("Resources", "TestBundleExtension.extension", "TestBundleTab1.tab", "TestPanelTwo.panel", "TestPulldown.pulldown", "bundle.yaml"),
                Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension", "TestBundleTab1.tab", "TestPanelTwo.panel", "TestPulldown.pulldown", "bundle.yaml"),
                Path.Combine(Directory.GetCurrentDirectory(), "Resources", "TestBundleExtension.extension", "TestBundleTab1.tab", "TestPanelTwo.panel", "TestPulldown.pulldown", "bundle.yaml")
            };

            string testBundlePath = null;
            foreach (var path in possiblePaths)
            {
                if (File.Exists(path))
                {
                    testBundlePath = path;
                    break;
                }
            }

            if (testBundlePath != null)
            {
                try
                {
                    var bundleData = BundleParser.BundleYamlParser.Parse(testBundlePath);
                    
                    TestContext.Out.WriteLine("=== Test Pulldown Bundle Parsing Results ===");
                    TestContext.Out.WriteLine($"Bundle file: {testBundlePath}");
                    
                    if (bundleData.Titles?.Count > 0)
                    {
                        TestContext.Out.WriteLine("Titles:");
                        foreach (var title in bundleData.Titles)
                        {
                            TestContext.Out.WriteLine($"  {title.Key}: {title.Value}");
                        }
                    }
                    
                    if (bundleData.Tooltips?.Count > 0)
                    {
                        TestContext.Out.WriteLine("Tooltips:");
                        foreach (var tooltip in bundleData.Tooltips)
                        {
                            TestContext.Out.WriteLine($"  {tooltip.Key}: {tooltip.Value}");
                        }
                    }
                    
                    if (!string.IsNullOrEmpty(bundleData.Author))
                    {
                        TestContext.Out.WriteLine($"Author: {bundleData.Author}");
                    }
                    
                    // Verify that en_us tooltip was parsed correctly
                    Assert.IsTrue(bundleData.Tooltips.ContainsKey("en_us"), "Should contain en_us tooltip");
                    
                    var enTooltip = bundleData.Tooltips["en_us"];
                    TestContext.Out.WriteLine($"English tooltip: '{enTooltip}'");
                    
                    // Should not contain YAML syntax
                    Assert.IsFalse(enTooltip.Contains("en_us:"), "Tooltip should not contain YAML syntax");
                    Assert.IsFalse(enTooltip.Contains(">-"), "Tooltip should not contain YAML folding indicators");
                    
                    // Should contain the actual content
                    Assert.IsTrue(enTooltip.Contains("This is a test tooltip for the pulldown button"), "Should contain the pulldown tooltip content");
                    
                    Assert.Pass("Pulldown tooltip parsing test completed successfully.");
                }
                catch (Exception ex)
                {
                    Assert.Fail($"Failed to parse test pulldown bundle: {ex.Message}");
                }
            }
            else
            {
                // Show what paths were tried for debugging
                TestContext.Out.WriteLine("Attempted paths:");
                foreach (var path in possiblePaths)
                {
                    TestContext.Out.WriteLine($"  {path} - Exists: {File.Exists(path)}");
                }
                TestContext.Out.WriteLine($"Current Directory: {Directory.GetCurrentDirectory()}");
                TestContext.Out.WriteLine($"Test Directory: {TestContext.CurrentContext.TestDirectory}");
                
                Assert.Fail("Test pulldown bundle file not found in any expected location");
            }
        }

        [Test]
        public void TestMultilineTooltipParsing()
        {
            // Try multiple paths to find the test resource
            var possiblePaths = new[]
            {
                @"Resources\TestBundleExtension.extension\TestBundleTab1.tab\TestPanelTwo.panel\TestTooltip.pushbutton\bundle.yaml",
                Path.Combine("Resources", "TestBundleExtension.extension", "TestBundleTab1.tab", "TestPanelTwo.panel", "TestTooltip.pushbutton", "bundle.yaml"),
                Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension", "TestBundleTab1.tab", "TestPanelTwo.panel", "TestTooltip.pushbutton", "bundle.yaml"),
                Path.Combine(Directory.GetCurrentDirectory(), "Resources", "TestBundleExtension.extension", "TestBundleTab1.tab", "TestPanelTwo.panel", "TestTooltip.pushbutton", "bundle.yaml")
            };

            string testBundlePath = null;
            foreach (var path in possiblePaths)
            {
                if (File.Exists(path))
                {
                    testBundlePath = path;
                    break;
                }
            }

            if (testBundlePath != null)
            {
                try
                {
                    var bundleData = BundleParser.BundleYamlParser.Parse(testBundlePath);
                    
                    TestContext.Out.WriteLine("=== Test Bundle Parsing Results ===");
                    TestContext.Out.WriteLine($"Bundle file: {testBundlePath}");
                    
                    if (bundleData.Titles?.Count > 0)
                    {
                        TestContext.Out.WriteLine("Titles:");
                        foreach (var title in bundleData.Titles)
                        {
                            TestContext.Out.WriteLine($"  {title.Key}: {title.Value}");
                        }
                    }
                    
                    if (bundleData.Tooltips?.Count > 0)
                    {
                        TestContext.Out.WriteLine("Tooltips:");
                        foreach (var tooltip in bundleData.Tooltips)
                        {
                            TestContext.Out.WriteLine($"  {tooltip.Key}: {tooltip.Value}");
                        }
                    }
                    
                    if (!string.IsNullOrEmpty(bundleData.Author))
                    {
                        TestContext.Out.WriteLine($"Author: {bundleData.Author}");
                    }
                    
                    // Verify that en_us tooltip was parsed correctly
                    Assert.IsTrue(bundleData.Tooltips.ContainsKey("en_us"), "Should contain en_us tooltip");
                    Assert.IsTrue(bundleData.Tooltips.ContainsKey("ru"), "Should contain ru tooltip");
                    
                    var enTooltip = bundleData.Tooltips["en_us"];
                    var ruTooltip = bundleData.Tooltips["ru"];
                    TestContext.Out.WriteLine($"English tooltip: '{enTooltip}'");
                    
                    // Should not contain YAML syntax
                    Assert.IsFalse(enTooltip.Contains("en_us:"), "Tooltip should not contain YAML syntax");
                    Assert.IsFalse(enTooltip.Contains(">-"), "Tooltip should not contain YAML folding indicators");
                   
                    Assert.IsFalse(ruTooltip.Contains("ru:"), "Tooltip should not contain YAML syntax");
                    Assert.IsFalse(ruTooltip.Contains(">-"), "Tooltip should not contain YAML folding indicators");
                    
                    // Should contain the actual content
                    Assert.IsTrue(enTooltip.Contains("This is a test tooltip in English"), "Should contain the English content");
                    Assert.IsTrue(ruTooltip.Contains("Это тестовая подсказка на русском языке."), "Should contain the Russian content");
                }
                catch (Exception ex)
                {
                    Assert.Fail($"Failed to parse test bundle: {ex.Message}");
                }
            }
            else
            {
                // Show what paths were tried for debugging
                TestContext.Out.WriteLine("Attempted paths:");
                foreach (var path in possiblePaths)
                {
                    TestContext.Out.WriteLine($"  {path} - Exists: {File.Exists(path)}");
                }
                TestContext.Out.WriteLine($"Current Directory: {Directory.GetCurrentDirectory()}");
                TestContext.Out.WriteLine($"Test Directory: {TestContext.CurrentContext.TestDirectory}");
                
                Assert.Fail("Test bundle file not found in any expected location");
            }
        }

    }
}
