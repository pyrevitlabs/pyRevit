using System;
using System.IO;
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
        [Test]
        public void HasSlideout()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintSlideoutRecursively(parsedExtension);
                }
                Assert.Pass("...");
            }
            else
            {
                Assert.Fail("...");
            }
        }

        [Test]
        public void IsParsingScriptFile()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintTitleRecursively(parsedExtension);
                }
                Assert.Pass("...");
            }
            else
            {
                Assert.Fail("...");
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
        public void PrintSlideoutRecursively(ParsedComponent parsedComponent)
        {
            TestContext.Out.WriteLine($"{parsedComponent.Name} -- has slideout {parsedComponent.HasSlideout}");
            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintSlideoutRecursively(child);
                }
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
        public void PrintTitleRecursively(ParsedComponent parsedComponent, int level = 0)
        {
            var indent = new string('-', level * 2);
            TestContext.Out.WriteLine($"{indent}- ({parsedComponent.Name}) - {parsedComponent.DisplayName} - {parsedComponent.Title} - {parsedComponent.Tooltip} - {parsedComponent.Author}");
            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintTitleRecursively(child, level + 1);
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

        [Test]
        public void TestMultilineTooltipParsing()
        {
            var testBundlePath = @"Resources\TestBundleExtension.extension\TestBundleTab1.tab\TestTooltip.pushbutton\bundle.yaml";
            if (File.Exists(testBundlePath))
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
                    
                    var enTooltip = bundleData.Tooltips["en_us"];
                    TestContext.Out.WriteLine($"English tooltip: '{enTooltip}'");
                    
                    // Should not contain YAML syntax
                    Assert.IsFalse(enTooltip.Contains("en_us:"), "Tooltip should not contain YAML syntax");
                    Assert.IsFalse(enTooltip.Contains(">-"), "Tooltip should not contain YAML folding indicators");
                    
                    // Should contain the actual content
                    Assert.IsTrue(enTooltip.Contains("This is a test tooltip in English"), "Should contain the English content");
                    
                    Assert.Pass("Multiline tooltip parsing test completed successfully.");
                }
                catch (Exception ex)
                {
                    Assert.Fail($"Failed to parse test bundle: {ex.Message}");
                }
            }
            else
            {
                Assert.Fail($"Test bundle file not found: {testBundlePath}");
            }
        }
    }
}
