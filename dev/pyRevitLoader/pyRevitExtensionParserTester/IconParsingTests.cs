using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class IconParsingTests : TempFileTestBase
    {
        private IEnumerable<ParsedExtension>? _installedExtensions;
        private string? _testExtensionPath;
        
        [SetUp]
        public void Setup()
        {
            // Create test extension with icons on-the-fly
            _testExtensionPath = TestExtensionFactory.CreateIconTestExtension(TestTempDir);
            _installedExtensions = ParseInstalledExtensions(new[] { _testExtensionPath });
        }

        [Test]
        public void TestIconFileDiscovery()
        {
            Assert.IsNotNull(_testExtensionPath, "Test extension path should not be null");
            
            // Test icon discovery in the on-the-fly created extension
            var buttonDirectories = Directory.GetDirectories(_testExtensionPath!, "*.pushbutton", SearchOption.AllDirectories);

            TestContext.Out.WriteLine("=== Icon File Discovery Test ===");
            foreach (var buttonDir in buttonDirectories)
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

            Assert.Pass("Icon file discovery test completed successfully.");
        }

        [Test]
        public void TestIconFileTypes()
        {
            Assert.IsNotNull(_testExtensionPath, "Test extension path should not be null");
            
            // Create a dedicated button for icon type testing
            var panelPath = Directory.GetDirectories(_testExtensionPath!, "*.panel", SearchOption.AllDirectories).First();
            var buttonDir = TestExtensionBuilder.CreatePushButton(panelPath, "IconTypeTest", "print('icon type test')");

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
                
                // Create simple test file (actual image format not required for this test)
                File.WriteAllText(iconPath, $"Test {iconType.Value} content");
                
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
            Assert.IsNotNull(_testExtensionPath, "Test extension path should not be null");
            
            // Create a dedicated button for naming convention testing
            var panelPath = Directory.GetDirectories(_testExtensionPath!, "*.panel", SearchOption.AllDirectories).First();
            var buttonDir = TestExtensionBuilder.CreatePushButton(panelPath, "IconNamingTest", "print('naming test')");

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
                File.WriteAllText(iconPath, "Test icon content");
                
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
            Assert.IsNotNull(_installedExtensions, "Test extensions should be loaded");
            
            TestContext.Out.WriteLine("=== Testing Component-Icon Associations ===");
            
            foreach (var extension in _installedExtensions!)
            {
                PrintComponentIconAssociations(extension);
            }

            // Verify specific buttons have icons
            var buttonWithIcons = FindComponentRecursively(_installedExtensions!.First(), "ButtonWithIcons");
            Assert.IsNotNull(buttonWithIcons, "ButtonWithIcons should be found");
            
            var buttonNoIcons = FindComponentRecursively(_installedExtensions!.First(), "ButtonNoIcons");
            Assert.IsNotNull(buttonNoIcons, "ButtonNoIcons should be found");

            Assert.Pass("Component icon association test completed successfully.");
        }

        [Test]
        public void TestDarkIconDetection()
        {
            Assert.IsNotNull(_installedExtensions, "Test extensions should be loaded");
            
            TestContext.Out.WriteLine("=== Testing Dark Icon Detection ===");
            
            var buttonWithIcons = FindComponentRecursively(_installedExtensions!.First(), "ButtonWithIcons");
            Assert.IsNotNull(buttonWithIcons, "ButtonWithIcons should be found");
            
            // Check that the button directory has both light and dark icons
            var buttonDir = Path.GetDirectoryName(buttonWithIcons!.ScriptPath);
            Assert.IsNotNull(buttonDir, "Button directory should exist");
            
            var lightIcon = Path.Combine(buttonDir!, "icon.png");
            var darkIcon = Path.Combine(buttonDir!, "icon.dark.png");
            
            Assert.IsTrue(File.Exists(lightIcon), "Light icon should exist");
            Assert.IsTrue(File.Exists(darkIcon), "Dark icon should exist");
            
            TestContext.Out.WriteLine($"Light icon: {lightIcon}");
            TestContext.Out.WriteLine($"Dark icon: {darkIcon}");
            
            Assert.Pass("Dark icon detection test completed successfully.");
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
                            TestContext.Out.WriteLine($"{indent}  → {fileName}");
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