using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;
using System.Drawing;
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
            
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            
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
        public void TestIconParsingWithCreatedIcons()
        {
            TestContext.Out.WriteLine("=== Testing Icon Parsing with Created Icons ===");
            
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            var testIconFiles = new List<string>();
            
            try
            {
                // Find a component directory to add icons to
                var componentDir = Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelTwo.panel", "TestAbout.pushbutton");
                
                if (!Directory.Exists(componentDir))
                {
                    Assert.Inconclusive($"Test component directory not found: {componentDir}");
                    return;
                }
                
                // Create test icon files
                var iconFiles = new[]
                {
                    "icon.png",
                    "icon_large.png", 
                    "icon_16.png",
                    "button_icon.ico"
                };
                
                foreach (var iconFile in iconFiles)
                {
                    var iconPath = Path.Combine(componentDir, iconFile);
                    CreateSimpleTestIcon(iconPath);
                    testIconFiles.Add(iconPath);
                    TestContext.Out.WriteLine($"Created test icon: {iconFile}");
                }
                
                // Re-parse the extension to detect the new icons
                var extensions = ParseInstalledExtensions(new[] { testBundlePath });
                var extension = extensions.First();
                
                // Find the TestAbout component
                var testAboutComponent = FindComponentRecursively(extension, "TestAbout");
                
                if (testAboutComponent != null)
                {
                    TestContext.Out.WriteLine($"Found TestAbout component: {testAboutComponent.DisplayName}");
                    TestContext.Out.WriteLine($"Component has {testAboutComponent.Icons.Count} icon(s)");
                    TestContext.Out.WriteLine($"Has icons: {testAboutComponent.HasIcons}");
                    TestContext.Out.WriteLine($"Has valid icons: {testAboutComponent.HasValidIcons}");
                    
                    if (testAboutComponent.PrimaryIcon != null)
                    {
                        TestContext.Out.WriteLine($"Primary icon: {testAboutComponent.PrimaryIcon.FileName} ({testAboutComponent.PrimaryIcon.Type})");
                    }
                    
                    // List all icons
                    foreach (var icon in testAboutComponent.Icons)
                    {
                        TestContext.Out.WriteLine($"  Icon: {icon.FileName} ({icon.Type}, {icon.Extension}, {icon.FileSize} bytes, Valid: {icon.IsValid})");
                    }
                    
                    // We should have found some icons
                    Assert.Greater(testAboutComponent.Icons.Count, 0, "Should have found created icons");
                    Assert.IsTrue(testAboutComponent.HasIcons, "Component should report having icons");
                    Assert.IsTrue(testAboutComponent.HasValidIcons, "Component should have valid icons");
                }
                else
                {
                    Assert.Fail("Could not find TestAbout component to test icons");
                }
                
                Assert.Pass("Icon parsing with created icons test completed successfully");
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