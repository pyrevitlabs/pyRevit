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

        [Test]
        public void TestPulldownComponentParsing()
        {
            // Find the test extension directory in Resources
            var possibleExtensionPaths = new[]
            {
                @"Resources\TestBundleExtension.extension",
                Path.Combine("Resources", "TestBundleExtension.extension"),
                Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension"),
                Path.Combine(Directory.GetCurrentDirectory(), "Resources", "TestBundleExtension.extension")
            };

            string testExtensionPath = null;
            foreach (var path in possibleExtensionPaths)
            {
                if (Directory.Exists(path))
                {
                    testExtensionPath = path;
                    break;
                }
            }

            if (testExtensionPath != null)
            {
                try
                {
                    // Parse the test extension manually since there's no direct ParseExtension method
                    var extName = Path.GetFileNameWithoutExtension(testExtensionPath);
                    var children = ParseTestComponents(testExtensionPath, extName);

                    var bundlePath = Path.Combine(testExtensionPath, "bundle.yaml");
                    var parsedBundle = File.Exists(bundlePath)
                        ? BundleParser.BundleYamlParser.Parse(bundlePath)
                        : null;

                    var parsedExtension = new ParsedExtension
                    {
                        Name = extName,
                        Directory = testExtensionPath,
                        Children = children,
                        LayoutOrder = parsedBundle?.LayoutOrder,
                        Titles = parsedBundle?.Titles,
                        Tooltips = parsedBundle?.Tooltips,
                        MinRevitVersion = parsedBundle?.MinRevitVersion,
                        Engine = parsedBundle?.Engine
                    };
                    
                    TestContext.Out.WriteLine($"=== Testing Pulldown Component in {parsedExtension.Name} ===");
                    TestContext.Out.WriteLine($"Extension Path: {testExtensionPath}");
                    
                    var pulldownComponent = FindComponentRecursively(parsedExtension, "TestPulldown");
                    if (pulldownComponent != null)
                    {
                        TestContext.Out.WriteLine($"Found pulldown component: {pulldownComponent.Name}");
                        TestContext.Out.WriteLine($"Display Name: {pulldownComponent.DisplayName}");
                        TestContext.Out.WriteLine($"Type: {pulldownComponent.Type}");
                        TestContext.Out.WriteLine($"Tooltip: '{pulldownComponent.Tooltip ?? "NULL"}'");
                        TestContext.Out.WriteLine($"Bundle File: {pulldownComponent.BundleFile ?? "NULL"}");
                        TestContext.Out.WriteLine($"Title: {pulldownComponent.Title ?? "NULL"}");
                        
                        // Verify the component was parsed correctly
                        Assert.AreEqual(CommandComponentType.PullDown, pulldownComponent.Type, "Component should be PullDown type");
                        Assert.IsNotNull(pulldownComponent.Tooltip, "Tooltip should not be null");
                        Assert.IsTrue(pulldownComponent.Tooltip.Contains("test tooltip for the pulldown button"), 
                                     $"Tooltip should contain expected text, but was: '{pulldownComponent.Tooltip}'");
                        
                        // Check child components
                        if (pulldownComponent.Children != null && pulldownComponent.Children.Count > 0)
                        {
                            TestContext.Out.WriteLine($"Child components count: {pulldownComponent.Children.Count}");
                            foreach (var child in pulldownComponent.Children)
                            {
                                TestContext.Out.WriteLine($"  Child: {child.Name} - {child.DisplayName} - Tooltip: '{child.Tooltip ?? "NULL"}'");
                            }
                        }
                        
                        Assert.Pass("Pulldown component parsing test completed successfully.");
                    }
                    else
                    {
                        Assert.Fail("TestPulldown component not found in parsed extension");
                    }
                }
                catch (Exception ex)
                {
                    Assert.Fail($"Failed to parse test extension: {ex.Message}");
                }
            }
            else
            {
                // Show what paths were tried for debugging
                TestContext.Out.WriteLine("Attempted extension paths:");
                foreach (var path in possibleExtensionPaths)
                {
                    TestContext.Out.WriteLine($"  {path} - Exists: {Directory.Exists(path)}");
                }
                TestContext.Out.WriteLine($"Current Directory: {Directory.GetCurrentDirectory()}");
                TestContext.Out.WriteLine($"Test Directory: {TestContext.CurrentContext.TestDirectory}");
                
                Assert.Fail("TestBundleExtension directory not found in any expected location");
            }
        }

        // Helper method to parse components similar to the ExtensionParser's ParseComponents method
        private List<ParsedComponent> ParseTestComponents(string baseDir, string extensionName, string parentPath = null)
        {
            var components = new List<ParsedComponent>();

            foreach (var dir in Directory.GetDirectories(baseDir))
            {
                var ext = Path.GetExtension(dir);
                var componentType = CommandComponentTypeExtensions.FromExtension(ext);
                if (componentType == CommandComponentType.Unknown)
                    continue;

                var namePart = Path.GetFileNameWithoutExtension(dir).Replace(" ", "");
                var displayName = Path.GetFileNameWithoutExtension(dir);
                var fullPath = string.IsNullOrEmpty(parentPath)
                    ? $"{extensionName}_{namePart}"
                    : $"{parentPath}_{namePart}";

                string scriptPath = null;

                if (componentType == CommandComponentType.UrlButton)
                {
                    var yaml = Path.Combine(dir, "bundle.yaml");
                    if (File.Exists(yaml))
                        scriptPath = yaml;
                }

                if (scriptPath == null)
                {
                    scriptPath = Directory
                        .EnumerateFiles(dir, "*", SearchOption.TopDirectoryOnly)
                        .FirstOrDefault(f => f.EndsWith("script.py", StringComparison.OrdinalIgnoreCase));
                }

                if (scriptPath == null &&
                   (componentType == CommandComponentType.PushButton ||
                    componentType == CommandComponentType.SmartButton ||
                    componentType == CommandComponentType.PullDown ||
                    componentType == CommandComponentType.SplitButton ||
                    componentType == CommandComponentType.SplitPushButton))
                {
                    var yaml = Path.Combine(dir, "bundle.yaml");
                    if (File.Exists(yaml))
                        scriptPath = yaml;
                }

                var bundleFile = Path.Combine(dir, "bundle.yaml");
                var children = ParseTestComponents(dir, extensionName, fullPath);

                // First, get values from Python script
                string title = null, author = null, doc = null;
                if (scriptPath != null && scriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase))
                {
                    (title, author, doc) = ReadPythonScriptConstants(scriptPath);
                }

                // Then parse bundle and override with bundle values if they exist
                var bundleInComponent = File.Exists(bundleFile) ? BundleParser.BundleYamlParser.Parse(bundleFile) : null;
                
                // Override script values with bundle values (bundle takes precedence)
                if (bundleInComponent != null)
                {
                    // Use en_us as default locale, fallback to first available, then to script values
                    var bundleTitle = GetLocalizedValue(bundleInComponent.Titles, "en_us");
                    var bundleTooltip = GetLocalizedValue(bundleInComponent.Tooltips, "en_us");
                    
                    if (!string.IsNullOrEmpty(bundleTitle))
                        title = bundleTitle;
                    
                    if (!string.IsNullOrEmpty(bundleTooltip))
                        doc = bundleTooltip;
                        
                    if (!string.IsNullOrEmpty(bundleInComponent.Author))
                        author = bundleInComponent.Author;
                }

                components.Add(new ParsedComponent
                {
                    Name = namePart,
                    DisplayName = displayName,
                    ScriptPath = scriptPath,
                    Tooltip = doc ?? $"Command: {namePart}", // Set Tooltip from bundle -> __doc__ -> fallback
                    UniqueId = SanitizeClassName(fullPath.ToLowerInvariant()),
                    Type = componentType,
                    Children = children,
                    BundleFile = File.Exists(bundleFile) ? bundleFile : null,
                    LayoutOrder = bundleInComponent?.LayoutOrder,
                    Title = title,
                    Author = author
                });
            }

            return components;
        }

        // Helper methods copied from ExtensionParser
        private static string GetLocalizedValue(Dictionary<string, string> localizedValues, string preferredLocale = "en_us")
        {
            if (localizedValues == null || localizedValues.Count == 0)
                return null;

            if (localizedValues.TryGetValue(preferredLocale, out string preferredValue))
                return preferredValue;

            if (preferredLocale != "en_us" && localizedValues.TryGetValue("en_us", out string enUsValue))
                return enUsValue;

            return localizedValues.Values.FirstOrDefault();
        }

        private static string SanitizeClassName(string name)
        {
            var sb = new System.Text.StringBuilder();
            foreach (char c in name)
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            return sb.ToString();
        }

        private static (string title, string author, string doc) ReadPythonScriptConstants(string scriptPath)
        {
            string title = null, author = null, doc = null;

            foreach (var line in File.ReadLines(scriptPath))
            {
                if (line.StartsWith("__title__"))
                {
                    title = ExtractPythonConstantValue(line);
                }
                else if (line.StartsWith("__author__"))
                {
                    author = ExtractPythonConstantValue(line);
                }
                else if (line.StartsWith("__doc__"))
                {
                    doc = ExtractPythonConstantValue(line);
                }
            }

            return (title, author, doc);
        }

        private static string ExtractPythonConstantValue(string line)
        {
            var parts = line.Split(new[] { '=' }, 2, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 2)
            {
                var value = parts[1].Trim().Trim('\'', '"');
                return value;
            }
            return null;
        }

        private ParsedComponent FindComponentRecursively(ParsedComponent parent, string componentName)
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
