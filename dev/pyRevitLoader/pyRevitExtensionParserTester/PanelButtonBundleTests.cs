using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;
using System;
using System.Collections.Generic;
using System.Linq;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class PanelButtonBundleTests
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
        public void TestPanelButtonWithoutBundle()
        {
            if (_installedExtensions == null)
            {
                Assert.Fail("No test extensions loaded");
                return;
            }

            TestContext.Out.WriteLine("=== Testing Panel Button Without Bundle File ===");
            
            foreach (var extension in _installedExtensions)
            {
                var panelButton = FindComponentRecursively(extension, "DebugDialogConfig");
                if (panelButton != null)
                {
                    TestContext.Out.WriteLine($"Panel Button: {panelButton.DisplayName}");
                    TestContext.Out.WriteLine($"Name: {panelButton.Name}");
                    TestContext.Out.WriteLine($"Type: {panelButton.Type}");
                    TestContext.Out.WriteLine($"Script Path: {panelButton.ScriptPath}");
                    TestContext.Out.WriteLine($"Bundle File: {panelButton.BundleFile ?? "None"}");
                    TestContext.Out.WriteLine($"Title: {panelButton.Title ?? "None"}");
                    TestContext.Out.WriteLine($"Tooltip: {panelButton.Tooltip ?? "None"}");
                    TestContext.Out.WriteLine($"Author: {panelButton.Author ?? "None"}");
                    
                    // Verify basic panel button properties
                    Assert.AreEqual(CommandComponentType.PanelButton, panelButton.Type);
                    Assert.IsNotNull(panelButton.ScriptPath);
                    Assert.IsTrue(panelButton.ScriptPath.EndsWith("script.py"));
                    Assert.AreEqual("Debug Dialog Config", panelButton.DisplayName);
                    
                    // Should have no bundle file initially
                    Assert.IsNull(panelButton.BundleFile);
                    
                    // Test completed successfully
                    return;
                }
            }
            
            Assert.Fail("DebugDialogConfig panel button not found");
        }

        [Test]
        public void TestPanelButtonWithSimpleBundle()
        {
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            var panelButtonPath = Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelOne.panel", "Debug Dialog Config.panelbutton");
            var bundlePath = Path.Combine(panelButtonPath, "bundle.yaml");
            
            var bundleContent = @"title:
  en_us: Panel Settings
tooltips:
  en_us: Configure panel display options
author: Test Framework
min_revit_ver: 2019
";

            try
            {
                File.WriteAllText(bundlePath, bundleContent);
                _createdTestFiles.Add(bundlePath);
                
                // Re-parse extensions
                var extensions = ParseInstalledExtensions(new[] { testBundlePath });
                
                TestContext.Out.WriteLine("=== Testing Panel Button With Simple Bundle ===");
                
                foreach (var extension in extensions)
                {
                    var panelButton = FindComponentRecursively(extension, "DebugDialogConfig");
                    if (panelButton != null)
                    {
                        TestContext.Out.WriteLine($"Panel Button: {panelButton.DisplayName}");
                        TestContext.Out.WriteLine($"Bundle File: {panelButton.BundleFile}");
                        TestContext.Out.WriteLine($"Title: {panelButton.Title}");
                        TestContext.Out.WriteLine($"Tooltip: {panelButton.Tooltip}");
                        TestContext.Out.WriteLine($"Author: {panelButton.Author}");
                        
                        // Verify bundle data was parsed
                        Assert.IsNotNull(panelButton.BundleFile);
                        Assert.IsTrue(File.Exists(panelButton.BundleFile));
                        Assert.AreEqual("Panel Settings", panelButton.Title);
                        Assert.AreEqual("Configure panel display options", panelButton.Tooltip);
                        Assert.AreEqual("Test Framework", panelButton.Author);
                        
                        // Test completed successfully
                        return;
                    }
                }
                
                Assert.Fail("Panel button not found after adding bundle");
            }
            catch (NUnit.Framework.SuccessException)
            {
                // Re-throw success exceptions
                throw;
            }
            catch (Exception ex)
            {
                Assert.Fail($"Test failed with exception: {ex.Message}");
            }
        }

        [Test]
        public void TestPanelButtonWithMultilingualBundle()
        {
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            var panelButtonPath = Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelOne.panel", "Debug Dialog Config.panelbutton");
            var bundlePath = Path.Combine(panelButtonPath, "bundle.yaml");
            
            var bundleContent = @"title:
  en_us: Panel Configuration
  fr: Configuration du Panneau
  de: Panel-Konfiguration
tooltips:
  en_us: >-
    This panel button allows you to configure
    various display and behavior options for
    the current panel.
  fr: >-
    Ce bouton de panneau vous permet de configurer
    diverses options d'affichage et de comportement
    pour le panneau actuel.
author: Multilingual Test
min_revit_ver: 2020
";

            try
            {
                File.WriteAllText(bundlePath, bundleContent);
                _createdTestFiles.Add(bundlePath);
                
                // Re-parse extensions
                var extensions = ParseInstalledExtensions(new[] { testBundlePath });
                
                TestContext.Out.WriteLine("=== Testing Panel Button With Multilingual Bundle ===");
                
                foreach (var extension in extensions)
                {
                    var panelButton = FindComponentRecursively(extension, "DebugDialogConfig");
                    if (panelButton != null)
                    {
                        TestContext.Out.WriteLine($"Panel Button: {panelButton.DisplayName}");
                        TestContext.Out.WriteLine($"Title: {panelButton.Title}");
                        TestContext.Out.WriteLine($"Tooltip: {panelButton.Tooltip}");
                        TestContext.Out.WriteLine($"Author: {panelButton.Author}");
                        
                        // Should default to en_us locale
                        Assert.AreEqual("Panel Configuration", panelButton.Title);
                        Assert.IsTrue(panelButton.Tooltip.Contains("panel button"));
                        Assert.IsTrue(panelButton.Tooltip.Contains("configure"));
                        Assert.AreEqual("Multilingual Test", panelButton.Author);
                        
                        // Verify multiline tooltip is properly parsed (no YAML artifacts)
                        Assert.IsFalse(panelButton.Tooltip.Contains("en_us:"));
                        Assert.IsFalse(panelButton.Tooltip.Contains(">-"));
                        
                        // Test completed successfully
                        return;
                    }
                }
                
                Assert.Fail("Panel button not found after adding multilingual bundle");
            }
            catch (NUnit.Framework.SuccessException)
            {
                // Re-throw success exceptions
                throw;
            }
            catch (Exception ex)
            {
                Assert.Fail($"Test failed with exception: {ex.Message}");
            }
        }

        [Test]
        public void TestPanelButtonWithComplexBundle()
        {
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            var panelButtonPath = Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelOne.panel", "Debug Dialog Config.panelbutton");
            var bundlePath = Path.Combine(panelButtonPath, "bundle.yaml");
            
            TestContext.Out.WriteLine($"Test bundle path: {testBundlePath}");
            TestContext.Out.WriteLine($"Path exists: {Directory.Exists(testBundlePath)}");
            TestContext.Out.WriteLine($"Panel button path exists: {Directory.Exists(panelButtonPath)}");
            
            var bundleContent = @"title:
  en_us: Advanced Panel Configuration
tooltips:
  en_us: >-
    This is an advanced panel configuration button that provides
    access to detailed settings for panel layout, behavior,
    and appearance customization.
    
    Features include:
    - Layout ordering
    - Visual themes
    - Behavior settings
    - Performance options
author: Advanced Test Suite
min_revit_ver: 2021
layout_order:
  - ""PanelOneButton1""
  - ""PanelOneButton2""
  - "">>>>>"" 
  - ""Debug Dialog Config""
";

            try
            {
                File.WriteAllText(bundlePath, bundleContent);
                _createdTestFiles.Add(bundlePath);
                
                TestContext.Out.WriteLine("=== Testing Panel Button With Complex Bundle ===");
                
                // Re-parse extensions with better error handling
                IEnumerable<ParsedExtension> extensions = null;
                try
                {
                    extensions = ParseInstalledExtensions(new[] { testBundlePath });
                    TestContext.Out.WriteLine("ParseInstalledExtensions call completed");
                }
                catch (Exception parseEx)
                {
                    Assert.Fail($"Failed to parse extensions: {parseEx.Message}");
                    return;
                }
                
                if (extensions == null)
                {
                    Assert.Fail("Extensions collection is null");
                    return;
                }
                
                // Use a more defensive enumeration approach
                List<ParsedExtension> extensionsList = new List<ParsedExtension>();
                try
                {
                    foreach (var ext in extensions)
                    {
                        if (ext != null)
                        {
                            extensionsList.Add(ext);
                        }
                        else
                        {
                            TestContext.Out.WriteLine("Warning: Found null extension during enumeration");
                        }
                    }
                    TestContext.Out.WriteLine($"Extension count: {extensionsList.Count}");
                }
                catch (Exception enumEx)
                {
                    Assert.Fail($"Failed to enumerate extensions: {enumEx.Message}\nStack trace: {enumEx.StackTrace}");
                    return;
                }
                
                if (extensionsList.Count == 0)
                {
                    Assert.Fail($"No extensions found at path: {testBundlePath}");
                    return;
                }
                
                foreach (var extension in extensionsList)
                {
                    TestContext.Out.WriteLine($"Extension: {extension.Name}");
                    
                    var panelButton = FindComponentRecursively(extension, "DebugDialogConfig");
                    if (panelButton != null)
                    {
                        TestContext.Out.WriteLine($"Panel Button: {panelButton.DisplayName}");
                        TestContext.Out.WriteLine($"Title: {panelButton.Title}");
                        TestContext.Out.WriteLine($"Author: {panelButton.Author}");
                        TestContext.Out.WriteLine($"Tooltip Length: {panelButton.Tooltip?.Length ?? 0} characters");
                        TestContext.Out.WriteLine($"Layout Order: {panelButton.LayoutOrder?.Count ?? 0} items");
                        
                        if (panelButton.LayoutOrder != null)
                        {
                            TestContext.Out.WriteLine("Layout Order Items:");
                            foreach (var item in panelButton.LayoutOrder)
                            {
                                TestContext.Out.WriteLine($"  - {item}");
                            }
                        }
                        
                        // Verify complex bundle data
                        Assert.AreEqual("Advanced Panel Configuration", panelButton.Title);
                        Assert.AreEqual("Advanced Test Suite", panelButton.Author);
                        Assert.IsNotNull(panelButton.Tooltip);
                        Assert.IsTrue(panelButton.Tooltip.Contains("advanced panel configuration"));
                        Assert.IsTrue(panelButton.Tooltip.Contains("Features include"));
                        
                        // Verify layout order parsing
                        Assert.IsNotNull(panelButton.LayoutOrder);
                        Assert.Greater(panelButton.LayoutOrder.Count, 0);
                        Assert.Contains("PanelOneButton1", panelButton.LayoutOrder);
                        Assert.Contains(">>>>>", panelButton.LayoutOrder);
                        
                        // Test completed successfully
                        return;
                    }
                    else
                    {
                        TestContext.Out.WriteLine("DebugDialogConfig component not found, available components:");
                        PrintAllComponents(extension, 0);
                    }
                }
                
                Assert.Fail("Panel button not found after adding complex bundle");
            }
            catch (NUnit.Framework.SuccessException)
            {
                // Re-throw success exceptions
                throw;
            }
            catch (Exception ex)
            {
                TestContext.Out.WriteLine($"Exception details: {ex}");
                Assert.Fail($"Test failed with exception: {ex.Message}");
            }
        }

        [Test]
        public void TestCreateNewPanelButton()
        {
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            var newPanelButtonPath = Path.Combine(testBundlePath, "TestBundleTab.tab", "TestPanelTwo.panel", "Test Panel Config.panelbutton");
            var scriptPath = Path.Combine(newPanelButtonPath, "script.py");
            var bundlePath = Path.Combine(newPanelButtonPath, "bundle.yaml");
            
            var scriptContent = @"""""""Test panel configuration button.""""""

from pyrevit import script
logger = script.get_logger()

__title__ = """"""Test Panel Config""""""
__author__ = """"""Test Creator""""""
__doc__ = """"""Test panel configuration functionality.""""""

logger.info('Panel config button executed')
print('Panel configuration executed successfully.')
";

            var bundleContent = @"title:
  en_us: Test Panel Config
tooltips:
  en_us: Test panel configuration button
author: Test Creator
min_revit_ver: 2019
";

            try
            {
                Directory.CreateDirectory(newPanelButtonPath);
                File.WriteAllText(scriptPath, scriptContent);
                File.WriteAllText(bundlePath, bundleContent);
                _createdTestFiles.Add(scriptPath);
                _createdTestFiles.Add(bundlePath);
                
                // Re-parse extensions
                var extensions = ParseInstalledExtensions(new[] { testBundlePath });
                
                TestContext.Out.WriteLine("=== Testing New Panel Button Creation ===");
                
                foreach (var extension in extensions)
                {
                    var newPanelButton = FindComponentRecursively(extension, "TestPanelConfig");
                    if (newPanelButton != null)
                    {
                        TestContext.Out.WriteLine($"New Panel Button: {newPanelButton.DisplayName}");
                        TestContext.Out.WriteLine($"Name: {newPanelButton.Name}");
                        TestContext.Out.WriteLine($"Type: {newPanelButton.Type}");
                        TestContext.Out.WriteLine($"Script Path: {newPanelButton.ScriptPath}");
                        TestContext.Out.WriteLine($"Bundle File: {newPanelButton.BundleFile}");
                        TestContext.Out.WriteLine($"Title: {newPanelButton.Title}");
                        TestContext.Out.WriteLine($"Tooltip: {newPanelButton.Tooltip}");
                        TestContext.Out.WriteLine($"Author: {newPanelButton.Author}");
                        
                        // Verify new panel button properties
                        Assert.AreEqual(CommandComponentType.PanelButton, newPanelButton.Type);
                        Assert.AreEqual("Test Panel Config", newPanelButton.DisplayName);
                        Assert.IsNotNull(newPanelButton.ScriptPath);
                        Assert.IsNotNull(newPanelButton.BundleFile);
                        Assert.AreEqual("Test Panel Config", newPanelButton.Title);
                        Assert.AreEqual("Test panel configuration button", newPanelButton.Tooltip);
                        Assert.AreEqual("Test Creator", newPanelButton.Author);
                        
                        // Test completed successfully
                        return;
                    }
                }
                
                Assert.Fail("New panel button not found after creation");
            }
            catch (NUnit.Framework.SuccessException)
            {
                // Re-throw success exceptions
                throw;
            }
            catch (Exception ex)
            {
                Assert.Fail($"Test failed with exception: {ex.Message}");
            }
            finally
            {
                // Clean up directory
                try
                {
                    if (Directory.Exists(newPanelButtonPath))
                    {
                        Directory.Delete(newPanelButtonPath, true);
                    }
                }
                catch
                {
                    // Ignore cleanup errors
                }
            }
        }

        // Helper method to find components recursively
        private ParsedComponent FindComponentRecursively(ParsedComponent parent, string componentName)
        {
            if (parent == null || string.IsNullOrEmpty(componentName))
                return null;
                
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

        // Helper method to print all components recursively for debugging
        private void PrintAllComponents(ParsedComponent component, int depth)
        {
            if (component == null)
            {
                var indent = new string(' ', depth * 2);
                TestContext.Out.WriteLine($"{indent}- NULL COMPONENT");
                return;
            }
            
            var indent2 = new string(' ', depth * 2);
            TestContext.Out.WriteLine($"{indent2}- {component.Name ?? "NULL"} ({component.DisplayName ?? "NULL"}) [{component.Type}]");
            
            if (component.Children != null)
            {
                foreach (var child in component.Children)
                {
                    PrintAllComponents(child, depth + 1);
                }
            }
        }
    }
}