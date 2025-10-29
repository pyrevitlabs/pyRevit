using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;
using System.Drawing;
using System.Drawing.Imaging;
using System;
using System.Linq;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class DarkIconTests
    {
        private List<string> _createdTestFiles = new List<string>();
        
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
        public void TestDarkIconDetection_StandardPatterns()
        {
            TestContext.Out.WriteLine("=== Testing Dark Icon Detection - Standard Patterns ===");

            var tempDir = Path.GetTempPath();
            var testIcons = new Dictionary<string, bool>
            {
                // Dark icons (should be detected as dark)
                { "icon.dark.png", true },
                { "icon_dark.png", true },
                { "icon-dark.png", true },
                { "icon.dark.ico", true },
                { "icon_dark.ico", true },
                { "icon-dark.ico", true },
                { "button_icon.dark.png", true },
                { "button_icon_dark.png", true },
                { "cmd_icon.dark.png", true },
                
                // Light icons (should NOT be detected as dark)
                { "icon.png", false },
                { "icon.ico", false },
                { "icon_light.png", false },
                { "icon.light.png", false },
                { "button_icon.png", false },
                { "cmd_icon.png", false },
                
                // Edge cases
                { "dark_icon.png", false }, // "dark" at beginning, not as suffix
                { "icon_dark_theme.png", true }, // contains "_dark"
                { "my_icon.dark.png", true }, // dark pattern in middle
                { "iconDark.png", false }, // no separator, should not match
            };

            foreach (var testCase in testIcons)
            {
                var iconPath = Path.Combine(tempDir, testCase.Key);
                CreateTestIcon(iconPath, 32, 32);
                _createdTestFiles.Add(iconPath);

                var icon = new ComponentIcon(iconPath);
                
                TestContext.Out.WriteLine($"Testing: {testCase.Key}");
                TestContext.Out.WriteLine($"  Expected Dark: {testCase.Value}");
                TestContext.Out.WriteLine($"  Actual Dark: {icon.IsDark}");
                TestContext.Out.WriteLine($"  Icon Type: {icon.Type}");
                
                Assert.AreEqual(testCase.Value, icon.IsDark, 
                    $"Icon '{testCase.Key}' dark detection failed. Expected: {testCase.Value}, Actual: {icon.IsDark}");
            }

            Assert.Pass("Dark icon detection test for standard patterns completed successfully.");
        }

        [Test]
        public void TestDarkIconTypes()
        {
            TestContext.Out.WriteLine("=== Testing Dark Icon Type Classification ===");

            var tempDir = Path.GetTempPath();
            var testIcons = new Dictionary<string, IconType>
            {
                // Standard dark icons
                { "icon.dark.png", IconType.DarkStandard },
                { "icon_dark.png", IconType.DarkStandard },
                
                // Size-specific dark icons
                { "icon_16.dark.png", IconType.DarkSize16 },
                { "icon_32.dark.png", IconType.DarkSize32 },
                { "icon_64.dark.png", IconType.DarkSize64 },
                { "icon16.dark.png", IconType.DarkSize16 },
                { "icon32.dark.png", IconType.DarkSize32 },
                { "icon64.dark.png", IconType.DarkSize64 },
                
                // Size variant dark icons
                { "icon_large.dark.png", IconType.DarkLarge },
                { "icon_small.dark.png", IconType.DarkSmall },
                
                // Special type dark icons
                { "button_icon.dark.png", IconType.DarkButton },
                { "cmd_icon.dark.png", IconType.DarkCommand },
                
                // Corresponding light icons for comparison
                { "icon.png", IconType.Standard },
                { "icon_16.png", IconType.Size16 },
                { "icon_32.png", IconType.Size32 },
                { "icon_64.png", IconType.Size64 },
                { "icon_large.png", IconType.Large },
                { "icon_small.png", IconType.Small },
                { "button_icon.png", IconType.Button },
                { "cmd_icon.png", IconType.Command }
            };

            foreach (var testCase in testIcons)
            {
                var iconPath = Path.Combine(tempDir, testCase.Key);
                CreateTestIcon(iconPath, 32, 32);
                _createdTestFiles.Add(iconPath);

                var icon = new ComponentIcon(iconPath);
                
                TestContext.Out.WriteLine($"Testing: {testCase.Key}");
                TestContext.Out.WriteLine($"  Expected Type: {testCase.Value}");
                TestContext.Out.WriteLine($"  Actual Type: {icon.Type}");
                TestContext.Out.WriteLine($"  Is Dark: {icon.IsDark}");
                
                Assert.AreEqual(testCase.Value, icon.Type, 
                    $"Icon '{testCase.Key}' type classification failed. Expected: {testCase.Value}, Actual: {icon.Type}");
            }

            Assert.Pass("Dark icon type classification test completed successfully.");
        }

        [Test]
        public void TestComponentIconCollectionDarkIconMethods()
        {
            TestContext.Out.WriteLine("=== Testing ComponentIconCollection Dark Icon Methods ===");

            var tempDir = Path.GetTempPath();
            var collection = new ComponentIconCollection();

            // Create a mix of light and dark icons
            var iconData = new[]
            {
                new { Name = "icon.png", IsDark = false, Type = IconType.Standard },
                new { Name = "icon.dark.png", IsDark = true, Type = IconType.DarkStandard },
                new { Name = "icon_16.png", IsDark = false, Type = IconType.Size16 },
                new { Name = "icon_16.dark.png", IsDark = true, Type = IconType.DarkSize16 },
                new { Name = "icon_large.png", IsDark = false, Type = IconType.Large },
                new { Name = "icon_large.dark.png", IsDark = true, Type = IconType.DarkLarge }
            };

            foreach (var iconInfo in iconData)
            {
                var iconPath = Path.Combine(tempDir, iconInfo.Name);
                CreateTestIcon(iconPath, 32, 32);
                _createdTestFiles.Add(iconPath);

                var icon = new ComponentIcon(iconPath);
                collection.Add(icon);
                
                TestContext.Out.WriteLine($"Added icon: {iconInfo.Name} (Dark: {icon.IsDark}, Type: {icon.Type})");
            }

            // Test collection properties and methods
            TestContext.Out.WriteLine($"Total icons: {collection.Count}");
            TestContext.Out.WriteLine($"Has dark icons: {collection.HasDarkIcons}");
            TestContext.Out.WriteLine($"Has light icons: {collection.HasLightIcons}");
            
            var lightIcons = collection.LightIcons.ToList();
            var darkIcons = collection.DarkIcons.ToList();
            
            TestContext.Out.WriteLine($"Light icons count: {lightIcons.Count}");
            TestContext.Out.WriteLine($"Dark icons count: {darkIcons.Count}");

            // Verify counts
            Assert.AreEqual(6, collection.Count, "Should have 6 total icons");
            Assert.AreEqual(3, lightIcons.Count, "Should have 3 light icons");
            Assert.AreEqual(3, darkIcons.Count, "Should have 3 dark icons");
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

            // Test GetBySize with theme parameter
            var lightSize16 = collection.GetBySize(16, false);
            var darkSize16 = collection.GetBySize(16, true);
            
            TestContext.Out.WriteLine($"Light 16px icon: {lightSize16?.FileName}");
            TestContext.Out.WriteLine($"Dark 16px icon: {darkSize16?.FileName}");

            Assert.IsNotNull(lightSize16, "Should find light 16px icon");
            Assert.IsNotNull(darkSize16, "Should find dark 16px icon");
            Assert.IsFalse(lightSize16.IsDark, "Light 16px icon should not be dark");
            Assert.IsTrue(darkSize16.IsDark, "Dark 16px icon should be dark");

            Assert.Pass("ComponentIconCollection dark icon methods test completed successfully.");
        }

        [Test]
        public void TestDarkIconsInRealExtension()
        {
            TestContext.Out.WriteLine("=== Testing Dark Icons in Real Extension ===");
            
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            var componentPath = Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelTwo.panel", "TestAbout.pushbutton");
            
            if (!Directory.Exists(componentPath))
            {
                Assert.Inconclusive($"Test component directory not found: {componentPath}");
                return;
            }

            try
            {
                // Create a set of light and dark icons in the test component
                var iconPairs = new[]
                {
                    new { Light = "icon.png", Dark = "icon.dark.png" },
                    new { Light = "icon_16.png", Dark = "icon_16.dark.png" },
                    new { Light = "icon_32.png", Dark = "icon_32.dark.png" },
                    new { Light = "icon_large.png", Dark = "icon_large.dark.png" }
                };

                foreach (var pair in iconPairs)
                {
                    var lightPath = Path.Combine(componentPath, pair.Light);
                    var darkPath = Path.Combine(componentPath, pair.Dark);
                    
                    CreateTestIcon(lightPath, 32, 32, Color.Blue);  // Light icons in blue
                    CreateTestIcon(darkPath, 32, 32, Color.Orange); // Dark icons in orange for distinction
                    
                    _createdTestFiles.Add(lightPath);
                    _createdTestFiles.Add(darkPath);
                }

                // Re-parse the extension to detect the new icons
                var extensions = ParseInstalledExtensions(new[] { testBundlePath });
                var extension = extensions.First();
                
                // Find the TestAbout component
                var testAboutComponent = FindComponentRecursively(extension, "TestAbout");
                
                if (testAboutComponent != null)
                {
                    TestContext.Out.WriteLine($"Found TestAbout component: {testAboutComponent.DisplayName}");
                    TestContext.Out.WriteLine($"Total icons: {testAboutComponent.Icons.Count}");
                    TestContext.Out.WriteLine($"Light icons: {testAboutComponent.Icons.LightIcons.Count()}");
                    TestContext.Out.WriteLine($"Dark icons: {testAboutComponent.Icons.DarkIcons.Count()}");
                    TestContext.Out.WriteLine($"Has dark icons: {testAboutComponent.Icons.HasDarkIcons}");
                    TestContext.Out.WriteLine($"Has light icons: {testAboutComponent.Icons.HasLightIcons}");
                    
                    // List all icons with their properties
                    foreach (var icon in testAboutComponent.Icons)
                    {
                        TestContext.Out.WriteLine($"  Icon: {icon.FileName}");
                        TestContext.Out.WriteLine($"    Type: {icon.Type}");
                        TestContext.Out.WriteLine($"    Is Dark: {icon.IsDark}");
                        TestContext.Out.WriteLine($"    Size: {icon.SizeSpecification}");
                        TestContext.Out.WriteLine($"    Valid: {icon.IsValid}");
                    }

                    // Test primary icons
                    var primaryIcon = testAboutComponent.Icons.PrimaryIcon;
                    var primaryDarkIcon = testAboutComponent.Icons.PrimaryDarkIcon;
                    
                    TestContext.Out.WriteLine($"Primary icon: {primaryIcon?.FileName} ({primaryIcon?.Type})");
                    TestContext.Out.WriteLine($"Primary dark icon: {primaryDarkIcon?.FileName} ({primaryDarkIcon?.Type})");

                    // Verify we found both light and dark icons
                    Assert.Greater(testAboutComponent.Icons.Count, 0, "Should have found icons");
                    Assert.IsTrue(testAboutComponent.Icons.HasDarkIcons, "Should have found dark icons");
                    Assert.IsTrue(testAboutComponent.Icons.HasLightIcons, "Should have found light icons");
                    
                    // Should have equal numbers of light and dark icons
                    var lightCount = testAboutComponent.Icons.LightIcons.Count();
                    var darkCount = testAboutComponent.Icons.DarkIcons.Count();
                    Assert.AreEqual(lightCount, darkCount, "Should have equal numbers of light and dark icons");
                    
                    // Verify primary icons exist and are correct types
                    Assert.IsNotNull(primaryIcon, "Should have a primary icon");
                    Assert.IsNotNull(primaryDarkIcon, "Should have a primary dark icon");
                    Assert.IsFalse(primaryIcon.IsDark, "Primary icon should not be dark");
                    Assert.IsTrue(primaryDarkIcon.IsDark, "Primary dark icon should be dark");
                }
                else
                {
                    Assert.Fail("Could not find TestAbout component to test dark icons");
                }
                
                Assert.Pass("Dark icons in real extension test completed successfully.");
            }
            finally
            {
                // Cleanup happens in TearDown
            }
        }

        [Test]
        public void TestDarkIconPrioritySorting()
        {
            TestContext.Out.WriteLine("=== Testing Dark Icon Priority Sorting ===");

            var tempDir = Path.GetTempPath();
            var collection = new ComponentIconCollection();

            // Create icons in mixed order to test sorting
            var iconNames = new[]
            {
                "icon_large.dark.png",    // DarkLarge (priority 10)
                "icon.png",               // Standard (priority 1)
                "icon_32.dark.png",       // DarkSize32 (priority 4)
                "icon_16.png",            // Size16 (priority 5)
                "icon.dark.png",          // DarkStandard (priority 2)
                "icon_32.png",            // Size32 (priority 3)
                "button_icon.dark.png",   // DarkButton (priority 14)
                "icon_16.dark.png"        // DarkSize16 (priority 6)
            };

            foreach (var iconName in iconNames)
            {
                var iconPath = Path.Combine(tempDir, iconName);
                CreateTestIcon(iconPath, 32, 32);
                _createdTestFiles.Add(iconPath);

                var icon = new ComponentIcon(iconPath);
                collection.Add(icon);
            }

            TestContext.Out.WriteLine("Icons before sorting:");
            for (int i = 0; i < collection.Count; i++)
            {
                TestContext.Out.WriteLine($"  {i + 1}. {collection[i].FileName} ({collection[i].Type})");
            }

            // Sort the collection (this should happen automatically in the parser)
            collection.Sort((icon1, icon2) => GetIconTypePriority(icon1.Type).CompareTo(GetIconTypePriority(icon2.Type)));

            TestContext.Out.WriteLine("Icons after sorting:");
            for (int i = 0; i < collection.Count; i++)
            {
                TestContext.Out.WriteLine($"  {i + 1}. {collection[i].FileName} ({collection[i].Type}) - Priority: {GetIconTypePriority(collection[i].Type)}");
            }

            // Verify sorting order
            Assert.AreEqual("icon.png", collection[0].FileName, "Standard icon should be first");
            Assert.AreEqual("icon.dark.png", collection[1].FileName, "Dark standard icon should be second");
            Assert.AreEqual("icon_32.png", collection[2].FileName, "Size32 icon should be third");
            Assert.AreEqual("icon_32.dark.png", collection[3].FileName, "Dark Size32 icon should be fourth");
            
            // Verify primary icon selection
            var primaryIcon = collection.PrimaryIcon;
            var primaryDarkIcon = collection.PrimaryDarkIcon;
            
            Assert.AreEqual("icon.png", primaryIcon.FileName, "Primary icon should be the standard icon");
            Assert.AreEqual("icon.dark.png", primaryDarkIcon.FileName, "Primary dark icon should be the dark standard icon");

            Assert.Pass("Dark icon priority sorting test completed successfully.");
        }

        [Test]
        public void TestThemeAwareIconSelection()
        {
            TestContext.Out.WriteLine("=== Testing Theme-Aware Icon Selection ===");

            var tempDir = Path.GetTempPath();
            var collection = new ComponentIconCollection();

            // Create a comprehensive set of light and dark icons
            var iconData = new[]
            {
                // Standard icons
                new { Name = "icon.png", IsDark = false, Type = IconType.Standard },
                new { Name = "icon.dark.png", IsDark = true, Type = IconType.DarkStandard },
                
                // Size-specific icons
                new { Name = "icon_16.png", IsDark = false, Type = IconType.Size16 },
                new { Name = "icon_16.dark.png", IsDark = true, Type = IconType.DarkSize16 },
                new { Name = "icon_32.png", IsDark = false, Type = IconType.Size32 },
                new { Name = "icon_32.dark.png", IsDark = true, Type = IconType.DarkSize32 },
                
                // Size variant icons
                new { Name = "icon_large.png", IsDark = false, Type = IconType.Large },
                new { Name = "icon_large.dark.png", IsDark = true, Type = IconType.DarkLarge },
                new { Name = "icon_small.png", IsDark = false, Type = IconType.Small },
                new { Name = "icon_small.dark.png", IsDark = true, Type = IconType.DarkSmall }
            };

            foreach (var iconInfo in iconData)
            {
                var iconPath = Path.Combine(tempDir, iconInfo.Name);
                CreateTestIcon(iconPath, 32, 32, iconInfo.IsDark ? Color.Orange : Color.Blue);
                _createdTestFiles.Add(iconPath);

                var icon = new ComponentIcon(iconPath);
                collection.Add(icon);
                
                TestContext.Out.WriteLine($"Added icon: {iconInfo.Name} (Dark: {icon.IsDark}, Type: {icon.Type})");
                
                // Verify the icon properties match expectations
                Assert.AreEqual(iconInfo.IsDark, icon.IsDark, $"Icon {iconInfo.Name} dark detection mismatch");
                Assert.AreEqual(iconInfo.Type, icon.Type, $"Icon {iconInfo.Name} type classification mismatch");
            }

            // Test collection properties
            TestContext.Out.WriteLine($"Total icons: {collection.Count}");
            TestContext.Out.WriteLine($"Has dark icons: {collection.HasDarkIcons}");
            TestContext.Out.WriteLine($"Has light icons: {collection.HasLightIcons}");
            TestContext.Out.WriteLine($"Light icons count: {collection.LightIcons.Count()}");
            TestContext.Out.WriteLine($"Dark icons count: {collection.DarkIcons.Count()}");

            // Verify the collection has both light and dark icons
            Assert.IsTrue(collection.HasDarkIcons, "Collection should have dark icons");
            Assert.IsTrue(collection.HasLightIcons, "Collection should have light icons");
            Assert.AreEqual(5, collection.LightIcons.Count(), "Should have 5 light icons");
            Assert.AreEqual(5, collection.DarkIcons.Count(), "Should have 5 dark icons");

            // Test primary icon selection
            var primaryIcon = collection.PrimaryIcon;
            var primaryDarkIcon = collection.PrimaryDarkIcon;
            
            TestContext.Out.WriteLine($"Primary icon: {primaryIcon?.FileName} (Type: {primaryIcon?.Type})");
            TestContext.Out.WriteLine($"Primary dark icon: {primaryDarkIcon?.FileName} (Type: {primaryDarkIcon?.Type})");

            Assert.IsNotNull(primaryIcon, "Should have a primary icon");
            Assert.IsNotNull(primaryDarkIcon, "Should have a primary dark icon");
            Assert.AreEqual(IconType.Standard, primaryIcon.Type, "Primary icon should be Standard type");
            Assert.AreEqual(IconType.DarkStandard, primaryDarkIcon.Type, "Primary dark icon should be DarkStandard type");

            // Test theme-specific size-based icon selection
            TestContext.Out.WriteLine("\n--- Testing Theme-Specific Size Selection ---");
            
            // Test light theme selection (isDark = false)
            var light16 = collection.GetBySize(16, false);
            var light32 = collection.GetBySize(32, false);
            
            TestContext.Out.WriteLine($"Light 16px icon: {light16?.FileName} (Dark: {light16?.IsDark})");
            TestContext.Out.WriteLine($"Light 32px icon: {light32?.FileName} (Dark: {light32?.IsDark})");

            Assert.IsNotNull(light16, "Should find light 16px icon");
            Assert.IsNotNull(light32, "Should find light 32px icon");
            Assert.IsFalse(light16.IsDark, "Light 16px icon should not be dark");
            Assert.IsFalse(light32.IsDark, "Light 32px icon should not be dark");
            Assert.AreEqual(IconType.Size16, light16.Type, "Light 16px icon should be Size16 type");
            Assert.AreEqual(IconType.Size32, light32.Type, "Light 32px icon should be Size32 type");

            // Test dark theme selection (isDark = true)
            var dark16 = collection.GetBySize(16, true);
            var dark32 = collection.GetBySize(32, true);
            
            TestContext.Out.WriteLine($"Dark 16px icon: {dark16?.FileName} (Dark: {dark16?.IsDark})");
            TestContext.Out.WriteLine($"Dark 32px icon: {dark32?.FileName} (Dark: {dark32?.IsDark})");

            Assert.IsNotNull(dark16, "Should find dark 16px icon");
            Assert.IsNotNull(dark32, "Should find dark 32px icon");
            Assert.IsTrue(dark16.IsDark, "Dark 16px icon should be dark");
            Assert.IsTrue(dark32.IsDark, "Dark 32px icon should be dark");
            Assert.AreEqual(IconType.DarkSize16, dark16.Type, "Dark 16px icon should be DarkSize16 type");
            Assert.AreEqual(IconType.DarkSize32, dark32.Type, "Dark 32px icon should be DarkSize32 type");

            // Test fallback behavior when theme-specific icons are not available
            TestContext.Out.WriteLine("\n--- Testing Fallback Behavior ---");
            
            // Test dark theme request when no dark 64px icon exists
            var dark64 = collection.GetBySize(64, true);
            TestContext.Out.WriteLine($"Dark 64px icon (should be null): {dark64?.FileName}");
            Assert.IsNull(dark64, "Should not find dark 64px icon as it doesn't exist");

            Assert.Pass("Theme-aware icon selection test completed successfully.");
        }

        private ParsedComponent CreateMockComponentWithIcons(string tempDir)
        {
            var component = new ParsedComponent
            {
                Name = "MockComponent",
                DisplayName = "Mock Component",
                Type = CommandComponentType.PushButton,
                Icons = new ComponentIconCollection()
            };

            // Create a set of test icons
            var iconFiles = new[]
            {
                "icon.png",         // Standard light
                "icon.dark.png",    // Standard dark
                "icon_16.png",      // Size16 light
                "icon_16.dark.png", // Size16 dark
                "icon_32.png",      // Size32 light
                "icon_32.dark.png"  // Size32 dark
            };

            foreach (var iconFile in iconFiles)
            {
                var iconPath = Path.Combine(tempDir, iconFile);
                var isDark = iconFile.Contains("dark");
                CreateTestIcon(iconPath, 32, 32, isDark ? Color.Orange : Color.Blue);
                _createdTestFiles.Add(iconPath);

                var icon = new ComponentIcon(iconPath);
                component.Icons.Add(icon);
            }

            return component;
        }

        private void TestIconSelectionScenario(ParsedComponent component, string scenarioName, bool simulateDarkTheme)
        {
            TestContext.Out.WriteLine($"\n--- {scenarioName} ---");
            
            // Simulate the logic that would be used in UIManager.GetBestIconForSize
            // Note: We can't actually call UIManager methods in unit tests due to Revit dependencies
            
            var isDarkTheme = simulateDarkTheme;
            TestContext.Out.WriteLine($"Simulated theme: {(isDarkTheme ? "Dark" : "Light")}");
            
            // Test size-based selection with theme preference
            for (int size = 16; size <= 32; size += 16)
            {
                var themeSpecificIcon = component.Icons.GetBySize(size, isDarkTheme);
                var fallbackIcon = component.Icons.GetBySize(size, false); // Light fallback
                
                var selectedIcon = themeSpecificIcon ?? fallbackIcon;
                
                TestContext.Out.WriteLine($"  Size {size}px: {selectedIcon?.FileName} " +
                                         $"(Dark: {selectedIcon?.IsDark}, Type: {selectedIcon?.Type})");
                
                if (isDarkTheme && component.Icons.HasDarkIcons)
                {
                    // In dark theme, should prefer dark icons when available
                    if (themeSpecificIcon != null)
                    {
                        Assert.IsTrue(selectedIcon.IsDark, 
                            $"In dark theme, should select dark icon for size {size}px when available");
                    }
                }
                else
                {
                    // In light theme, should use light icons
                    if (selectedIcon != null)
                    {
                        Assert.IsFalse(selectedIcon.IsDark, 
                            $"In light theme, should select light icon for size {size}px");
                    }
                }
            }
            
            // Test primary icon selection with theme preference
            var primaryIcon = component.Icons.PrimaryIcon;
            var primaryDarkIcon = component.Icons.PrimaryDarkIcon;
            var selectedPrimary = (isDarkTheme && primaryDarkIcon != null) ? primaryDarkIcon : primaryIcon;
            
            TestContext.Out.WriteLine($"  Primary: {selectedPrimary?.FileName} " +
                                     $"(Dark: {selectedPrimary?.IsDark}, Type: {selectedPrimary?.Type})");
            
            if (isDarkTheme && primaryDarkIcon != null)
            {
                Assert.IsTrue(selectedPrimary.IsDark, "In dark theme, should prefer primary dark icon when available");
                Assert.AreEqual(IconType.DarkStandard, selectedPrimary.Type, "Primary dark icon should be DarkStandard type");
            }
            else if (primaryIcon != null)
            {
                Assert.IsFalse(selectedPrimary.IsDark, "Should fall back to light primary icon");
                Assert.AreEqual(IconType.Standard, selectedPrimary.Type, "Primary light icon should be Standard type");
            }
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
                if (fileName.Contains("dark"))
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

        // Helper method to get icon type priority (copied from ExtensionParser for testing)
        private int GetIconTypePriority(IconType iconType)
        {
            switch (iconType)
            {
                case IconType.Standard:
                    return 1;
                case IconType.DarkStandard:
                    return 2;
                case IconType.Size32:
                    return 3;
                case IconType.DarkSize32:
                    return 4;
                case IconType.Size16:
                    return 5;
                case IconType.DarkSize16:
                    return 6;
                case IconType.Size64:
                    return 7;
                case IconType.DarkSize64:
                    return 8;
                case IconType.Large:
                    return 9;
                case IconType.DarkLarge:
                    return 10;
                case IconType.Small:
                    return 11;
                case IconType.DarkSmall:
                    return 12;
                case IconType.Button:
                    return 13;
                case IconType.DarkButton:
                    return 14;
                case IconType.Command:
                    return 15;
                case IconType.DarkCommand:
                    return 16;
                case IconType.Other:
                    return 17;
                case IconType.DarkOther:
                    return 18;
                default:
                    return 19;
            }
        }
    }
}