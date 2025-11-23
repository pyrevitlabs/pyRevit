using pyRevitExtensionParser;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;
using System.Drawing.Imaging;

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
                TestContext.Out.WriteLine($"  Directory: {component.Directory}");
                TestContext.Out.WriteLine($"  Total icons: {component.Icons.Count}");
                TestContext.Out.WriteLine($"  Light icons: {component.Icons.LightIcons.Count()}");
                TestContext.Out.WriteLine($"  Dark icons: {component.Icons.DarkIcons.Count()}");
                TestContext.Out.WriteLine($"  Has dark icons: {component.Icons.HasDarkIcons}");
                
                foreach (var icon in component.Icons)
                {
                    TestContext.Out.WriteLine($"    - {icon.FileName} (Type: {icon.Type}, Dark: {icon.IsDark})");
                }
            }
            
            // If we found components with dark icons, validate them
            if (componentsWithDarkIcons.Count > 0)
            {
                TestContext.Out.WriteLine($"\n=== Validating Components with Dark Icons ===");
                
                foreach (var component in componentsWithDarkIcons)
                {
                    TestContext.Out.WriteLine($"\nValidating: {component.DisplayName}");
                    
                    // Test basic dark icon properties
                    Assert.IsTrue(component.Icons.HasDarkIcons, $"{component.DisplayName} should have dark icons");
                    Assert.Greater(component.Icons.DarkIcons.Count(), 0, $"{component.DisplayName} should have at least one dark icon");
                    
                    // Test primary dark icon
                    var primaryDarkIcon = component.Icons.PrimaryDarkIcon;
                    if (primaryDarkIcon != null)
                    {
                        TestContext.Out.WriteLine($"  Primary dark icon: {primaryDarkIcon.FileName}");
                        Assert.IsTrue(primaryDarkIcon.IsDark, "Primary dark icon should be dark");
                        Assert.AreEqual(IconType.DarkStandard, primaryDarkIcon.Type, "Primary dark icon should be DarkStandard type");
                    }
                    
                    // Validate each dark icon
                    foreach (var darkIcon in component.Icons.DarkIcons)
                    {
                        TestContext.Out.WriteLine($"  Validating dark icon: {darkIcon.FileName}");
                        Assert.IsTrue(darkIcon.IsDark, $"Icon {darkIcon.FileName} should be marked as dark");
                        Assert.IsTrue(darkIcon.Type.ToString().StartsWith("Dark"), $"Icon {darkIcon.FileName} type should start with 'Dark'");
                        Assert.IsTrue(darkIcon.IsValid, $"Icon {darkIcon.FileName} should be valid");
                    }
                }
                
                Assert.Pass($"Dark icon validation completed successfully. Found {componentsWithDarkIcons.Count} component(s) with dark icons.");
            }
            else
            {
                // No dark icons found - just report what we found
                TestContext.Out.WriteLine("\n=== No Dark Icons Found ===");
                TestContext.Out.WriteLine("The extension doesn't currently have any components with dark icons.");
                TestContext.Out.WriteLine("This test validates that the parser can detect dark icons when they exist.");
                
                if (componentsWithIcons.Count > 0)
                {
                    TestContext.Out.WriteLine($"\nFound {componentsWithIcons.Count} component(s) with light icons:");
                    foreach (var component in componentsWithIcons.Take(5)) // Show first 5
                    {
                        TestContext.Out.WriteLine($"  - {component.DisplayName}: {component.Icons.Count} icon(s)");
                    }
                }
                
                Assert.Inconclusive("No dark icons found in the extension. Test skipped.");
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
                    if (themeSpecificIcon != null && selectedIcon != null)
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
            
            if (isDarkTheme && primaryDarkIcon != null && selectedPrimary != null)
            {
                Assert.IsTrue(selectedPrimary.IsDark, "In dark theme, should prefer primary dark icon when available");
                Assert.AreEqual(IconType.DarkStandard, selectedPrimary.Type, "Primary dark icon should be DarkStandard type");
            }
            else if (primaryIcon != null && selectedPrimary != null)
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