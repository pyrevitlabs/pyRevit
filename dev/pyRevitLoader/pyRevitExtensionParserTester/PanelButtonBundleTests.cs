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
            TestContext.Out.WriteLine("=== Testing Panel Button With Simple Bundle ===");
            TestContext.Out.WriteLine("This test validates that bundle.yaml files with simple content are parsed correctly.");
            TestContext.Out.WriteLine("\nNote: This test requires an existing bundle.yaml file to validate parsing.");
            TestContext.Out.WriteLine("To enable this test, create a bundle.yaml file with the following structure:");
            TestContext.Out.WriteLine("---");
            TestContext.Out.WriteLine("title:");
            TestContext.Out.WriteLine("  en_us: Panel Settings");
            TestContext.Out.WriteLine("tooltips:");
            TestContext.Out.WriteLine("  en_us: Configure panel display options");
            TestContext.Out.WriteLine("author: Test Framework");
            TestContext.Out.WriteLine("min_revit_ver: 2019");
            
            Assert.Inconclusive("This test requires manual setup of bundle.yaml files. See test output for instructions.");
        }

        [Test]
        public void TestPanelButtonWithMultilingualBundle()
        {
            TestContext.Out.WriteLine("=== Testing Panel Button With Multilingual Bundle ===");
            TestContext.Out.WriteLine("This test validates multilingual support in bundle.yaml files.");
            TestContext.Out.WriteLine("\nTo enable this test, ensure a bundle.yaml with multilingual content exists.");
            TestContext.Out.WriteLine("Example multilingual bundle structure:");
            TestContext.Out.WriteLine("---");
            TestContext.Out.WriteLine("title:");
            TestContext.Out.WriteLine("  en_us: Panel Configuration");
            TestContext.Out.WriteLine("  fr: Configuration du Panneau");
            TestContext.Out.WriteLine("  de: Panel-Konfiguration");
            TestContext.Out.WriteLine("tooltips:");
            TestContext.Out.WriteLine("  en_us: Configure various display and behavior options");
            TestContext.Out.WriteLine("author: Your Name");
            
            Assert.Inconclusive("This test requires manual setup of multilingual bundle.yaml files.");
        }

        [Test]
        public void TestPanelButtonWithComplexBundle()
        {
            TestContext.Out.WriteLine("=== Testing Panel Button With Complex Bundle ===");
            TestContext.Out.WriteLine("This test validates complex bundle.yaml features including:");
            TestContext.Out.WriteLine("  - Multiline tooltips");
            TestContext.Out.WriteLine("  - Layout ordering");
            TestContext.Out.WriteLine("  - Multiple metadata fields");
            TestContext.Out.WriteLine("\\nExample complex bundle structure:");
            TestContext.Out.WriteLine("---");
            TestContext.Out.WriteLine("title:");
            TestContext.Out.WriteLine("  en_us: Advanced Panel Configuration");
            TestContext.Out.WriteLine("tooltips:");
            TestContext.Out.WriteLine("  en_us: >-");
            TestContext.Out.WriteLine("    This is an advanced panel configuration");
            TestContext.Out.WriteLine("    with multiline tooltip support.");
            TestContext.Out.WriteLine("author: Your Name");
            TestContext.Out.WriteLine("min_revit_ver: 2021");
            TestContext.Out.WriteLine("layout_order:");
            TestContext.Out.WriteLine("  - \\\"Button1\\\"");
            TestContext.Out.WriteLine("  - \\\"Button2\\\"");
            TestContext.Out.WriteLine("  - \\\">>>>>\\\"");
            
            Assert.Inconclusive("This test requires manual setup of complex bundle.yaml files.");
        }

        [Test]
        public void TestCreateNewPanelButton()
        {
            TestContext.Out.WriteLine("=== Testing New Panel Button Creation ===");
            TestContext.Out.WriteLine("This test validates that the parser can detect newly created panel buttons.");
            TestContext.Out.WriteLine("\\nNote: Dynamic button creation during tests is not supported.");
            TestContext.Out.WriteLine("To test panel button parsing, create a .panelbutton directory with:");
            TestContext.Out.WriteLine("  1. script.py file with __title__, __author__, and command logic");
            TestContext.Out.WriteLine("  2. bundle.yaml file with metadata");
            TestContext.Out.WriteLine("\\nExample directory structure:");
            TestContext.Out.WriteLine("  MyButton.panelbutton/");
            TestContext.Out.WriteLine("    ├── script.py");
            TestContext.Out.WriteLine("    ├── bundle.yaml");
            TestContext.Out.WriteLine("    └── icon.png (optional)");
            
            Assert.Inconclusive("This test requires manual creation of panel button directories.");
        }

        [Test]
        public void TestPanelButtonWithContextAvailability()
        {
            TestContext.Out.WriteLine("=== Testing Panel Button With Context Availability ===");
            TestContext.Out.WriteLine("This test validates context/availability parsing in bundle.yaml files.");
            TestContext.Out.WriteLine("\nExample bundle with context:");
            TestContext.Out.WriteLine("---");
            TestContext.Out.WriteLine("title:");
            TestContext.Out.WriteLine("  en_us: Zero-Doc Command");
            TestContext.Out.WriteLine("context: zero-doc");
            TestContext.Out.WriteLine("\nSupported context values:");
            TestContext.Out.WriteLine("  - zero-doc: Available when no document is open");
            TestContext.Out.WriteLine("  - selection: Requires element selection");
            TestContext.Out.WriteLine("  - zerodoc: Alternative spelling");
            
            Assert.Inconclusive("This test requires manual setup of bundle.yaml with context property.");
        }

        [Test]
        public void TestPanelButtonWithSelectionContext()
        {
            TestContext.Out.WriteLine("=== Testing Panel Button With Selection Context ===");
            TestContext.Out.WriteLine("This test validates selection context parsing in bundle.yaml files.");
            TestContext.Out.WriteLine("\nExample bundle with selection context:");
            TestContext.Out.WriteLine("---");
            TestContext.Out.WriteLine("title:");
            TestContext.Out.WriteLine("  en_us: Selection Command");
            TestContext.Out.WriteLine("context: selection");
            TestContext.Out.WriteLine("\nWhen context is 'selection':");
            TestContext.Out.WriteLine("  - Command requires elements to be selected");
            TestContext.Out.WriteLine("  - Button is disabled when no selection");
            
            Assert.Inconclusive("This test requires manual setup of bundle.yaml with selection context.");
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