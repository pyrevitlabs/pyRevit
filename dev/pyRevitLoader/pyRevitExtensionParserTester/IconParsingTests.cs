using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class IconParsingTests
    {
        private IEnumerable<ParsedExtension>? _installedExtensions;
        private List<string> _createdTestFiles = new List<string>();
        
        [SetUp]
        public void Setup()
        {
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            _installedExtensions = ParseInstalledExtensions(new[] { testBundlePath });
        }

        [TearDown]
        public void TearDown()
        {
            // Clean up any test files we created
            foreach (var file in _createdTestFiles)
            {
                if (File.Exists(file))
                {
                    try
                    {
                        File.Delete(file);
                    }
                    catch
                    {
                        // Ignore cleanup errors
                    }
                }
            }
            _createdTestFiles.Clear();
        }

        [Test]
        public void TestIconFileDiscovery()
        {
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            
            // Create test icon files in button directories
            var buttonDirectories = new[]
            {
                Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelTwo.panel", "TestAbout.pushbutton"),
                Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelOne.panel", "PanelOneButton1.pushbutton"),
                Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelOne.panel", "PanelOneButton2.pushbutton")
            };

            // Create different types of icon files
            var iconFileNames = new[] { "icon.png", "icon.ico", "icon_small.png", "icon_large.png" };
            
            foreach (var buttonDir in buttonDirectories)
            {
                if (Directory.Exists(buttonDir))
                {
                    foreach (var iconFileName in iconFileNames)
                    {
                        var iconPath = Path.Combine(buttonDir, iconFileName);
                        CreateSimpleTestFile(iconPath, "Test icon content");
                        _createdTestFiles.Add(iconPath);
                    }
                }
            }

            // Test icon discovery
            TestContext.Out.WriteLine("=== Icon File Discovery Test ===");
            foreach (var buttonDir in buttonDirectories)
            {
                if (Directory.Exists(buttonDir))
                {
                    var buttonName = Path.GetFileName(buttonDir);
                    TestContext.Out.WriteLine($"Button: {buttonName}");
                    
                    var iconFiles = Directory.GetFiles(buttonDir, "*icon*.*", SearchOption.TopDirectoryOnly);
                    TestContext.Out.WriteLine($"  Found {iconFiles.Length} icon file(s):");
                    
                    foreach (var iconFile in iconFiles)
                    {
                        var fileName = Path.GetFileName(iconFile);
                        var fileInfo = new FileInfo(iconFile);
                        TestContext.Out.WriteLine($"    - {fileName} ({fileInfo.Length} bytes)");
                        
                        // Verify file exists and has content
                        Assert.IsTrue(File.Exists(iconFile), $"Icon file should exist: {fileName}");
                        Assert.Greater(fileInfo.Length, 0, $"Icon file should have content: {fileName}");
                    }
                }
            }

            Assert.Pass("Icon file discovery test completed successfully.");
        }

        [Test]
        public void TestIconFileTypes()
        {
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            var buttonDir = Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelTwo.panel", "TestAbout.pushbutton");
            
            if (!Directory.Exists(buttonDir))
            {
                Assert.Inconclusive($"Test button directory does not exist: {buttonDir}");
                return;
            }

            // Test various icon file extensions
            var iconTypes = new Dictionary<string, string>
            {
                { ".png", "PNG image" },
                { ".ico", "Windows icon" },
                { ".jpg", "JPEG image" },
                { ".jpeg", "JPEG image" },
                { ".bmp", "Bitmap image" },
                { ".svg", "SVG vector image" }
            };

            TestContext.Out.WriteLine("=== Testing Icon File Types ===");
            
            foreach (var iconType in iconTypes)
            {
                var iconFileName = $"test_icon{iconType.Key}";
                var iconPath = Path.Combine(buttonDir, iconFileName);
                
                CreateSimpleTestFile(iconPath, $"Test {iconType.Value} content");
                _createdTestFiles.Add(iconPath);
                
                TestContext.Out.WriteLine($"Created: {iconFileName} ({iconType.Value})");
                Assert.IsTrue(File.Exists(iconPath), $"Icon file should be created: {iconFileName}");
            }

            // Verify all files were created
            var allIconFiles = Directory.GetFiles(buttonDir, "test_icon.*", SearchOption.TopDirectoryOnly);
            Assert.AreEqual(iconTypes.Count, allIconFiles.Length, 
                           $"Should have created {iconTypes.Count} icon files");

            Assert.Pass("Icon file types test completed successfully.");
        }

        [Test]
        public void TestIconNamingConventions()
        {
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            var buttonDir = Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelTwo.panel", "TestAbout.pushbutton");
            
            if (!Directory.Exists(buttonDir))
            {
                Assert.Inconclusive($"Test button directory does not exist: {buttonDir}");
                return;
            }

            // Test common icon naming conventions
            var iconNames = new[]
            {
                "icon.png",           // Standard icon
                "icon_small.png",     // Small size variant
                "icon_large.png",     // Large size variant
                "icon_16.png",        // Size-specific
                "icon_32.png",        // Size-specific
                "icon_64.png",        // Size-specific
                "button_icon.png",    // Alternative naming
                "cmd_icon.png"        // Command icon
            };

            TestContext.Out.WriteLine("=== Testing Icon Naming Conventions ===");
            
            foreach (var iconName in iconNames)
            {
                var iconPath = Path.Combine(buttonDir, iconName);
                CreateSimpleTestFile(iconPath, "Test icon content");
                _createdTestFiles.Add(iconPath);
                
                TestContext.Out.WriteLine($"Created: {iconName}");
                Assert.IsTrue(File.Exists(iconPath), $"Icon file should be created: {iconName}");
            }

            // Test icon discovery with different naming patterns
            var discoveredIcons = Directory.GetFiles(buttonDir, "*icon*", SearchOption.TopDirectoryOnly);
            TestContext.Out.WriteLine($"Discovered {discoveredIcons.Length} icon files with pattern '*icon*'");
            
            Assert.GreaterOrEqual(discoveredIcons.Length, iconNames.Length, 
                                 "Should discover all created icon files");

            Assert.Pass("Icon naming conventions test completed successfully.");
        }

        [Test]
        public void TestComponentIconAssociation()
        {
            if (_installedExtensions == null)
            {
                Assert.Fail("No test extensions loaded");
                return;
            }

            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            
            // Create icons for specific components
            var componentIconPairs = new[]
            {
                ("TestAbout.pushbutton", "icon.png"),
                ("PanelOneButton1.pushbutton", "icon.png"),
                ("Debug Dialog Config.panelbutton", "icon.png")
            };

            foreach (var (componentDir, iconFile) in componentIconPairs)
            {
                var componentPath = Directory.GetDirectories(testBundlePath, componentDir, SearchOption.AllDirectories).FirstOrDefault();
                if (componentPath != null)
                {
                    var iconPath = Path.Combine(componentPath, iconFile);
                    CreateSimpleTestFile(iconPath, "Component icon content");
                    _createdTestFiles.Add(iconPath);
                }
            }

            // Re-parse extensions to check component-icon associations
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            
            TestContext.Out.WriteLine("=== Testing Component-Icon Associations ===");
            
            foreach (var extension in extensions)
            {
                PrintComponentIconAssociations(extension);
            }

            Assert.Pass("Component icon association test completed successfully.");
        }

        // Helper method to create a simple test file
        private void CreateSimpleTestFile(string filePath, string content)
        {
            var directory = Path.GetDirectoryName(filePath);
            if (directory != null)
                Directory.CreateDirectory(directory);
            File.WriteAllText(filePath, content);
        }

        // Helper method to print component-icon associations
        private void PrintComponentIconAssociations(ParsedComponent component, int level = 0)
        {
            var indent = new string(' ', level * 2);
            
            if (!string.IsNullOrEmpty(component.ScriptPath))
            {
                var componentDir = Path.GetDirectoryName(component.ScriptPath);
                if (!string.IsNullOrEmpty(componentDir) && Directory.Exists(componentDir))
                {
                    var iconFiles = Directory.GetFiles(componentDir, "*icon*.*", SearchOption.TopDirectoryOnly);
                    
                    if (iconFiles.Any())
                    {
                        TestContext.Out.WriteLine($"{indent}[{component.Type}] {component.DisplayName}:");
                        foreach (var iconFile in iconFiles)
                        {
                            var fileName = Path.GetFileName(iconFile);
                            TestContext.Out.WriteLine($"{indent}  ?? {fileName}");
                        }
                    }
                }
            }

            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    PrintComponentIconAssociations(child, level + 1);
                }
            }
        }
    }
}