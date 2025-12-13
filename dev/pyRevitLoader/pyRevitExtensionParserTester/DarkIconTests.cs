using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;
using System.Drawing.Imaging;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Tests for icon functionality. Only icon.png (Standard) and icon.dark.png (DarkStandard) are supported.
    /// </summary>
    [TestFixture]
    public class DarkIconTests : TempFileTestBase
    {

        [Test]
        public void TestDarkIconDetection_OnlyIconDarkPngIsSupported()
        {
            TestContext.Out.WriteLine("=== Testing Dark Icon Detection ===");
            TestContext.Out.WriteLine("Only 'icon.dark.png' pattern is recognized as dark icon.");

            var testIcons = new Dictionary<string, bool>
            {
                // Only icon.dark.png should be detected as dark
                { "icon.dark.png", true },
                { "icon.dark.ico", true },
                { "ICON.DARK.PNG", true }, // Case insensitive
                
                // All other patterns should NOT be detected as dark
                { "icon.png", false },
                { "icon.ico", false },
                { "icon_dark.png", false },
                { "icon-dark.png", false },
                { "button_icon.dark.png", false },
                { "dark_icon.png", false },
                { "iconDark.png", false },
                { "icon_16.dark.png", false },
                { "my_icon.dark.png", false },
            };

            foreach (var testCase in testIcons)
            {
                var iconPath = Path.Combine(TestTempDir, testCase.Key);
                CreateTestIcon(iconPath, 32, 32);

                var icon = new ComponentIcon(iconPath);
                
                TestContext.Out.WriteLine($"Testing: {testCase.Key}");
                TestContext.Out.WriteLine($"  Expected Dark: {testCase.Value}");
                TestContext.Out.WriteLine($"  Actual Dark: {icon.IsDark}");
                TestContext.Out.WriteLine($"  Icon Type: {icon.Type}");
                
                Assert.AreEqual(testCase.Value, icon.IsDark, 
                    $"Icon '{testCase.Key}' dark detection failed. Expected: {testCase.Value}, Actual: {icon.IsDark}");
            }

            Assert.Pass("Dark icon detection test completed successfully.");
        }

        [Test]
        public void TestIconTypes_OnlyStandardAndDarkStandard()
        {
            TestContext.Out.WriteLine("=== Testing Icon Type Classification ===");
            TestContext.Out.WriteLine("Only Standard and DarkStandard icon types are supported.");

            var testIcons = new Dictionary<string, IconType>
            {
                // Standard icons (icon.png)
                { "icon.png", IconType.Standard },
                { "icon.ico", IconType.Standard },
                { "ICON.PNG", IconType.Standard },
                
                // Dark standard icons (icon.dark.png)
                { "icon.dark.png", IconType.DarkStandard },
                { "icon.dark.ico", IconType.DarkStandard },
                
                // All other patterns default to Standard (not dark)
                { "button_icon.png", IconType.Standard },
                { "icon_16.png", IconType.Standard },
                { "icon_32.png", IconType.Standard },
                { "icon_large.png", IconType.Standard },
            };

            foreach (var testCase in testIcons)
            {
                var iconPath = Path.Combine(TestTempDir, testCase.Key);
                CreateTestIcon(iconPath, 32, 32);

                var icon = new ComponentIcon(iconPath);
                
                TestContext.Out.WriteLine($"Testing: {testCase.Key}");
                TestContext.Out.WriteLine($"  Expected Type: {testCase.Value}");
                TestContext.Out.WriteLine($"  Actual Type: {icon.Type}");
                TestContext.Out.WriteLine($"  Is Dark: {icon.IsDark}");
                
                Assert.AreEqual(testCase.Value, icon.Type, 
                    $"Icon '{testCase.Key}' type classification failed. Expected: {testCase.Value}, Actual: {icon.Type}");
            }

            Assert.Pass("Icon type classification test completed successfully.");
        }

        [Test]
        public void TestComponentIconCollection_BasicFunctionality()
        {
            TestContext.Out.WriteLine("=== Testing ComponentIconCollection ===");

            var collection = new ComponentIconCollection();

            // Create light and dark icons
            var iconPath = Path.Combine(TestTempDir, "icon.png");
            var darkIconPath = Path.Combine(TestTempDir, "icon.dark.png");
            
            CreateTestIcon(iconPath, 32, 32, Color.Blue);
            CreateTestIcon(darkIconPath, 32, 32, Color.Orange);

            var lightIcon = new ComponentIcon(iconPath);
            var darkIcon = new ComponentIcon(darkIconPath);
            collection.Add(lightIcon);
            collection.Add(darkIcon);

            // Test collection properties
            TestContext.Out.WriteLine($"Total icons: {collection.Count}");
            TestContext.Out.WriteLine($"Has dark icons: {collection.HasDarkIcons}");
            TestContext.Out.WriteLine($"Has light icons: {collection.HasLightIcons}");

            Assert.AreEqual(2, collection.Count, "Should have 2 total icons");
            Assert.IsTrue(collection.HasDarkIcons, "Collection should have dark icons");
            Assert.IsTrue(collection.HasLightIcons, "Collection should have light icons");

            // Test primary icons
            var primaryIcon = collection.PrimaryIcon;
            var primaryDarkIcon = collection.PrimaryDarkIcon;
            
            TestContext.Out.WriteLine($"Primary icon: {primaryIcon?.FileName} (Type: {primaryIcon?.Type})");
            TestContext.Out.WriteLine($"Primary dark icon: {primaryDarkIcon?.FileName} (Type: {primaryDarkIcon?.Type})");

            Assert.IsNotNull(primaryIcon, "Should have a primary icon");
            Assert.AreEqual(IconType.Standard, primaryIcon.Type, "Primary icon should be Standard type");
            Assert.IsFalse(primaryIcon.IsDark, "Primary icon should not be dark");

            Assert.IsNotNull(primaryDarkIcon, "Should have a primary dark icon");
            Assert.AreEqual(IconType.DarkStandard, primaryDarkIcon.Type, "Primary dark icon should be DarkStandard type");
            Assert.IsTrue(primaryDarkIcon.IsDark, "Primary dark icon should be dark");

            Assert.Pass("ComponentIconCollection test completed successfully.");
        }

        [Test]
        public void TestDarkIconsInRealExtension()
        {
            TestContext.Out.WriteLine("=== Testing Dark Icons in Real Extension ===");
            
            var testBundlePath = TestConfiguration.TestExtensionPath;
            
            // Parse the extension to find components with existing dark icons
            TestContext.Out.WriteLine($"Parsing extension from: {testBundlePath}");
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            var extension = extensions.First();
            
            TestContext.Out.WriteLine($"Extension parsed: {extension.Name}");
            
            // Search for all components and check which ones have icons
            var allComponents = GetAllComponentsFlat(extension);
            TestContext.Out.WriteLine($"Total components found: {allComponents.Count}");
            
            var componentsWithIcons = allComponents.Where(c => c.Icons.Count > 0).ToList();
            TestContext.Out.WriteLine($"Components with icons: {componentsWithIcons.Count}");
            
            var componentsWithDarkIcons = allComponents.Where(c => c.Icons.HasDarkIcons).ToList();
            TestContext.Out.WriteLine($"Components with dark icons: {componentsWithDarkIcons.Count}");
            
            // List all components with icons
            foreach (var component in componentsWithIcons)
            {
                TestContext.Out.WriteLine($"\nComponent: {component.DisplayName} ({component.Name})");
                TestContext.Out.WriteLine($"  Type: {component.Type}");
                TestContext.Out.WriteLine($"  Total icons: {component.Icons.Count}");
                TestContext.Out.WriteLine($"  Has dark icons: {component.Icons.HasDarkIcons}");
                
                foreach (var icon in component.Icons)
                {
                    TestContext.Out.WriteLine($"    - {icon.FileName} (Type: {icon.Type}, Dark: {icon.IsDark})");
                }
            }
            
            // Validate dark icons if found
            if (componentsWithDarkIcons.Count > 0)
            {
                foreach (var component in componentsWithDarkIcons)
                {
                    var primaryDarkIcon = component.Icons.PrimaryDarkIcon;
                    if (primaryDarkIcon != null)
                    {
                        Assert.IsTrue(primaryDarkIcon.IsDark, "Primary dark icon should be dark");
                        Assert.AreEqual(IconType.DarkStandard, primaryDarkIcon.Type, "Primary dark icon should be DarkStandard type");
                    }
                }
                
                Assert.Pass($"Found {componentsWithDarkIcons.Count} component(s) with dark icons.");
            }
            else
            {
                TestContext.Out.WriteLine("\nNo dark icons found in the extension.");
                Assert.Inconclusive("No dark icons found in the extension. Test skipped.");
            }
        }
        
        [Test]
        public void TestThemeAwareIconSelection()
        {
            TestContext.Out.WriteLine("=== Testing Theme-Aware Icon Selection ===");

            var collection = new ComponentIconCollection();

            // Create light and dark icons
            var iconPath = Path.Combine(TestTempDir, "icon.png");
            var darkIconPath = Path.Combine(TestTempDir, "icon.dark.png");
            
            CreateTestIcon(iconPath, 32, 32, Color.Blue);
            CreateTestIcon(darkIconPath, 32, 32, Color.Orange);

            var lightIcon = new ComponentIcon(iconPath);
            var darkIcon = new ComponentIcon(darkIconPath);
            collection.Add(lightIcon);
            collection.Add(darkIcon);

            // Test light theme selection
            var selectedForLightTheme = collection.PrimaryIcon;
            Assert.IsNotNull(selectedForLightTheme, "Should find icon for light theme");
            Assert.IsFalse(selectedForLightTheme.IsDark, "Light theme should use light icon");
            Assert.AreEqual(IconType.Standard, selectedForLightTheme.Type);

            // Test dark theme selection
            var selectedForDarkTheme = collection.PrimaryDarkIcon;
            Assert.IsNotNull(selectedForDarkTheme, "Should find icon for dark theme");
            Assert.IsTrue(selectedForDarkTheme.IsDark, "Dark theme should use dark icon");
            Assert.AreEqual(IconType.DarkStandard, selectedForDarkTheme.Type);

            Assert.Pass("Theme-aware icon selection test completed successfully.");
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

        // Helper method to create a test icon
        private void CreateTestIcon(string filePath, int width, int height, Color? backgroundColor = null)
        {
            var bgColor = backgroundColor ?? Color.Blue;
            
            using (var bitmap = new Bitmap(width, height))
            using (var graphics = Graphics.FromImage(bitmap))
            {
                graphics.Clear(bgColor);
                using (var pen = new Pen(Color.White, 2))
                {
                    graphics.DrawRectangle(pen, 1, 1, width - 3, height - 3);
                }
                
                // Add dark indicator for dark icons
                var fileName = Path.GetFileName(filePath).ToLowerInvariant();
                if (fileName == "icon.dark.png" || fileName == "icon.dark.ico")
                {
                    using (var brush = new SolidBrush(Color.Black))
                    using (var font = new Font("Arial", 8, FontStyle.Bold))
                    {
                        graphics.DrawString("D", font, brush, 2, 2);
                    }
                }
                
                bitmap.Save(filePath, ImageFormat.Png);
            }
        }
    }
}
