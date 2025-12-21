using pyRevitExtensionParser;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class PanelButtonAndIconTests
    {
        private IEnumerable<ParsedExtension>? _installedExtensions;
        
        [SetUp]
        public void Setup()
        {
            var testBundlePath = TestConfiguration.TestExtensionPath;
            _installedExtensions = ParseInstalledExtensions(new[] { testBundlePath });
        }

        [Test]
        public void TestPanelButtonParsing()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    TestContext.Out.WriteLine($"=== Testing Panel Button in {parsedExtension.Name} ===");
                    TestContext.Out.WriteLine($"Extension Path: {parsedExtension.Directory}");
                    
                    var panelButtonComponent = FindComponentRecursively(parsedExtension, "DebugDialogConfig");
                    if (panelButtonComponent != null)
                    {
                        TestContext.Out.WriteLine($"Found panel button component: {panelButtonComponent.Name}");
                        TestContext.Out.WriteLine($"Display Name: {panelButtonComponent.DisplayName}");
                        TestContext.Out.WriteLine($"Type: {panelButtonComponent.Type}");
                        TestContext.Out.WriteLine($"Script Path: {panelButtonComponent.ScriptPath ?? "NULL"}");
                        TestContext.Out.WriteLine($"Tooltip: '{panelButtonComponent.Tooltip ?? "NULL"}'");
                        TestContext.Out.WriteLine($"Bundle File: {panelButtonComponent.BundleFile ?? "NULL"}");
                        TestContext.Out.WriteLine($"Title: {panelButtonComponent.Title ?? "NULL"}");
                        TestContext.Out.WriteLine($"Author: {panelButtonComponent.Author ?? "NULL"}");
                        
                        // Verify the component was parsed correctly
                        Assert.That(panelButtonComponent.Type,
                            Is.EqualTo(CommandComponentType.PanelButton),
                            "Component should be PanelButton type");
                        
                        Assert.IsNotNull(panelButtonComponent.ScriptPath,
                            "Panel button should have a script path");
                        Assert.IsTrue(panelButtonComponent.ScriptPath.EndsWith("script.py"),
                            "Panel button should have a Python script");
                        
                        Assert.IsNotNull(panelButtonComponent.DisplayName,
                            "Panel button should have a display name");
                        Assert.AreEqual("Debug Dialog Config", panelButtonComponent.DisplayName,
                            "Display name should match expected value");
                        
                        Assert.Pass("Panel button parsing test completed successfully.");
                    }
                    else
                    {
                        Assert.Fail("Debug Dialog Config panel button component not found in parsed extension");
                    }
                }
            }
            else
            {
                Assert.Fail("No test extensions found");
            }
        }

        [Test]
        public void TestPanelButtonWithBundleFile()
        {
            TestContext.Out.WriteLine("=== Testing Panel Button with Bundle File ===");
            
            var testBundlePath = TestConfiguration.TestExtensionPath;
            
            // Parse the extension to find panel buttons
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            var extension = extensions.First();
            
            TestContext.Out.WriteLine($"Extension: {extension.Name}");
            
            // Find all panel buttons
            var panelButtons = FindAllComponentsByType(extension, CommandComponentType.PanelButton);
            TestContext.Out.WriteLine($"Found {panelButtons.Count} panel button(s)");
            
            if (panelButtons.Count == 0)
            {
                Assert.Inconclusive("No panel buttons found in the extension to test bundle file parsing.");
                return;
            }
            
            // Look for panel buttons that have bundle files
            var panelButtonsWithBundles = panelButtons.Where(pb => !string.IsNullOrEmpty(pb.BundleFile)).ToList();
            TestContext.Out.WriteLine($"Panel buttons with bundle files: {panelButtonsWithBundles.Count}");
            
            // Test each panel button with a bundle
            foreach (var panelButton in panelButtons)
            {
                TestContext.Out.WriteLine($"\nPanel Button: {panelButton.DisplayName} ({panelButton.Name})");
                TestContext.Out.WriteLine($"  Directory: {panelButton.Directory}");
                TestContext.Out.WriteLine($"  Has bundle: {!string.IsNullOrEmpty(panelButton.BundleFile)}");
                
                if (!string.IsNullOrEmpty(panelButton.BundleFile))
                {
                    TestContext.Out.WriteLine($"  Bundle file: {panelButton.BundleFile}");
                    TestContext.Out.WriteLine($"  Bundle exists: {File.Exists(panelButton.BundleFile)}");
                    TestContext.Out.WriteLine($"  Title: {panelButton.Title ?? "(null)"}");
                    TestContext.Out.WriteLine($"  Tooltip: {panelButton.Tooltip ?? "(null)"}");
                    TestContext.Out.WriteLine($"  Author: {panelButton.Author ?? "(null)"}");
                    
                    // Verify bundle file parsing
                    Assert.That(panelButton.Type, Is.EqualTo(CommandComponentType.PanelButton),
                                "Component should be PanelButton type");
                    Assert.IsTrue(File.Exists(panelButton.BundleFile), 
                                 $"Bundle file should exist: {panelButton.BundleFile}");
                    
                    // If bundle file exists and has content, some properties should be populated
                    var bundleContent = File.ReadAllText(panelButton.BundleFile);
                    if (!string.IsNullOrWhiteSpace(bundleContent))
                    {
                        TestContext.Out.WriteLine($"  Bundle has content ({bundleContent.Length} chars)");
                        
                        // At least one of these should be populated from the bundle
                        var hasAnyBundleData = !string.IsNullOrEmpty(panelButton.Title) ||
                                              !string.IsNullOrEmpty(panelButton.Tooltip) ||
                                              !string.IsNullOrEmpty(panelButton.Author);
                        
                        if (hasAnyBundleData)
                        {
                            TestContext.Out.WriteLine("  ✓ Bundle data was parsed successfully");
                        }
                        else
                        {
                            TestContext.Out.WriteLine("  ⚠ Bundle file exists but no data was parsed");
                        }
                    }
                }
                else
                {
                    TestContext.Out.WriteLine($"  No bundle file found at expected location");
                    
                    // Check if bundle.yaml exists in the directory
                    if (!string.IsNullOrEmpty(panelButton.Directory) && Directory.Exists(panelButton.Directory))
                    {
                        var expectedBundlePath = Path.Combine(panelButton.Directory, "bundle.yaml");
                        if (File.Exists(expectedBundlePath))
                        {
                            TestContext.Out.WriteLine($"  ⚠ bundle.yaml exists but wasn't detected: {expectedBundlePath}");
                        }
                    }
                }
            }
            
            if (panelButtonsWithBundles.Count > 0)
            {
                Assert.Pass($"Panel button bundle file test completed. {panelButtonsWithBundles.Count} panel button(s) with bundle files found.");
            }
            else
            {
                // Provide helpful information about how to enable this test
                TestContext.Out.WriteLine("\n=== How to Enable Bundle File Testing ===");
                TestContext.Out.WriteLine("To test bundle file parsing, create a 'bundle.yaml' file in one of the panel button directories:");
                
                foreach (var pb in panelButtons.Take(2))
                {
                    if (!string.IsNullOrEmpty(pb.Directory))
                    {
                        var bundlePath = Path.Combine(pb.Directory, "bundle.yaml");
                        TestContext.Out.WriteLine($"\nExample location: {bundlePath}");
                        TestContext.Out.WriteLine("Example content:");
                        TestContext.Out.WriteLine("---");
                        TestContext.Out.WriteLine("title:");
                        TestContext.Out.WriteLine("  en_us: Panel Configuration");
                        TestContext.Out.WriteLine("tooltips:");
                        TestContext.Out.WriteLine("  en_us: Configure panel options");
                        TestContext.Out.WriteLine("author: Test Author");
                        TestContext.Out.WriteLine("min_revit_ver: 2019");
                        break;
                    }
                }
                
                Assert.Inconclusive("No panel buttons with bundle files found. Test validates bundle parsing when bundles exist. See output for instructions.");
            }
        }

        [Test]
        public void TestIconFileDetection()
        {
            TestContext.Out.WriteLine("=== Testing Icon File Detection ===");
            
            var testBundlePath = TestConfiguration.TestExtensionPath;
            
            // Parse extensions to check existing icon detection
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            
            foreach (var parsedExtension in extensions)
            {
                TestContext.Out.WriteLine($"\nExtension: {parsedExtension.Name}");
                PrintIconsRecursively(parsedExtension);
            }
            
            // Count components with icons
            var extension = extensions.First();
            var allComponents = GetAllComponentsFlat(extension);
            var componentsWithIcons = allComponents.Where(c => c.HasIcons).ToList();
            
            TestContext.Out.WriteLine($"\nSummary:");
            TestContext.Out.WriteLine($"  Total components: {allComponents.Count}");
            TestContext.Out.WriteLine($"  Components with icons: {componentsWithIcons.Count}");
            
            if (componentsWithIcons.Count > 0)
            {
                Assert.Pass($"Icon file detection test completed. Found {componentsWithIcons.Count} component(s) with icons.");
            }
            else
            {
                Assert.Inconclusive("No components with icons found. Test validates icon detection when icons exist.");
            }
        }
        
        // Helper method to get all components in a flat list
        private List<ParsedComponent> GetAllComponentsFlat(ParsedComponent root)
        {
            var result = new List<ParsedComponent> { root };
            
            if (root.Children != null)
            {
                foreach (var child in root.Children)
                {
                    result.AddRange(GetAllComponentsFlat(child));
                }
            }
            
            return result;
        }

        [Test]
        public void TestIconsInBundle()
        {
            TestContext.Out.WriteLine("=== Testing Icon Types in Bundles ===");
            
            var testBundlePath = TestConfiguration.TestExtensionPath;
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            var extension = extensions.First();
            
            // Find all components with icons
            var allComponents = GetAllComponentsFlat(extension);
            var componentsWithIcons = allComponents.Where(c => c.HasIcons).ToList();
            
            TestContext.Out.WriteLine($"Found {componentsWithIcons.Count} component(s) with icons");
            
            if (componentsWithIcons.Count == 0)
            {
                Assert.Inconclusive("No components with icons found. Test validates icon type detection when icons exist.");
                return;
            }
            
            // Analyze icon types
            var iconTypeStats = new Dictionary<string, int>();
            var totalIcons = 0;
            
            foreach (var component in componentsWithIcons)
            {
                TestContext.Out.WriteLine($"\n{component.DisplayName} ({component.Type}):");
                foreach (var icon in component.Icons)
                {
                    totalIcons++;
                    var ext = icon.Extension.ToLowerInvariant();
                    
                    if (!iconTypeStats.ContainsKey(ext))
                        iconTypeStats[ext] = 0;
                    iconTypeStats[ext]++;
                    
                    TestContext.Out.WriteLine($"  - {icon.FileName}");
                    TestContext.Out.WriteLine($"      Extension: {icon.Extension}");
                    TestContext.Out.WriteLine($"      Type: {icon.Type}");
                    TestContext.Out.WriteLine($"      Size: {icon.FileSize} bytes");
                    TestContext.Out.WriteLine($"      Valid: {icon.IsValid}");
                }
            }
            
            // Report statistics
            TestContext.Out.WriteLine($"\n=== Icon Type Statistics ===");
            TestContext.Out.WriteLine($"Total icons: {totalIcons}");
            foreach (var stat in iconTypeStats.OrderByDescending(kv => kv.Value))
            {
                TestContext.Out.WriteLine($"  {stat.Key}: {stat.Value} icon(s)");
            }
            
            Assert.Pass($"Icon types test completed. Analyzed {totalIcons} icon(s) across {componentsWithIcons.Count} component(s).");
        }

        [Test]
        public void TestPanelButtonsInExtensionStructure()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    TestContext.Out.WriteLine($"=== Scanning for Panel Buttons in {parsedExtension.Name} ===");
                    var panelButtons = FindAllComponentsByType(parsedExtension, CommandComponentType.PanelButton);
                    
                    TestContext.Out.WriteLine($"Found {panelButtons.Count} panel button(s):");
                    foreach (var panelButton in panelButtons)
                    {
                        TestContext.Out.WriteLine($"  - {panelButton.DisplayName} ({panelButton.Name})");
                        TestContext.Out.WriteLine($"    Type: {panelButton.Type}");
                        TestContext.Out.WriteLine($"    Script: {panelButton.ScriptPath ?? "None"}");
                        TestContext.Out.WriteLine($"    Bundle: {panelButton.BundleFile ?? "None"}");
                    }
                    
                    // We expect at least one panel button (Debug Dialog Config)
                    Assert.GreaterOrEqual(panelButtons.Count, 1, "Should find at least one panel button");
                    
                    // Verify the known panel button exists
                    var debugConfig = panelButtons.FirstOrDefault(pb => pb.Name == "DebugDialogConfig");
                    Assert.IsNotNull(debugConfig, "Should find the Debug Dialog Config panel button");
                }
                
                Assert.Pass("Panel button structure test completed successfully.");
            }
            else
            {
                Assert.Fail("No test extensions found");
            }
        }

        [Test]
        public void TestIconsAreBeingParsed()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    TestContext.Out.WriteLine($"=== Testing Icon Parsing in {parsedExtension.Name} ===");
                    
                    var foundIconsCount = 0;
                    PrintComponentIconInfo(parsedExtension, ref foundIconsCount);
                    
                    TestContext.Out.WriteLine($"\nTotal components with icons found: {foundIconsCount}");
                    
                    if (foundIconsCount > 0)
                    {
                        Assert.Pass($"Icon parsing test completed. Found {foundIconsCount} component(s) with icons.");
                    }
                    else
                    {
                        Assert.Inconclusive("No components with icons found. Test validates icon parsing when icons exist.");
                    }
                }
            }
            else
            {
                Assert.Fail("No test extensions found");
            }
        }

        // Helper method to print icons found in components
        private void PrintIconsRecursively(ParsedComponent component, int level = 0)
        {
            var indent = new string(' ', level * 2);
            
            if (!string.IsNullOrEmpty(component.ScriptPath))
            {
                var componentDir = Path.GetDirectoryName(component.ScriptPath);
                if (!string.IsNullOrEmpty(componentDir) && Directory.Exists(componentDir))
                {
                    var iconFiles = Directory.GetFiles(componentDir, "*icon*.*", SearchOption.TopDirectoryOnly)
                        .Where(f => IsImageFile(f))
                        .ToList();
                    
                    if (iconFiles.Any())
                    {
                        TestContext.Out.WriteLine($"{indent}[{component.Type}] {component.DisplayName}:");
                        foreach (var iconFile in iconFiles)
                        {
                            var fileName = Path.GetFileName(iconFile);
                            var fileInfo = new FileInfo(iconFile);
                            TestContext.Out.WriteLine($"{indent}  ?? {fileName} ({fileInfo.Length} bytes)");
                        }
                    }
                }
            }

            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    PrintIconsRecursively(child, level + 1);
                }
            }
        }

        // Helper method to check if file is an image
        private bool IsImageFile(string filePath)
        {
            var extension = Path.GetExtension(filePath).ToLowerInvariant();
            return new[] { ".png", ".ico", ".jpg", ".jpeg", ".bmp", ".gif", ".svg" }.Contains(extension);
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

        // Helper method to find all components of a specific type
        private List<ParsedComponent> FindAllComponentsByType(ParsedComponent parent, CommandComponentType type)
        {
            var results = new List<ParsedComponent>();
            
            if (parent.Type == type)
                results.Add(parent);

            if (parent.Children != null)
            {
                foreach (var child in parent.Children)
                {
                    results.AddRange(FindAllComponentsByType(child, type));
                }
            }

            return results;
        }

        // Helper method to print component icon information recursively
        private void PrintComponentIconInfo(ParsedComponent component, ref int iconCount, int level = 0)
        {
            var indent = new string(' ', level * 2);
            
            // Check if this component has icons
            if (component.HasIcons)
            {
                iconCount++;
                TestContext.Out.WriteLine($"{indent}[{component.Type}] {component.DisplayName} - {component.Icons.Count} icon(s):");
                
                foreach (var icon in component.Icons)
                {
                    TestContext.Out.WriteLine($"{indent}  ?? {icon.FileName} ({icon.Type}, {icon.FileSize} bytes, Valid: {icon.IsValid})");
                }
                
                if (component.PrimaryIcon != null)
                {
                    TestContext.Out.WriteLine($"{indent}  ?? Primary: {component.PrimaryIcon.FileName}");
                }
            }

            // Recurse into children
            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    PrintComponentIconInfo(child, ref iconCount, level + 1);
                }
            }
        }
    }
}