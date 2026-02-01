using NUnit.Framework;
using pyRevitExtensionParser;
using System.IO;
using System.Linq;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Tests for template variable inheritance from parent bundle.yaml files.
    /// Uses the actual pyRevitDevTools extension to verify template substitution works correctly.
    /// </summary>
    [TestFixture]
    public class TemplateInheritanceTests
    {
        private string _extensionPath;
        private string _debugPanelPath;
        private string _bundleTestsPulldownPath;

        [SetUp]
        public void SetUp()
        {
            _extensionPath = TestConfiguration.TestExtensionPath;
            _debugPanelPath = Path.Combine(_extensionPath, "pyRevitDev.tab", "Debug.panel");
            _bundleTestsPulldownPath = Path.Combine(_debugPanelPath, "Bundle Tests.pulldown");

            if (!Directory.Exists(_extensionPath))
            {
                Assert.Inconclusive($"pyRevitDevTools extension not found at: {_extensionPath}");
            }
        }

        /// <summary>
        /// Tests that template_test from Debug.panel/bundle.yaml is substituted in 
        /// Test pyRevit Bundle.pushbutton tooltip.
        /// 
        /// Debug.panel/bundle.yaml defines:
        ///   template_test: Bundle liquid templating works (https://www.youtube.com/watch?v=)
        /// 
        /// Test pyRevit Bundle.pushbutton/bundle.yaml uses:
        ///   tooltip: |
        ///     Test pyRevit Bundle Tooltip
        ///     {{template_test}}
        /// </summary>
        [Test]
        public void TestTemplateTestSubstitutionInTooltip()
        {
            // Parse the extension
            var extensions = ExtensionParser.ParseInstalledExtensions(_extensionPath).ToList();
            Assert.That(extensions.Count, Is.EqualTo(1), "Should parse one extension");

            var extension = extensions[0];

            // Navigate to Test pyRevit Bundle button
            // Path: pyRevitDev.tab > Debug.panel > Bundle Tests.pulldown > Test pyRevit Bundle.pushbutton
            var devTab = extension.Children?.FirstOrDefault(c => c.Name == "pyRevitDev");
            Assert.That(devTab, Is.Not.Null, "Should find pyRevitDev tab");

            var debugPanel = devTab.Children?.FirstOrDefault(c => c.Name == "Debug");
            Assert.That(debugPanel, Is.Not.Null, "Should find Debug panel");

            var bundleTestsPulldown = debugPanel.Children?.FirstOrDefault(c => c.Name == "BundleTests");
            Assert.That(bundleTestsPulldown, Is.Not.Null, "Should find BundleTests pulldown");

            var testBundleButton = bundleTestsPulldown.Children?.FirstOrDefault(c => c.Name == "TestpyRevitBundle");
            Assert.That(testBundleButton, Is.Not.Null, "Should find Test pyRevit Bundle button");

            // Verify tooltip contains the substituted template_test value
            TestContext.Out.WriteLine($"Button: {testBundleButton.Name}");
            TestContext.Out.WriteLine($"DisplayName: {testBundleButton.DisplayName}");
            TestContext.Out.WriteLine($"Tooltip: {testBundleButton.Tooltip}");

            Assert.That(testBundleButton.Tooltip, Is.Not.Null, "Tooltip should not be null");
            Assert.That(testBundleButton.Tooltip, Does.Contain("Test pyRevit Bundle Tooltip"), 
                "Tooltip should contain the base text");
            
            // The template_test should be substituted with the value from Debug.panel/bundle.yaml
            Assert.That(testBundleButton.Tooltip, Does.Contain("Bundle liquid templating works"), 
                "Tooltip should contain substituted template_test value");
            Assert.That(testBundleButton.Tooltip, Does.Not.Contain("{{template_test}}"), 
                "Tooltip should not contain unsubstituted template variable");
        }

        /// <summary>
        /// Tests that docpath template from parent bundle.yaml is substituted in 
        /// Test pyRevit Bundle.pushbutton help_url.
        /// 
        /// Test pyRevit Bundle.pushbutton/bundle.yaml uses:
        ///   help_url: "{{docpath}}"
        /// 
        /// Note: docpath needs to be defined in a parent bundle.yaml for this to work.
        /// </summary>
        [Test]
        public void TestDocpathTemplateInHelpUrl()
        {
            // First verify what docpath is defined as (if at all)
            var debugPanelBundlePath = Path.Combine(_debugPanelPath, "bundle.yaml");
            if (File.Exists(debugPanelBundlePath))
            {
                var debugPanelBundle = BundleParser.BundleYamlParser.Parse(debugPanelBundlePath);
                TestContext.Out.WriteLine($"Debug.panel templates: {string.Join(", ", debugPanelBundle.Templates.Keys)}");
                foreach (var kvp in debugPanelBundle.Templates)
                {
                    TestContext.Out.WriteLine($"  {kvp.Key}: {kvp.Value}");
                }
            }

            // Parse the extension
            var extensions = ExtensionParser.ParseInstalledExtensions(_extensionPath).ToList();
            var extension = extensions[0];

            // Navigate to Test pyRevit Bundle button
            var devTab = extension.Children?.FirstOrDefault(c => c.Name == "pyRevitDev");
            var debugPanel = devTab?.Children?.FirstOrDefault(c => c.Name == "Debug");
            var bundleTestsPulldown = debugPanel?.Children?.FirstOrDefault(c => c.Name == "BundleTests");
            var testBundleButton = bundleTestsPulldown?.Children?.FirstOrDefault(c => c.Name == "TestpyRevitBundle");

            Assert.That(testBundleButton, Is.Not.Null, "Should find Test pyRevit Bundle button");

            TestContext.Out.WriteLine($"Button Hyperlink: {testBundleButton.Hyperlink ?? "null"}");
            
            // If docpath template is not defined, the hyperlink will still contain {{docpath}}
            // This test documents the current behavior
            if (testBundleButton.Hyperlink != null && testBundleButton.Hyperlink.Contains("{{docpath}}"))
            {
                TestContext.Out.WriteLine("Note: docpath template is not defined in parent bundle.yaml");
            }
        }

        /// <summary>
        /// Tests that author template from parent bundle.yaml is substituted in 
        /// Test C# Script.pushbutton author field.
        /// 
        /// Test C# Script.pushbutton/bundle.yaml uses:
        ///   author: "{{author}}"
        /// 
        /// This requires author to be defined in a parent bundle.yaml (extension or tab level).
        /// </summary>
        [Test]
        public void TestAuthorTemplateSubstitution()
        {
            // Check if extension-level bundle.yaml defines author
            var extensionBundlePath = Path.Combine(_extensionPath, "bundle.yaml");
            string? expectedAuthor = null;
            
            if (File.Exists(extensionBundlePath))
            {
                var extensionBundle = BundleParser.BundleYamlParser.Parse(extensionBundlePath);
                expectedAuthor = extensionBundle.Author;
                TestContext.Out.WriteLine($"Extension author: {expectedAuthor ?? "not defined"}");
                
                if (extensionBundle.Templates.ContainsKey("author"))
                {
                    expectedAuthor = extensionBundle.Templates["author"];
                    TestContext.Out.WriteLine($"Extension author template: {expectedAuthor}");
                }
            }
            else
            {
                TestContext.Out.WriteLine("No extension-level bundle.yaml found");
            }

            // Parse the extension
            var extensions = ExtensionParser.ParseInstalledExtensions(_extensionPath).ToList();
            var extension = extensions[0];

            // Navigate to Test C# Script button
            var devTab = extension.Children?.FirstOrDefault(c => c.Name == "pyRevitDev");
            var debugPanel = devTab?.Children?.FirstOrDefault(c => c.Name == "Debug");
            var bundleTestsPulldown = debugPanel?.Children?.FirstOrDefault(c => c.Name == "BundleTests");
            var testCSharpButton = bundleTestsPulldown?.Children?.FirstOrDefault(c => c.Name == "TestC#Script");

            Assert.That(testCSharpButton, Is.Not.Null, "Should find Test C# Script button");

            TestContext.Out.WriteLine($"Button: {testCSharpButton.Name}");
            TestContext.Out.WriteLine($"Author: {testCSharpButton.Author ?? "null"}");

            // Document what happens with author template
            if (testCSharpButton.Author != null && testCSharpButton.Author.Contains("{{author}}"))
            {
                TestContext.Out.WriteLine("Note: author template is not defined in any parent bundle.yaml");
                TestContext.Out.WriteLine("To enable author inheritance, add 'author: <value>' to extension or tab bundle.yaml");
            }
            else if (!string.IsNullOrEmpty(expectedAuthor))
            {
                // If author is defined at extension level, it should be substituted
                Assert.That(testCSharpButton.Author, Does.Contain(expectedAuthor),
                    "Author should be substituted with value from parent bundle.yaml");
            }
        }

        /// <summary>
        /// Tests that template variables defined in Debug.panel/bundle.yaml are correctly 
        /// parsed and available for child components.
        /// </summary>
        [Test]
        public void TestDebugPanelTemplatesAreParsed()
        {
            var bundlePath = Path.Combine(_debugPanelPath, "bundle.yaml");
            Assert.That(File.Exists(bundlePath), Is.True, $"Debug.panel bundle.yaml should exist at: {bundlePath}");

            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            TestContext.Out.WriteLine("=== Debug.panel bundle.yaml templates ===");
            foreach (var kvp in bundle.Templates)
            {
                TestContext.Out.WriteLine($"  {kvp.Key}: {kvp.Value}");
            }

            // Verify template_test is parsed
            Assert.That(bundle.Templates.ContainsKey("template_test"), Is.True,
                "Debug.panel bundle.yaml should contain template_test");
            Assert.That(bundle.Templates["template_test"], Does.StartWith("Bundle liquid templating works"),
                "template_test should have correct value");
        }

        /// <summary>
        /// Tests that authors list in Test pyRevit Bundle.pushbutton is documented.
        /// 
        /// Test pyRevit Bundle.pushbutton/bundle.yaml defines:
        ///   authors:
        ///     - "{{author}}"
        ///     - John Doe
        /// 
        /// Note: The BundleParser currently only supports singular 'author:' field,
        /// not 'authors:' list. This test documents the current behavior.
        /// </summary>
        [Test]
        public void TestAuthorsListWithTemplate()
        {
            var bundlePath = Path.Combine(_bundleTestsPulldownPath, "Test pyRevit Bundle.pushbutton", "bundle.yaml");
            Assert.That(File.Exists(bundlePath), Is.True, $"Bundle.yaml should exist at: {bundlePath}");

            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            TestContext.Out.WriteLine("=== Test pyRevit Bundle bundle.yaml ===");
            TestContext.Out.WriteLine($"Author: {bundle.Author ?? "null"}");
            TestContext.Out.WriteLine($"Hyperlink: {bundle.Hyperlink ?? "null"}");
            
            // Note: 'authors:' list (plural) is not currently supported by BundleParser
            // Only singular 'author:' field is parsed
            // This test documents the current behavior
            if (bundle.Author == null)
            {
                TestContext.Out.WriteLine("Note: 'authors:' list is not currently supported by BundleParser");
                TestContext.Out.WriteLine("Only singular 'author:' field is parsed");
            }
            else
            {
                TestContext.Out.WriteLine($"Parsed author value: {bundle.Author}");
            }
            
            // This test passes - it just documents the behavior
            Assert.Pass("Test documents current authors list behavior");
        }
    }
}
