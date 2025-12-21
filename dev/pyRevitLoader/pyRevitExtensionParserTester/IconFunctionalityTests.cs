using pyRevitExtensionParser;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;
using System.Drawing.Imaging;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class IconFunctionalityTests
    {
        [Test]
        public void TestIconParsingBasicFunctionality()
        {
            TestContext.Out.WriteLine("=== Testing Basic Icon Parsing Functionality ===");
            
            // Test ComponentIcon creation
            var tempIconFile = Path.GetTempFileName();
            try
            {
                // Create a simple test file
                File.WriteAllText(tempIconFile, "test icon content");
                
                // Test ComponentIcon creation
                var icon = new ComponentIcon(tempIconFile);
                TestContext.Out.WriteLine($"Created icon: {icon.FileName}");
                TestContext.Out.WriteLine($"File size: {icon.FileSize} bytes");
                TestContext.Out.WriteLine($"Extension: {icon.Extension}");
                TestContext.Out.WriteLine($"Type: {icon.Type}");
                
                Assert.IsNotNull(icon.FilePath);
                Assert.IsNotNull(icon.FileName);
                Assert.GreaterOrEqual(icon.FileSize, 0);
                
                TestContext.Out.WriteLine("? ComponentIcon creation works");
            }
            finally
            {
                if (File.Exists(tempIconFile))
                    File.Delete(tempIconFile);
            }
            
            // Test ComponentIconCollection
            var collection = new ComponentIconCollection();
            TestContext.Out.WriteLine($"Created empty collection with {collection.Count} items");
            
            // Test supported extensions
            var supportedExtensions = ComponentIconCollection.SupportedExtensions;
            TestContext.Out.WriteLine($"Supported extensions: [{string.Join(", ", supportedExtensions)}]");
            
            Assert.Greater(supportedExtensions.Length, 0);
            Assert.Contains(".png", supportedExtensions);
            Assert.Contains(".ico", supportedExtensions);
            
            TestContext.Out.WriteLine("? ComponentIconCollection functionality works");
            
            // Test extension recognition
            Assert.IsTrue(ComponentIconCollection.IsSupportedImageExtension(".png"));
            Assert.IsTrue(ComponentIconCollection.IsSupportedImageExtension(".ico"));
            Assert.IsFalse(ComponentIconCollection.IsSupportedImageExtension(".txt"));
            
            TestContext.Out.WriteLine("? Extension recognition works");
            
            Assert.Pass("Basic icon parsing functionality test completed successfully");
        }

        [Test]
        public void TestIconParsingWithRealExtension()
        {
            TestContext.Out.WriteLine("=== Testing Icon Parsing with Real Extension ===");
            
            var testBundlePath = TestConfiguration.TestExtensionPath;
            
            if (!Directory.Exists(testBundlePath))
            {
                Assert.Inconclusive($"Test bundle not found at: {testBundlePath}");
                return;
            }
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            var extensionsList = extensions.ToList();
            
            TestContext.Out.WriteLine($"Parsed {extensionsList.Count} extension(s)");
            
            Assert.Greater(extensionsList.Count, 0, "Should parse at least one extension");
            
            var extension = extensionsList.First();
            TestContext.Out.WriteLine($"Extension: {extension.Name}");
            TestContext.Out.WriteLine($"Directory: {extension.Directory}");
            
            // Check if any components have the Icons property
            var allComponents = GetAllComponentsFlat(extension);
            TestContext.Out.WriteLine($"Found {allComponents.Count} total components");
            
            var componentsWithIconProperty = allComponents.Where(c => c.Icons != null).ToList();
            TestContext.Out.WriteLine($"Components with Icons property: {componentsWithIconProperty.Count}");
            
            // All components should have the Icons property (even if empty)
            Assert.AreEqual(allComponents.Count, componentsWithIconProperty.Count, 
                           "All components should have Icons property");
            
            // Find components that actually have icons
            var componentsWithIcons = allComponents.Where(c => c.HasIcons).ToList();
            TestContext.Out.WriteLine($"Components with actual icons: {componentsWithIcons.Count}");
            
            // Print details of components with icons
            foreach (var component in componentsWithIcons)
            {
                TestContext.Out.WriteLine($"  {component.DisplayName} ({component.Type}): {component.Icons.Count} icon(s)");
                foreach (var icon in component.Icons)
                {
                    TestContext.Out.WriteLine($"    - {icon.FileName} ({icon.Type}, {icon.FileSize} bytes, Valid: {icon.IsValid})");
                }
            }
            
            Assert.Pass("Icon parsing with real extension test completed successfully");
        }

        [Test]
        public void TestIconParsingWithExistingIcons()
        {
            TestContext.Out.WriteLine("=== Testing Icon Parsing with Existing Icons ===");
            
            var testBundlePath = TestConfiguration.TestExtensionPath;
            
            if (!Directory.Exists(testBundlePath))
            {
                Assert.Inconclusive($"Test bundle not found at: {testBundlePath}");
                return;
            }
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            var extension = extensions.First();
            
            TestContext.Out.WriteLine($"Extension: {extension.Name}");
            
            // Find all components with icons
            var allComponents = GetAllComponentsFlat(extension);
            var componentsWithIcons = allComponents.Where(c => c.HasIcons).ToList();
            
            TestContext.Out.WriteLine($"Total components: {allComponents.Count}");
            TestContext.Out.WriteLine($"Components with icons: {componentsWithIcons.Count}");
            
            if (componentsWithIcons.Count == 0)
            {
                TestContext.Out.WriteLine("No components with icons found in the extension.");
                Assert.Inconclusive("No existing icons found to test with. Extension components don't have icons.");
                return;
            }
            
            // Test each component with icons
            foreach (var component in componentsWithIcons)
            {
                TestContext.Out.WriteLine($"\nComponent: {component.DisplayName} ({component.Name})");
                TestContext.Out.WriteLine($"  Type: {component.Type}");
                TestContext.Out.WriteLine($"  Directory: {component.Directory}");
                TestContext.Out.WriteLine($"  Icon count: {component.Icons.Count}");
                TestContext.Out.WriteLine($"  Has icons: {component.HasIcons}");
                TestContext.Out.WriteLine($"  Has valid icons: {component.HasValidIcons}");
                
                // Validate icon properties
                Assert.Greater(component.Icons.Count, 0, $"{component.DisplayName} should have at least one icon");
                Assert.IsTrue(component.HasIcons, $"{component.DisplayName} should report having icons");
                
                // Test primary icon if it exists
                if (component.PrimaryIcon != null)
                {
                    TestContext.Out.WriteLine($"  Primary icon: {component.PrimaryIcon.FileName} ({component.PrimaryIcon.Type})");
                    Assert.IsNotNull(component.PrimaryIcon.FilePath, "Primary icon should have a file path");
                    Assert.IsNotNull(component.PrimaryIcon.FileName, "Primary icon should have a file name");
                }
                
                // List and validate all icons
                foreach (var icon in component.Icons)
                {
                    TestContext.Out.WriteLine($"    - {icon.FileName} (Type: {icon.Type}, Size: {icon.FileSize} bytes, Valid: {icon.IsValid})");
                    
                    Assert.IsNotNull(icon.FilePath, $"Icon {icon.FileName} should have a file path");
                    Assert.IsNotNull(icon.FileName, $"Icon {icon.FileName} should have a file name");
                    Assert.IsNotNull(icon.Extension, $"Icon {icon.FileName} should have an extension");
                    Assert.GreaterOrEqual(icon.FileSize, 0, $"Icon {icon.FileName} should have non-negative file size");
                    
                    // Verify the icon file actually exists
                    if (icon.IsValid)
                    {
                        Assert.IsTrue(File.Exists(icon.FilePath), $"Valid icon file should exist: {icon.FilePath}");
                    }
                }
            }
            
            Assert.Pass($"Icon parsing validation completed successfully. Tested {componentsWithIcons.Count} component(s) with icons.");
        }

        [Test]
        public void TestDarkIconBasicFunctionality()
        {
            TestContext.Out.WriteLine("=== Testing Dark Icon Basic Functionality ===");
            
            var tempDir = Path.GetTempPath();
            var testFiles = new List<string>();
            
            try
            {
                // Test both light and dark icon creation
                var lightIconPath = Path.Combine(tempDir, "icon.png");
                var darkIconPath = Path.Combine(tempDir, "icon.dark.png");
                
                CreateSimpleTestIcon(lightIconPath);
                CreateSimpleTestIcon(darkIconPath);
                testFiles.Add(lightIconPath);
                testFiles.Add(darkIconPath);
                
                // Test light icon
                var lightIcon = new ComponentIcon(lightIconPath);
                TestContext.Out.WriteLine($"Light icon: {lightIcon.FileName}");
                TestContext.Out.WriteLine($"  Is Dark: {lightIcon.IsDark}");
                TestContext.Out.WriteLine($"  Type: {lightIcon.Type}");
                
                Assert.IsFalse(lightIcon.IsDark, "Light icon should not be marked as dark");
                Assert.AreEqual(IconType.Standard, lightIcon.Type, "Light icon should be Standard type");
                
                // Test dark icon
                var darkIcon = new ComponentIcon(darkIconPath);
                TestContext.Out.WriteLine($"Dark icon: {darkIcon.FileName}");
                TestContext.Out.WriteLine($"  Is Dark: {darkIcon.IsDark}");
                TestContext.Out.WriteLine($"  Type: {darkIcon.Type}");
                
                Assert.IsTrue(darkIcon.IsDark, "Dark icon should be marked as dark");
                Assert.AreEqual(IconType.DarkStandard, darkIcon.Type, "Dark icon should be DarkStandard type");
                
                // Test ComponentIconCollection with both
                var collection = new ComponentIconCollection();
                collection.Add(lightIcon);
                collection.Add(darkIcon);
                
                TestContext.Out.WriteLine($"Collection has {collection.Count} icons");
                TestContext.Out.WriteLine($"Has light icons: {collection.HasLightIcons}");
                TestContext.Out.WriteLine($"Has dark icons: {collection.HasDarkIcons}");
                TestContext.Out.WriteLine($"Primary icon: {collection.PrimaryIcon?.FileName}");
                TestContext.Out.WriteLine($"Primary dark icon: {collection.PrimaryDarkIcon?.FileName}");
                
                Assert.AreEqual(2, collection.Count, "Collection should have 2 icons");
                Assert.IsTrue(collection.HasLightIcons, "Collection should have light icons");
                Assert.IsTrue(collection.HasDarkIcons, "Collection should have dark icons");
                Assert.AreEqual(lightIcon, collection.PrimaryIcon, "Primary icon should be the light icon");
                Assert.AreEqual(darkIcon, collection.PrimaryDarkIcon, "Primary dark icon should be the dark icon");
                
                TestContext.Out.WriteLine("? Dark icon basic functionality works");
                Assert.Pass("Dark icon basic functionality test completed successfully");
            }
            finally
            {
                // Clean up test files
                foreach (var file in testFiles)
                {
                    if (File.Exists(file))
                        File.Delete(file);
                }
            }
        }

        // Helper method to create a simple test icon file
        private void CreateSimpleTestIcon(string filePath)
        {
            var extension = Path.GetExtension(filePath).ToLowerInvariant();
            
            if (extension == ".png" || extension == ".ico")
            {
                // Create a simple 32x32 bitmap
                using (var bitmap = new Bitmap(32, 32))
                using (var graphics = Graphics.FromImage(bitmap))
                {
                    graphics.Clear(Color.Blue);
                    using (var pen = new Pen(Color.White, 2))
                    {
                        graphics.DrawRectangle(pen, 2, 2, 28, 28);
                    }
                    
                    bitmap.Save(filePath, ImageFormat.Png);
                }
            }
            else
            {
                // For other extensions, just create a simple text file
                File.WriteAllText(filePath, "Test icon file content");
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