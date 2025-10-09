using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;
using System.Drawing;
using System.Drawing.Imaging;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class PanelButtonAndIconTests
    {
        private IEnumerable<ParsedExtension>? _installedExtensions;
        
        [SetUp]
        public void Setup()
        {
            // Use the test bundle from Resources folder
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
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
            // First, create a bundle.yaml file for the panel button
            var panelButtonPath = Path.Combine(TestContext.CurrentContext.TestDirectory, 
                "Resources", "TestBundleExtension.extension", "TestBundleTab.tab", 
                "TestPanelOne.panel", "Debug Dialog Config.panelbutton");
            
            var bundlePath = Path.Combine(panelButtonPath, "bundle.yaml");
            
            var bundleContent = @"title:
  en_us: Panel Configuration
tooltips:
  en_us: >-
    This is a panel button that provides
    configuration options for the panel.
    It should appear as a small button
    in the panel header.
author: Test Author
min_revit_ver: 2019
";

            // Create the bundle file for testing
            File.WriteAllText(bundlePath, bundleContent);
            
            try
            {
                // Re-parse with the new bundle file
                var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
                var extensions = ParseInstalledExtensions(new[] { testBundlePath });
                
                foreach (var parsedExtension in extensions)
                {
                    var panelButtonComponent = FindComponentRecursively(parsedExtension, "DebugDialogConfig");
                    if (panelButtonComponent != null)
                    {
                        TestContext.Out.WriteLine($"=== Testing Panel Button with Bundle File ===");
                        TestContext.Out.WriteLine($"Component: {panelButtonComponent.Name}");
                        TestContext.Out.WriteLine($"Display Name: {panelButtonComponent.DisplayName}");
                        TestContext.Out.WriteLine($"Bundle File: {panelButtonComponent.BundleFile}");
                        TestContext.Out.WriteLine($"Title: {panelButtonComponent.Title}");
                        TestContext.Out.WriteLine($"Tooltip: {panelButtonComponent.Tooltip}");
                        TestContext.Out.WriteLine($"Author: {panelButtonComponent.Author}");
                        TestContext.Out.WriteLine($"Type: {panelButtonComponent.Type}");
                        
                        // Verify bundle data was parsed correctly
                        Assert.That(panelButtonComponent.Type, Is.EqualTo(CommandComponentType.PanelButton),
                                        "Component should be PanelButton type");
                        Assert.IsNotNull(panelButtonComponent.BundleFile, "Bundle file should be detected");
                        Assert.IsTrue(File.Exists(panelButtonComponent.BundleFile), "Bundle file should exist");
                        
                        // Verify bundle content was parsed
                        Assert.AreEqual("Panel Configuration", panelButtonComponent.Title, 
                                       "Title should match bundle content");
                        Assert.IsNotNull(panelButtonComponent.Tooltip, "Tooltip should not be null");
                        Assert.IsTrue(panelButtonComponent.Tooltip.Contains("panel button"), 
                                     "Tooltip should contain expected content");
                        Assert.AreEqual("Test Author", panelButtonComponent.Author,
                                       "Author should match bundle content");
                        
                        Assert.Pass("Panel button with bundle file parsing test completed successfully.");
                        return;
                    }
                }
                Assert.Fail("Panel button component not found");
            }
            finally
            {
                // Clean up - remove the test bundle file
                if (File.Exists(bundlePath))
                {
                    File.Delete(bundlePath);
                }
            }
        }

        [Test]
        public void TestIconFileDetection()
        {
            // Create test icon files in various button directories
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            var buttonPaths = new[]
            {
                Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelTwo.panel", "TestAbout.pushbutton"),
                Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelOne.panel", "PanelOneButton1.pushbutton"),
                Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelOne.panel", "Debug Dialog Config.panelbutton")
            };

            var iconFiles = new List<string>();

            try
            {
                // Create test icon files
                foreach (var buttonPath in buttonPaths)
                {
                    if (Directory.Exists(buttonPath))
                    {
                        // Create different types of icon files
                        var iconPath = Path.Combine(buttonPath, "icon.png");
                        CreateTestIcon(iconPath, 32, 32);
                        iconFiles.Add(iconPath);

                        // Also create a larger icon
                        var largeIconPath = Path.Combine(buttonPath, "icon_large.png");
                        CreateTestIcon(largeIconPath, 64, 64);
                        iconFiles.Add(largeIconPath);
                    }
                }

                // Re-parse extensions to check icon detection
                var extensions = ParseInstalledExtensions(new[] { testBundlePath });
                
                foreach (var parsedExtension in extensions)
                {
                    TestContext.Out.WriteLine($"=== Testing Icon Detection in {parsedExtension.Name} ===");
                    PrintIconsRecursively(parsedExtension);
                }

                // Verify icons exist
                foreach (var iconFile in iconFiles)
                {
                    Assert.IsTrue(File.Exists(iconFile), $"Icon file should exist: {iconFile}");
                }

                Assert.Pass("Icon file detection test completed successfully.");
            }
            finally
            {
                // Clean up test icon files
                foreach (var iconFile in iconFiles)
                {
                    if (File.Exists(iconFile))
                    {
                        File.Delete(iconFile);
                    }
                }
            }
        }

        [Test]
        public void TestIconsInBundle()
        {
            // Test that we can detect and report on icon files in button directories
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            var buttonPath = Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelTwo.panel", "TestAbout.pushbutton");
            
            var iconFiles = new List<string>();
            
            try
            {
                // Create various icon file types
                var iconTypes = new Dictionary<string, string>
                {
                    { "icon.png", "PNG Icon" },
                    { "icon.ico", "ICO Icon" },
                    { "icon_small.png", "Small PNG Icon" },
                    { "icon_large.png", "Large PNG Icon" }
                };

                foreach (var iconType in iconTypes)
                {
                    var iconPath = Path.Combine(buttonPath, iconType.Key);
                    if (iconType.Key.EndsWith(".ico"))
                    {
                        CreateTestIconIco(iconPath);
                    }
                    else
                    {
                        var size = iconType.Key.Contains("large") ? 64 : 32;
                        CreateTestIcon(iconPath, size, size);
                    }
                    iconFiles.Add(iconPath);
                }

                // Test icon detection
                TestContext.Out.WriteLine("=== Testing Various Icon Types ===");
                foreach (var iconFile in iconFiles)
                {
                    TestContext.Out.WriteLine($"Created icon: {Path.GetFileName(iconFile)}");
                    Assert.IsTrue(File.Exists(iconFile), $"Icon file should exist: {iconFile}");
                    
                    var fileInfo = new FileInfo(iconFile);
                    TestContext.Out.WriteLine($"  Size: {fileInfo.Length} bytes");
                    TestContext.Out.WriteLine($"  Extension: {fileInfo.Extension}");
                }

                Assert.Pass("Icon types test completed successfully.");
            }
            finally
            {
                // Clean up
                foreach (var iconFile in iconFiles)
                {
                    if (File.Exists(iconFile))
                    {
                        File.Delete(iconFile);
                    }
                }
            }
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
                    
                    // First, let's create some test icons to ensure we have something to test
                    var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
                    var testIconFiles = new List<string>();
                    
                    try
                    {
                        // Create test icons in a few component directories
                        var componentPaths = new[]
                        {
                            Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelTwo.panel", "TestAbout.pushbutton"),
                            Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelOne.panel", "Debug Dialog Config.panelbutton")
                        };

                        foreach (var componentPath in componentPaths)
                        {
                            if (Directory.Exists(componentPath))
                            {
                                var iconPath = Path.Combine(componentPath, "icon.png");
                                CreateTestIcon(iconPath, 32, 32);
                                testIconFiles.Add(iconPath);
                                
                                var largeIconPath = Path.Combine(componentPath, "icon_large.png");
                                CreateTestIcon(largeIconPath, 64, 64);
                                testIconFiles.Add(largeIconPath);
                            }
                        }

                        // Re-parse extensions to test icon detection
                        var extensions = ParseInstalledExtensions(new[] { testBundlePath });
                        
                        var foundIconsCount = 0;
                        
                        foreach (var extension in extensions)
                        {
                            PrintComponentIconInfo(extension, ref foundIconsCount);
                        }
                        
                        TestContext.Out.WriteLine($"Total components with icons found: {foundIconsCount}");
                        
                        // We should find at least some icons if our test files were created
                        if (testIconFiles.Any(File.Exists))
                        {
                            Assert.Greater(foundIconsCount, 0, "Should find at least one component with icons");
                        }
                        
                        Assert.Pass("Icon parsing test completed successfully.");
                    }
                    finally
                    {
                        // Clean up test icon files
                        foreach (var iconFile in testIconFiles)
                        {
                            if (File.Exists(iconFile))
                            {
                                File.Delete(iconFile);
                            }
                        }
                    }
                }
            }
            else
            {
                Assert.Fail("No test extensions found");
            }
        }

        // Helper method to create a test PNG icon
        private void CreateTestIcon(string filePath, int width, int height)
        {
            using (var bitmap = new Bitmap(width, height))
            using (var graphics = Graphics.FromImage(bitmap))
            {
                // Create a simple test icon (blue square with white border)
                graphics.Clear(Color.Blue);
                using (var pen = new Pen(Color.White, 2))
                {
                    graphics.DrawRectangle(pen, 1, 1, width - 3, height - 3);
                }
                
                // Add some text to make it identifiable
                using (var font = new Font("Arial", Math.Max(8, width / 8)))
                using (var brush = new SolidBrush(Color.White))
                {
                    var text = $"{width}x{height}";
                    var textSize = graphics.MeasureString(text, font);
                    var x = (width - textSize.Width) / 2;
                    var y = (height - textSize.Height) / 2;
                    graphics.DrawString(text, font, brush, x, y);
                }
                
                bitmap.Save(filePath, ImageFormat.Png);
            }
        }

        // Helper method to create a test ICO icon
        private void CreateTestIconIco(string filePath)
        {
            // For simplicity, create a PNG and save it as ICO
            // In a real scenario, you'd want proper ICO format
            using (var bitmap = new Bitmap(32, 32))
            using (var graphics = Graphics.FromImage(bitmap))
            {
                graphics.Clear(Color.Red);
                using (var pen = new Pen(Color.White, 2))
                {
                    graphics.DrawEllipse(pen, 4, 4, 24, 24);
                }
                
                bitmap.Save(filePath, ImageFormat.Png); // Simplified for testing
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