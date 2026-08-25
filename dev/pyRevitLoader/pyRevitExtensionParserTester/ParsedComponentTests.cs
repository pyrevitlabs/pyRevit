using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using System.IO;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
	[TestFixture]
	internal class ParsedComponentTests : TempFileTestBase
	{
        private IEnumerable<ParsedExtension>? _installedExtensions;
        private string? _testExtensionPath;
        
        [SetUp]
        public void Setup()
        {
            // Create comprehensive test extension on-the-fly
            _testExtensionPath = TestExtensionFactory.CreateComprehensiveTestExtension(TestTempDir);
            _installedExtensions = ParseInstalledExtensions(new[] { _testExtensionPath });
        }

        [Test]
        public void HasSlideout()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintSlideoutRecursively(parsedExtension);
                }
                Assert.Pass("...");
            }
            else
            {
                Assert.Fail("...");
            }
        }
        public void PrintSlideoutRecursively(ParsedComponent parsedComponent)
        {
            TestContext.Out.WriteLine($"{parsedComponent.Name} -- has slideout {parsedComponent.HasSlideout}");
            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintSlideoutRecursively(child);
                }
            }
        }

        [Test]
        public void IsParsingScriptFile()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintTitleRecursively(parsedExtension);
                }
                Assert.Pass("...");
            }
            else
            {
                Assert.Fail("...");
            }
        }
        public void PrintTitleRecursively(ParsedComponent parsedComponent, int level = 0)
        {
            var indent = new string('-', level * 2);
            TestContext.Out.WriteLine($"{indent}- ({parsedComponent.Name}) - {parsedComponent.DisplayName} - {parsedComponent.Title} - {parsedComponent.Tooltip} - {parsedComponent.Author}");
            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintTitleRecursively(child, level + 1);
                }
            }
        }

        [Test]
        public void TestPulldownComponentParsing()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    TestContext.Out.WriteLine($"=== Testing Pulldown Component in {parsedExtension.Name} ===");
                    TestContext.Out.WriteLine($"Extension Path: {parsedExtension.Directory}");
                    
                    var pulldownComponent = FindComponentRecursively(parsedExtension, "TestPulldown");
                    if (pulldownComponent != null)
                    {
                        TestContext.Out.WriteLine($"Found pulldown component: {pulldownComponent.Name}");
                        TestContext.Out.WriteLine($"Display Name: {pulldownComponent.DisplayName}");
                        TestContext.Out.WriteLine($"Type: {pulldownComponent.Type}");
                        TestContext.Out.WriteLine($"Tooltip: '{pulldownComponent.Tooltip ?? "NULL"}'");
                        TestContext.Out.WriteLine($"Bundle File: {pulldownComponent.BundleFile ?? "NULL"}");
                        TestContext.Out.WriteLine($"Title: {pulldownComponent.Title ?? "NULL"}");
                        
                        // Verify the component was parsed correctly
                        Assert.That(pulldownComponent.Type,
                            Is.EqualTo(CommandComponentType.PullDown),
                            "Component should be PullDown type");
                        Assert.IsNotNull(pulldownComponent.Tooltip,
                            "Tooltip should not be null");
                        Assert.IsTrue(pulldownComponent.Tooltip.Contains("test tooltip for the pulldown button"), 
                                     $"Tooltip should contain expected text, but was: '{pulldownComponent.Tooltip}'");
                        
                        // Check child components
                        if (pulldownComponent.Children != null && pulldownComponent.Children.Count > 0)
                        {
                            TestContext.Out.WriteLine($"Child components count: {pulldownComponent.Children.Count}");
                            foreach (var child in pulldownComponent.Children)
                            {
                                TestContext.Out.WriteLine($"Child: {child.Name} - {child.DisplayName} - Tooltip: '{child.Tooltip ?? "NULL"}'");
                            }
                        }
                        
                        Assert.Pass("Pulldown component parsing test completed successfully.");
                    }
                    else
                    {
                        Assert.Fail("TestPulldown component not found in parsed extension");
                    }
                }
            }
            else
            {
                Assert.Fail("No test extensions found");
            }
        }

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
