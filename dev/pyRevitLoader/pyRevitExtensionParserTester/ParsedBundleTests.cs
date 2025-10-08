using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
	internal class ParsedBundleTests
	{
        private IEnumerable<ParsedExtension>? _installedExtensions;
        
        [SetUp]
        public void Setup()
        {
            // Use the test bundle from Resources folder
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources", "TestBundleExtension.extension");
            _installedExtensions = ParseInstalledExtensions(new[] { testBundlePath });
        }

        [Test]
        public void ParsingBundleFiles()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintBundleDataRecursively(parsedExtension);
                }
                Assert.Pass("Bundle file parsing completed.");
            }
            else
            {
                Assert.Fail("No installed extensions found.");
            }
        }

        [Test]
        public void ParseBundleLayouts()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintLayoutRecursively(parsedExtension);
                }
                Assert.Pass("...");
            }
            else
            {
                Assert.Fail("...");
            }
        }
        public void PrintBundleDataRecursively(ParsedComponent parsedComponent, int level = 0)
        {
            // Only print components that have bundle files
            if (!string.IsNullOrEmpty(parsedComponent.BundleFile))
            {
                var indent = new string('-', level * 2);
                TestContext.Out.WriteLine($"{indent}[BUNDLE] {parsedComponent.Name}");
                TestContext.Out.WriteLine($"{indent}  Display Name: {parsedComponent.DisplayName ?? "N/A"}");
                TestContext.Out.WriteLine($"{indent}  Bundle File: {parsedComponent.BundleFile}");
                
                try
                {
                    var bundleData = BundleParser.BundleYamlParser.Parse(parsedComponent.BundleFile);
                    
                    if (bundleData.Titles?.Count > 0)
                    {
                        TestContext.Out.WriteLine($"{indent}  Bundle Titles:");
                        foreach (var title in bundleData.Titles)
                        {
                            TestContext.Out.WriteLine($"{indent}    {title.Key}: {title.Value}");
                        }
                    }
                    
                    if (bundleData.Tooltips?.Count > 0)
                    {
                        TestContext.Out.WriteLine($"{indent}  Bundle Tooltips:");
                        foreach (var tooltip in bundleData.Tooltips)
                        {
                            // Truncate long tooltips for readability
                            var truncatedTooltip = tooltip.Value.Length > 100 
                                ? tooltip.Value.Substring(0, 100) + "..." 
                                : tooltip.Value;
                            TestContext.Out.WriteLine($"{indent}    {tooltip.Key}: {truncatedTooltip}");
                        }
                    }
                    
                    if (!string.IsNullOrEmpty(bundleData.Author))
                    {
                        TestContext.Out.WriteLine($"{indent}  Bundle Author: {bundleData.Author}");
                    }

                    if (bundleData.LayoutOrder?.Count > 0)
                    {
                        TestContext.Out.WriteLine($"{indent}  Layout Order: [{string.Join(", ", bundleData.LayoutOrder)}]");
                    }

                    if (!string.IsNullOrEmpty(bundleData.MinRevitVersion))
                    {
                        TestContext.Out.WriteLine($"{indent}  Min Revit Version: {bundleData.MinRevitVersion}");
                    }
                }
                catch (System.Exception ex)
                {
                    TestContext.Out.WriteLine($"{indent}  [BUNDLE PARSE ERROR]: {ex.Message}");
                }
                
                TestContext.Out.WriteLine($"{indent}  --------------------------------");
            }

            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintBundleDataRecursively(child, level + 1);
                }
            }
        }
        public void PrintLayoutRecursively(ParsedComponent parsedComponent)
        {
            TestContext.Out.WriteLine($"{parsedComponent.Name}");
            if (parsedComponent.LayoutOrder == null)
            {
                TestContext.Out.WriteLine($"-- No layout order");
            }
            else
            {
                foreach (var str in parsedComponent.LayoutOrder)
                {
                    TestContext.Out.WriteLine($"-- {str}");
                }
            }

            TestContext.Out.WriteLine($"*******************************");

            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintLayoutRecursively(child);
                }
            }
        }

	}
}
