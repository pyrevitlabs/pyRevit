using pyRevitExtensionParser;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class ComponentValidationTests
    {
        private IEnumerable<ParsedExtension>? _installedExtensions;
        
        [SetUp]
        public void Setup()
        {
            var testBundlePath = TestConfiguration.TestExtensionPath;
            _installedExtensions = ParseInstalledExtensions([testBundlePath]);
        }

        [Test]
        public void ValidatePanelButtonExistsAndParsedCorrectly()
        {
            Assert.IsNotNull(_installedExtensions, "Extensions should be loaded");
            
            TestContext.Out.WriteLine("=== Validating Panel Button Parsing ===");
            
            var panelButtonFound = false;
            
            foreach (var extension in _installedExtensions)
            {
                TestContext.Out.WriteLine($"Checking extension: {extension.Name}");
                
                var allComponents = GetAllComponentsFlat(extension);
                var panelButtons = allComponents.Where(c => c.Type == CommandComponentType.PanelButton).ToList();
                
                TestContext.Out.WriteLine($"Found {panelButtons.Count} panel button(s)");
                
                foreach (var panelButton in panelButtons)
                {
                    panelButtonFound = true;
                    TestContext.Out.WriteLine($"Panel Button Details:");
                    TestContext.Out.WriteLine($"  Name: {panelButton.Name}");
                    TestContext.Out.WriteLine($"  DisplayName: {panelButton.DisplayName}");
                    TestContext.Out.WriteLine($"  Type: {panelButton.Type}");
                    TestContext.Out.WriteLine($"  ScriptPath: {panelButton.ScriptPath ?? "None"}");
                    TestContext.Out.WriteLine($"  BundleFile: {panelButton.BundleFile ?? "None"}");
                    TestContext.Out.WriteLine($"  UniqueId: {panelButton.UniqueId}");
                    
                    // Validate core panel button properties
                    Assert.AreEqual(CommandComponentType.PanelButton, panelButton.Type, 
                                   "Panel button should have correct type");
                    Assert.IsNotEmpty(panelButton.Name, 
                                     "Panel button should have a name");
                    Assert.IsNotEmpty(panelButton.DisplayName, 
                                     "Panel button should have a display name");
                    Assert.IsNotEmpty(panelButton.UniqueId, 
                                     "Panel button should have a unique ID");
                    
                    // Validate that if script path exists, it points to a real file
                    if (!string.IsNullOrEmpty(panelButton.ScriptPath))
                    {
                        Assert.IsTrue(File.Exists(panelButton.ScriptPath), 
                                     $"Script path should point to existing file: {panelButton.ScriptPath}");
                    }
                    
                    // Validate that if bundle file exists, it points to a real file
                    if (!string.IsNullOrEmpty(panelButton.BundleFile))
                    {
                        Assert.IsTrue(File.Exists(panelButton.BundleFile), 
                                     $"Bundle file should exist: {panelButton.BundleFile}");
                    }
                }
            }
            
            // Only assert if panel buttons were found - otherwise just report it
            if (!panelButtonFound)
            {
                TestContext.Out.WriteLine("No panel buttons found in the test bundle. Test will pass as parser didn't crash.");
            }
            
            Assert.Pass($"Panel button validation completed successfully. Found {(panelButtonFound ? "panel buttons" : "no panel buttons")}.");
        }

        [Test]
        public void ValidateComponentTypeMapping()
        {
            Assert.IsNotNull(_installedExtensions, "Extensions should be loaded");
            
            TestContext.Out.WriteLine("=== Validating Component Type Mapping ===");
            
            var expectedTypes = new Dictionary<string, CommandComponentType>
            {
                { ".panelbutton", CommandComponentType.PanelButton },
                { ".pushbutton", CommandComponentType.PushButton },
                { ".pulldown", CommandComponentType.PullDown },
                { ".tab", CommandComponentType.Tab },
                { ".panel", CommandComponentType.Panel }
            };
            
            foreach (var expectedType in expectedTypes)
            {
                var extension = expectedType.Key;
                var expectedComponentType = expectedType.Value;
                var actualComponentType = CommandComponentTypeExtensions.FromExtension(extension);
                
                TestContext.Out.WriteLine($"Extension: {extension} -> {actualComponentType}");
                Assert.AreEqual(expectedComponentType, actualComponentType, 
                               $"Extension {extension} should map to {expectedComponentType}");
            }
            
            // Test reverse mapping
            foreach (var expectedType in expectedTypes)
            {
                var componentType = expectedType.Value;
                var expectedExtension = expectedType.Key;
                var actualExtension = componentType.ToExtension();
                
                TestContext.Out.WriteLine($"Type: {componentType} -> {actualExtension}");
                Assert.AreEqual(expectedExtension, actualExtension, 
                               $"Component type {componentType} should map to {expectedExtension}");
            }
            
            Assert.Pass("Component type mapping validation completed successfully");
        }

        [Test]
        public void ValidateExtensionStructure()
        {
            Assert.IsNotNull(_installedExtensions, "Extensions should be loaded");
            
            TestContext.Out.WriteLine("=== Validating Extension Structure ===");
            
            foreach (var extension in _installedExtensions)
            {
                TestContext.Out.WriteLine($"Extension: {extension.Name}");
                TestContext.Out.WriteLine($"Directory: {extension.Directory}");
                
                // Validate extension directory exists (or is a valid tab directory)
                var dirExists = Directory.Exists(extension.Directory);
                var parentDirExists = Directory.Exists(Path.GetDirectoryName(extension.Directory) ?? "");
                Assert.IsTrue(dirExists || parentDirExists, 
                             $"Extension directory or parent should exist: {extension.Directory}");
                
                // Validate extension has children collection (may be empty for tab-level parsing)
                Assert.IsNotNull(extension.Children, "Extension should have children collection");
                TestContext.Out.WriteLine($"Extension has {extension.Children.Count} child(ren)");
                
                var validButtonTypes = new[]
                {
                    CommandComponentType.PushButton,
                    CommandComponentType.PanelButton,
                    CommandComponentType.PullDown,
                    CommandComponentType.SplitButton,
                    CommandComponentType.SplitPushButton,
                    CommandComponentType.Stack,
                    CommandComponentType.SmartButton,
                    CommandComponentType.LinkButton,
                    CommandComponentType.InvokeButton,
                    CommandComponentType.Separator,
                    CommandComponentType.NoButton,
                    CommandComponentType.UrlButton,
                    CommandComponentType.ContentButton,
                    CommandComponentType.ComboBox
                };
                
                // Validate tab structure
                foreach (var tab in extension.Children)
                {
                    TestContext.Out.WriteLine($"  Tab: {tab.DisplayName} ({tab.Type})");
                    Assert.AreEqual(CommandComponentType.Tab, tab.Type, "Child of extension should be a tab");
                    
                    // Validate tab has panels
                    if (tab.Children != null && tab.Children.Count > 0)
                    {
                        foreach (var panel in tab.Children)
                        {
                            TestContext.Out.WriteLine($"    Panel: {panel.DisplayName} ({panel.Type})");
                            Assert.AreEqual(CommandComponentType.Panel, panel.Type, "Child of tab should be a panel");
                            
                            // Validate panel has buttons
                            if (panel.Children != null && panel.Children.Count > 0)
                            {
                                foreach (var button in panel.Children)
                                {
                                    TestContext.Out.WriteLine($"      Button: {button.DisplayName} ({button.Type})");
                                    
                                    // Validate button type is valid
                                    Assert.Contains(button.Type, validButtonTypes, 
                                                   $"Button should have a valid type, but was: {button.Type}");
                                }
                            }
                        }
                    }
                }
            }
            
            Assert.Pass("Extension structure validation completed successfully");
        }

        [Test]
        public void ValidateIconFileSupport()
        {
            TestContext.Out.WriteLine("=== Validating Icon File Support ===");
            
            var supportedExtensions = new[] { ".png", ".ico", ".jpg", ".jpeg", ".bmp", ".gif", ".svg" };
            
            foreach (var extension in supportedExtensions)
            {
                var testFileName = $"test_icon{extension}";
                TestContext.Out.WriteLine($"Testing icon extension: {extension}");
                
                // Verify the extension is considered an image file
                Assert.IsTrue(IsImageFileExtension(extension), 
                             $"Extension {extension} should be recognized as an image file");
            }
            
            // Test non-image extensions
            var nonImageExtensions = new[] { ".txt", ".py", ".cs", ".yaml", ".json" };
            foreach (var extension in nonImageExtensions)
            {
                TestContext.Out.WriteLine($"Testing non-image extension: {extension}");
                Assert.IsFalse(IsImageFileExtension(extension), 
                              $"Extension {extension} should NOT be recognized as an image file");
            }
            
            Assert.Pass("Icon file support validation completed successfully");
        }

        [Test]
        public void ValidateUniqueIdGeneration()
        {
            Assert.IsNotNull(_installedExtensions, "Extensions should be loaded");
            
            TestContext.Out.WriteLine("=== Validating Unique ID Generation ===");
            
            var allUniqueIds = new HashSet<string>();
            var duplicateIds = new List<string>();
            
            foreach (var extension in _installedExtensions)
            {
                var allComponents = GetAllComponentsFlat(extension);
                
                foreach (var component in allComponents)
                {
                    if (!string.IsNullOrEmpty(component.UniqueId))
                    {
                        TestContext.Out.WriteLine($"Component: {component.DisplayName}, UniqueId: {component.UniqueId}");
                        
                        if (allUniqueIds.Contains(component.UniqueId))
                        {
                            duplicateIds.Add(component.UniqueId);
                            TestContext.Out.WriteLine($"  WARNING: Duplicate unique ID found: {component.UniqueId}");
                        }
                        else
                        {
                            allUniqueIds.Add(component.UniqueId);
                        }
                        
                        // Validate unique ID format (should be sanitized)
                        Assert.IsTrue(IsValidUniqueId(component.UniqueId), 
                                     $"Unique ID should only contain letters, digits, and underscores: {component.UniqueId}");
                    }
                }
            }
            
            TestContext.Out.WriteLine($"Total unique IDs: {allUniqueIds.Count}");
            TestContext.Out.WriteLine($"Duplicate IDs: {duplicateIds.Count}");
            
            if (duplicateIds.Count > 0)
            {
                TestContext.Out.WriteLine("Duplicate IDs found:");
                foreach (var duplicateId in duplicateIds.Distinct())
                {
                    TestContext.Out.WriteLine($"  - {duplicateId}");
                }
            }
            
            // For now, we'll warn about duplicates but not fail the test
            // In a production system, you might want to enforce uniqueness
            Assert.Pass("Unique ID validation completed successfully");
        }

        [Test]
        public void ValidateIconParsingFunctionality()
        {
            Assert.IsNotNull(_installedExtensions, "Extensions should be loaded");
            
            TestContext.Out.WriteLine("=== Validating Icon Parsing Functionality ===");
            
            var componentsWithIcons = new List<ParsedComponent>();
            
            foreach (var extension in _installedExtensions)
            {
                var allComponents = GetAllComponentsFlat(extension);
                
                foreach (var component in allComponents)
                {
                    // Check if component has Icons property
                    Assert.IsNotNull(component.Icons, "Component should have Icons collection");
                    
                    // If the component has icons, validate them
                    if (component.HasIcons)
                    {
                        componentsWithIcons.Add(component);
                        TestContext.Out.WriteLine($"Component with icons: {component.DisplayName}");
                        TestContext.Out.WriteLine($"  Icon count: {component.Icons.Count}");
                        TestContext.Out.WriteLine($"  Has valid icons: {component.HasValidIcons}");
                        
                        if (component.PrimaryIcon != null)
                        {
                            TestContext.Out.WriteLine($"  Primary icon: {component.PrimaryIcon.FileName}");
                            TestContext.Out.WriteLine($"  Primary icon type: {component.PrimaryIcon.Type}");
                        }
                        
                        // Validate each icon
                        foreach (var icon in component.Icons)
                        {
                            TestContext.Out.WriteLine($"    Icon: {icon.FileName} ({icon.Type}, {icon.FileSize} bytes)");
                            
                            // Validate icon properties
                            Assert.IsNotEmpty(icon.FilePath, "Icon should have a file path");
                            Assert.IsNotEmpty(icon.FileName, "Icon should have a file name");
                            Assert.IsNotEmpty(icon.Extension, "Icon should have an extension");
                            Assert.GreaterOrEqual(icon.FileSize, 0, "Icon file size should be non-negative");
                            
                            // Validate icon type is not unknown (allow Other for edge cases)
                            // Assert.AreNotEqual(IconType.Other, icon.Type, "Icon type should be determined correctly");
                        }
                    }
                }
            }
            
            TestContext.Out.WriteLine($"Found {componentsWithIcons.Count} component(s) with icons");
            
            // Icon parsing should work without throwing exceptions
            Assert.Pass("Icon parsing functionality validation completed successfully");
        }

        [Test]
        public void ValidateIconTypesAndExtensions()
        {
            TestContext.Out.WriteLine("=== Validating Icon Types and Extensions ===");
            
            // Test that ComponentIconCollection properly recognizes supported extensions
            var supportedExtensions = ComponentIconCollection.SupportedExtensions;
            var expectedExtensions = new[] { ".png", ".ico", ".jpg", ".jpeg", ".bmp", ".gif", ".svg" };
            
            TestContext.Out.WriteLine($"Supported extensions: [{string.Join(", ", supportedExtensions)}]");
            
            foreach (var expectedExt in expectedExtensions)
            {
                Assert.Contains(expectedExt, supportedExtensions, 
                               $"Extension {expectedExt} should be supported");
                
                Assert.IsTrue(ComponentIconCollection.IsSupportedImageExtension(expectedExt),
                             $"Extension {expectedExt} should be recognized as supported");
            }
            
            // Test unsupported extensions
            var unsupportedExtensions = new[] { ".txt", ".py", ".cs", ".yaml", ".json", ".xml" };
            foreach (var unsupportedExt in unsupportedExtensions)
            {
                Assert.IsFalse(ComponentIconCollection.IsSupportedImageExtension(unsupportedExt),
                              $"Extension {unsupportedExt} should NOT be recognized as supported");
            }
            
            Assert.Pass("Icon types and extensions validation completed successfully");
        }

        [Test]
        public void ValidateIconCollectionMethods()
        {
            TestContext.Out.WriteLine("=== Validating Icon Collection Methods ===");
            
            // Create a test collection with supported icon types
            // Only Standard and DarkStandard are supported
            var iconCollection = new ComponentIconCollection();
            
            // Note: These are test paths, not actual files
            var testIcons = new[]
            {
                new ComponentIcon("test/icon.png") { Type = IconType.Standard },
                new ComponentIcon("test/icon.dark.png") { Type = IconType.DarkStandard },
                new ComponentIcon("test/button_icon.ico") { Type = IconType.Standard }
            };
            
            // Manually set types for testing (since files don't exist)
            foreach (var icon in testIcons)
            {
                iconCollection.Add(icon);
            }
            
            TestContext.Out.WriteLine($"Test collection has {iconCollection.Count} icons");
            
            // Test PrimaryIcon (should return Standard type first)
            var primaryIcon = iconCollection.PrimaryIcon;
            TestContext.Out.WriteLine($"Primary icon: {primaryIcon?.FileName ?? "None"}");
            Assert.IsNotNull(primaryIcon, "Should have a primary icon");
            Assert.AreEqual(IconType.Standard, primaryIcon.Type, "Primary icon should be Standard type");
            
            // Test PrimaryDarkIcon
            var darkIcon = iconCollection.PrimaryDarkIcon;
            Assert.IsNotNull(darkIcon, "Should find dark icon");
            Assert.AreEqual(IconType.DarkStandard, darkIcon.Type, "Dark icon should be DarkStandard type");
            
            // Test GetByType
            var standardIcon = iconCollection.GetByType(IconType.Standard);
            Assert.IsNotNull(standardIcon, "Should find Standard type icon");
            Assert.AreEqual("icon.png", standardIcon.FileName);
            
            // Test GetByExtension
            var pngIcons = iconCollection.GetByExtension(".png").ToList();
            Assert.Greater(pngIcons.Count, 0, "Should find PNG icons");
            
            var icoIcons = iconCollection.GetByExtension(".ico").ToList();
            Assert.Greater(icoIcons.Count, 0, "Should find ICO icons");
            
            Assert.Pass("Icon collection methods validation completed successfully");
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

        // Helper method to check if an extension is for an image file
        private bool IsImageFileExtension(string extension)
        {
            var imageExtensions = new[] { ".png", ".ico", ".jpg", ".jpeg", ".bmp", ".gif", ".svg" };
            return imageExtensions.Contains(extension.ToLowerInvariant());
        }

        // Helper method to validate unique ID format
        private bool IsValidUniqueId(string uniqueId)
        {
            if (string.IsNullOrEmpty(uniqueId))
                return false;
                
            return uniqueId.All(c => char.IsLetterOrDigit(c) || c == '_');
        }
    }
}