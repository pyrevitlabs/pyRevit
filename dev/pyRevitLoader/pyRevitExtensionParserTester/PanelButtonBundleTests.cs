using pyRevitExtensionParser;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;
using System.Text;

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
            var testBundlePath = TestConfiguration.TestExtensionPath;
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
        public void TestPushButtonWithoutBundle()
        {
            if (_installedExtensions == null)
            {
                Assert.Fail("No test extensions loaded");
                return;
            }

            TestContext.Out.WriteLine("=== Testing Push Button Without Bundle File ===");
            
            foreach (var extension in _installedExtensions)
            {
                var pushButton = FindComponentRecursively(extension, "Logs");
                if (pushButton != null)
                {
                    TestContext.Out.WriteLine($"Push Button: {pushButton.DisplayName}");
                    TestContext.Out.WriteLine($"Name: {pushButton.Name}");
                    TestContext.Out.WriteLine($"Type: {pushButton.Type}");
                    TestContext.Out.WriteLine($"Script Path: {pushButton.ScriptPath}");
                    TestContext.Out.WriteLine($"Bundle File: {pushButton.BundleFile ?? "None"}");
                    TestContext.Out.WriteLine($"Title: {pushButton.Title ?? "None"}");
                    TestContext.Out.WriteLine($"Tooltip: {pushButton.Tooltip ?? "None"}");
                    TestContext.Out.WriteLine($"Author: {pushButton.Author ?? "None"}");
                    
                    // Verify basic push button properties
                    Assert.AreEqual(CommandComponentType.PushButton, pushButton.Type);
                    Assert.IsNotNull(pushButton.ScriptPath);
                    Assert.IsTrue(pushButton.ScriptPath.EndsWith("script.py"));
                    Assert.AreEqual("Logs", pushButton.DisplayName);
                    
                    // Should have no bundle file
                    Assert.IsNull(pushButton.BundleFile);
                    
                    // Test completed successfully
                    return;
                }
            }
            
            Assert.Fail("Logs push button not found");
        }

        [Test]
        public void TestPanelButtonWithSimpleBundle()
        {
            if (_installedExtensions == null)
            {
                Assert.Fail("No test extensions loaded");
                return;
            }

            TestContext.Out.WriteLine("=== Testing Push Button With Simple Bundle ===");
            
            foreach (var extension in _installedExtensions)
            {
                var pushButton = FindComponentRecursively(extension, "SelectionTest");
                if (pushButton != null)
                {
                    TestContext.Out.WriteLine($"Push Button: {pushButton.DisplayName}");
                    TestContext.Out.WriteLine($"Name: {pushButton.Name}");
                    TestContext.Out.WriteLine($"Type: {pushButton.Type}");
                    TestContext.Out.WriteLine($"Bundle File: {pushButton.BundleFile ?? "None"}");
                    TestContext.Out.WriteLine($"Title: {pushButton.Title ?? "None"}");
                    TestContext.Out.WriteLine($"Tooltip: {pushButton.Tooltip ?? "None"}");
                    TestContext.Out.WriteLine($"Author: {pushButton.Author ?? "None"}");
                    
                    Assert.AreEqual(CommandComponentType.PushButton, pushButton.Type);
                    Assert.AreEqual("Selection Test", pushButton.DisplayName);
                    
                    Assert.IsNotNull(pushButton.BundleFile, "Bundle file should be present");
                    Assert.IsTrue(pushButton.BundleFile.EndsWith("bundle.yaml"), "Bundle file should be bundle.yaml");
                    
                    Assert.AreEqual("Selection Test", pushButton.Title);
                    Assert.AreEqual("Test command that requires element selection", pushButton.Tooltip);
                    Assert.AreEqual("Test User", pushButton.Author);
                    
                    return;
                }
            }
            
            Assert.Fail("SelectionTest push button not found");
        }

        [Test]
        public void TestPanelButtonWithMultilingualBundle()
        {
            if (_installedExtensions == null)
            {
                Assert.Fail("No test extensions loaded");
                return;
            }

            TestContext.Out.WriteLine("=== Testing Panel Button With Multilingual Bundle ===");

            foreach (var extension in _installedExtensions)
            {
                var panelButton = FindComponentRecursively(extension, "DebugDialogConfig");
                if (panelButton != null)
                {
                    var locales = panelButton.AvailableLocales == null
                        ? new List<string>()
                        : new List<string>(panelButton.AvailableLocales);

                    TestContext.Out.WriteLine($"Panel Button: {panelButton.DisplayName}");
                    TestContext.Out.WriteLine($"Locales: {(locales.Count == 0 ? "None" : string.Join(", ", locales))}");

                    Assert.AreEqual(CommandComponentType.PanelButton, panelButton.Type);
                    Assert.IsTrue(panelButton.HasLocalizedContent, "Expected localized content in bundle.yaml");

                    Assert.IsNotNull(panelButton.LocalizedTitles, "Localized titles should be present");
                    Assert.IsTrue(panelButton.LocalizedTitles.ContainsKey("en_us"));
                    Assert.IsTrue(panelButton.LocalizedTitles.ContainsKey("fr"));
                    Assert.IsTrue(panelButton.LocalizedTitles.ContainsKey("de"));

                    Assert.IsNotNull(panelButton.LocalizedTooltips, "Localized tooltips should be present");
                    Assert.IsTrue(panelButton.LocalizedTooltips.ContainsKey("en_us"));
                    Assert.IsTrue(panelButton.LocalizedTooltips.ContainsKey("fr"));
                    Assert.IsTrue(panelButton.LocalizedTooltips.ContainsKey("de"));

                    var frTitle = panelButton.GetLocalizedTitle("fr");
                    var deTitle = panelButton.GetLocalizedTitle("de");
                    Assert.AreEqual("Configuration du Panneau", frTitle);
                    Assert.AreEqual("Panelkonfiguration", deTitle);

                    var frTooltip = panelButton.GetLocalizedTooltip("fr");
                    var deTooltip = panelButton.GetLocalizedTooltip("de");
                    Assert.IsNotNull(frTooltip);
                    Assert.IsNotNull(deTooltip);
                    StringAssert.Contains("options", frTooltip);
                    StringAssert.Contains("panneau", frTooltip);
                    StringAssert.Contains("Panel", deTooltip);
                    StringAssert.Contains("Debug", deTooltip);

                    CollectionAssert.Contains(locales, "en_us");
                    CollectionAssert.Contains(locales, "fr");
                    CollectionAssert.Contains(locales, "de");

                    return;
                }
            }

            Assert.Fail("DebugDialogConfig panel button not found");
        }

        [Test]
        public void TestPulldownWithComplexBundle()
        {
            if (_installedExtensions == null)
            {
                Assert.Fail("No test extensions loaded");
                return;
            }

            TestContext.Out.WriteLine("=== Testing Pulldown With Complex Bundle ===");
            
            foreach (var extension in _installedExtensions)
            {
                var pulldown = FindComponentRecursively(extension, "BundleTests");
                if (pulldown != null)
                {
                    TestContext.Out.WriteLine($"Pulldown: {pulldown.DisplayName}");
                    TestContext.Out.WriteLine($"Name: {pulldown.Name}");
                    TestContext.Out.WriteLine($"Type: {pulldown.Type}");
                    TestContext.Out.WriteLine($"Bundle File: {pulldown.BundleFile ?? "None"}");
                    TestContext.Out.WriteLine($"Highlight: {pulldown.Highlight ?? "None"}");
                    TestContext.Out.WriteLine($"Layout Order Count: {pulldown.LayoutOrder?.Count ?? 0}");
                    
                    // Verify pulldown properties
                    Assert.AreEqual(CommandComponentType.PullDown, pulldown.Type);
                    Assert.AreEqual("Bundle Tests", pulldown.DisplayName);
                    
                    // Bundle file should be present
                    Assert.IsNotNull(pulldown.BundleFile, "Bundle file should be present");
                    Assert.IsTrue(pulldown.BundleFile.EndsWith("bundle.yaml"), "Bundle file should be bundle.yaml");
                    
                    // Verify complex bundle features
                    Assert.AreEqual("new", pulldown.Highlight, "Highlight should be 'new'");
                    Assert.IsNotNull(pulldown.LayoutOrder, "Layout order should be parsed");
                    Assert.IsTrue(pulldown.LayoutOrder.Count > 0, "Layout order should have items");
                    
                    // Verify layout contains expected items
                    Assert.IsTrue(pulldown.LayoutOrder.Contains("Test pyRevit Bundle"), "Layout should contain 'Test pyRevit Bundle'");
                    Assert.IsTrue(pulldown.LayoutOrder.Contains("Test pyRevit Button"), "Layout should contain 'Test pyRevit Button'");
                    
                    // Test completed successfully
                    return;
                }
            }
            
            Assert.Fail("BundleTests pulldown not found");
        }

        [Test]
        public void TestPanelButtonWithBundle()
        {
            if (_installedExtensions == null)
            {
                Assert.Fail("No test extensions loaded");
                return;
            }

            TestContext.Out.WriteLine("=== Testing Panel Button With Bundle File ===");
            
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
                    
                    // Bundle file should be present and parsed
                    Assert.IsNotNull(panelButton.BundleFile, "Bundle file should be present");
                    Assert.IsTrue(panelButton.BundleFile.EndsWith("bundle.yaml"), "Bundle file should be bundle.yaml");
                    
                    // Verify bundle metadata was parsed
                    Assert.AreEqual("Panel Configuration", panelButton.Title);
                    Assert.AreEqual("Test command that requires element selection and debug settings", panelButton.Tooltip);
                    Assert.AreEqual("Test User", panelButton.Author);
                    
                    // Test completed successfully
                    return;
                }
            }
            
            Assert.Fail("DebugDialogConfig panel button not found");
        }

        [Test]
        public void TestPanelButtonWithContextAvailability()
        {
            if (_installedExtensions == null)
            {
                Assert.Fail("No test extensions loaded");
                return;
            }

            TestContext.Out.WriteLine("=== Testing Panel Button With Context Availability ===");
            
            foreach (var extension in _installedExtensions)
            {
                var panelButton = FindComponentRecursively(extension, "DebugDialogConfig");
                if (panelButton != null)
                {
                    TestContext.Out.WriteLine($"Panel Button: {panelButton.DisplayName}");
                    TestContext.Out.WriteLine($"Context: {panelButton.Context ?? "None"}");

                    Assert.AreEqual(CommandComponentType.PanelButton, panelButton.Type);
                    Assert.IsNotNull(panelButton.Context, "Context should be parsed from bundle.yaml");
                    Assert.AreEqual("zero-doc", panelButton.Context);

                    return;
                }
            }

            Assert.Fail("DebugDialogConfig panel button not found");
        }

        [Test]
        public void TestPushButtonWithSelectionContext()
        {
            if (_installedExtensions == null)
            {
                Assert.Fail("No test extensions loaded");
                return;
            }

            TestContext.Out.WriteLine("=== Testing Push Button With Selection Context ===");
            
            foreach (var extension in _installedExtensions)
            {
                var pushButton = FindComponentRecursively(extension, "SelectionTest");
                if (pushButton != null)
                {
                    TestContext.Out.WriteLine($"Push Button: {pushButton.DisplayName}");
                    TestContext.Out.WriteLine($"Context: {pushButton.Context ?? "None"}");

                    Assert.AreEqual(CommandComponentType.PushButton, pushButton.Type);
                    Assert.IsNotNull(pushButton.Context, "Context should be parsed from bundle.yaml");
                    Assert.AreEqual("selection", pushButton.Context);
                    Assert.AreEqual("Selection Test", pushButton.Title);
                    Assert.AreEqual("Test command that requires element selection", pushButton.Tooltip);

                    return;
                }
            }

            Assert.Fail("Selection Test push button not found");
        }

        [Test]
        public void TestBundleTestsPulldownFromDevToolsExtension()
        {
            var devToolsExtensionPath = TestConfiguration.TestExtensionPath;
            if (!Directory.Exists(devToolsExtensionPath))
            {
                Assert.Inconclusive("pyRevitDevTools extension directory is missing");
                return;
            }

            var extensions = ParseInstalledExtensions(new[] { devToolsExtensionPath }).ToList();
            Assert.IsNotEmpty(extensions, "Failed to parse any extensions from pyRevitDevTools");

            var devToolsExtension = extensions
                .FirstOrDefault(ext => ext.Name.Equals("pyRevitDevTools", StringComparison.OrdinalIgnoreCase))
                ?? extensions.First();

            var bundlePulldown = FindComponentRecursively(devToolsExtension, "BundleTests");
            Assert.IsNotNull(bundlePulldown, "Bundle Tests pulldown not found in dev tools extension");
            Assert.AreEqual(CommandComponentType.PullDown, bundlePulldown.Type);
            Assert.AreEqual("new", bundlePulldown.Highlight);

            var expectedLayout = new[]
            {
                "Test pyRevit Bundle",
                "Test pyRevit Button",
                "Test Smart Button",
                "Test C# Script",
                "Test Direct Invoke",
                "Test Direct Invoke (ExecParams)",
                "Test Direct Class Invoke",
                "Test Link Button",
                "Test VisualBasic",
                "Test Ruby",
                "Test DynamoBIM",
                "Test DynamoBIM GUI",
                "Test Grasshopper",
                "Test Content Bundle",
                "Test Content Bundle - no rfa in folder nor specifed in bundle",
                "Test Content Bundle - rfa in same folder and specified in bundle",
                "Test Content Bundle - with rfa outside of content folder",
                "Test Hyperlink",
                "Test Блог"
            };

            Assert.IsNotNull(bundlePulldown.LayoutOrder, "Pulldown layout order should be parsed");
            CollectionAssert.AreEqual(expectedLayout, bundlePulldown.LayoutOrder);

            Assert.IsNotNull(bundlePulldown.Children, "Pulldown children should not be null");
            
            // List of layout items that have corresponding child components
            // Note: "Test Content Bundle - no rfa in folder nor specifed in bundle" is in bundle.yaml
            // but does not have a corresponding component directory, so it won't have a child
            var expectedChildren = new[]
            {
                "Test pyRevit Bundle",
                "Test pyRevit Button",
                "Test Smart Button",
                "Test C# Script",
                "Test Direct Invoke",
                "Test Direct Invoke (ExecParams)",
                "Test Direct Class Invoke",
                "Test Link Button",
                "Test VisualBasic",
                "Test Ruby",
                "Test DynamoBIM",
                "Test DynamoBIM GUI",
                "Test Grasshopper",
                "Test Content Bundle",
                "Test Content Bundle - rfa in same folder and specified in bundle",
                "Test Content Bundle - with rfa outside of content folder",
                "Test Hyperlink",
                "Test Блог"
            };
            
            foreach (var layoutName in expectedChildren)
            {
                var child = bundlePulldown.Children.FirstOrDefault(c => c.DisplayName == layoutName);
                Assert.IsNotNull(child, $"Pulldown child '{layoutName}' missing");
            }

            var directInvoke = FindComponentRecursively(bundlePulldown, "TestDirectInvoke");
            Assert.IsNotNull(directInvoke);
            Assert.AreEqual(CommandComponentType.InvokeButton, directInvoke.Type);
            Assert.AreEqual("PyRevitTestBundles.dll", directInvoke.TargetAssembly);
            Assert.IsNull(directInvoke.CommandClass);

            var execInvoke = FindComponentRecursively(bundlePulldown, "TestDirectInvoke(ExecParams)");
            Assert.IsNotNull(execInvoke);
            Assert.AreEqual(CommandComponentType.InvokeButton, execInvoke.Type);
            Assert.AreEqual("PyRevitTestBundles", execInvoke.TargetAssembly);
            Assert.AreEqual("PyRevitTestInvokeCommandWithExecParams", execInvoke.CommandClass);

            var classInvoke = FindComponentRecursively(bundlePulldown, "TestDirectClassInvoke");
            Assert.IsNotNull(classInvoke);
            Assert.AreEqual(CommandComponentType.InvokeButton, classInvoke.Type);
            Assert.AreEqual("PyRevitTestBundles", classInvoke.TargetAssembly);
            Assert.AreEqual("PyRevitTestInvokeCommand", classInvoke.CommandClass);
        }

        // Helper method to find components recursively
        private ParsedComponent? FindComponentRecursively(ParsedComponent? parent, string componentName)
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

        [Test]
        public void TestButtonTitleWithNewlineEscapeSequence()
        {
            // Create a temporary test button with \n in the title
            var tempDir = Path.Combine(Path.GetTempPath(), "TestNewlineTitle.extension");
            var tabDir = Path.Combine(tempDir, "TestTab.tab");
            var panelDir = Path.Combine(tabDir, "TestPanel.panel");
            var buttonDir = Path.Combine(panelDir, "TestNewlineButton.pushbutton");
            
            try
            {
                Directory.CreateDirectory(buttonDir);
                
                var scriptPath = Path.Combine(buttonDir, "script.py");
                // Test with \n in the title
                File.WriteAllText(scriptPath, @"__title__ = 'Generate\nAPI Stubs'
print('test')");
                
                // Parse the extension
                var extensions = ParseInstalledExtensions(new[] { tempDir });
                var extension = extensions.FirstOrDefault();
                
                Assert.IsNotNull(extension, "Extension should be parsed");
                
                var testButton = FindComponentRecursively(extension, "TestNewlineButton");
                Assert.IsNotNull(testButton, "TestNewlineButton should be found");
                
                // Verify that \n is converted to an actual newline
                Assert.IsNotNull(testButton.Title, "Title should not be null");
                Assert.That(testButton.Title, Does.Contain("\n"), "Title should contain an actual newline character");
                Assert.That(testButton.Title, Is.EqualTo("Generate\nAPI Stubs"), "Title should have newline properly parsed");
                
                // Verify it's NOT the literal \n string
                Assert.That(testButton.Title, Does.Not.Contain("\\n"), "Title should not contain literal \\n");
                
                TestContext.Out.WriteLine($"Title successfully parsed with newline: '{testButton.Title}'");
            }
            finally
            {
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }

        [Test]
        public void TestButtonWithVariousEscapeSequences()
        {
            // Test various Python escape sequences
            var tempDir = Path.Combine(Path.GetTempPath(), "TestEscapeSequences.extension");
            var tabDir = Path.Combine(tempDir, "TestTab.tab");
            var panelDir = Path.Combine(tabDir, "TestPanel.panel");
            var buttonDir = Path.Combine(panelDir, "TestButton.pushbutton");
            
            try
            {
                Directory.CreateDirectory(buttonDir);
                
                var scriptPath = Path.Combine(buttonDir, "script.py");
                // Test with various escape sequences - use raw Python string literals
                var scriptContent = new StringBuilder();
                scriptContent.AppendLine("__title__ = 'Line1\\nLine2\\tTab'");
                scriptContent.AppendLine("__author__ = \"Test's Author\"");
                scriptContent.AppendLine("__doc__ = 'Backslash: \\\\'");
                scriptContent.AppendLine("print('test')");
                File.WriteAllText(scriptPath, scriptContent.ToString());
                
                // Parse the extension
                var extensions = ParseInstalledExtensions(new[] { tempDir });
                var extension = extensions.FirstOrDefault();
                
                Assert.IsNotNull(extension, "Extension should be parsed");
                
                var testButton = FindComponentRecursively(extension, "TestButton");
                Assert.IsNotNull(testButton, "TestButton should be found");
                
                // Verify newline and tab are converted
                Assert.That(testButton.Title, Is.EqualTo("Line1\nLine2\tTab"), "Title should have \\n and \\t converted");
                
                // Verify single quote (no escape needed when using double quotes in Python)
                Assert.That(testButton.Author, Is.EqualTo("Test's Author"), "Author should preserve single quote");
                
                // Verify backslash escape
                Assert.That(testButton.Tooltip, Is.EqualTo("Backslash: \\"), "Tooltip should have \\\\ converted to single backslash");
                
                TestContext.Out.WriteLine($"Title: '{testButton.Title}'");
                TestContext.Out.WriteLine($"Author: '{testButton.Author}'");
                TestContext.Out.WriteLine($"Tooltip: '{testButton.Tooltip}'");
            }
            finally
            {
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }
    }
}
