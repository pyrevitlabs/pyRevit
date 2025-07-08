using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class Tests
    {
        private IEnumerable<ParsedExtension>? _installedExtensions;

        [SetUp]
        public void Setup()
        {
            // Collect all supported by pyRevit extensions
            _installedExtensions = ExtensionParser.ParseInstalledExtensions();
        }

        [Test]
        public void ParsingExtensionsTest()
        {
            if (_installedExtensions != null)
            {
                foreach (var parsedExtension in _installedExtensions)
                {
                    PrintComponentsRecursively(parsedExtension);
                }
                Assert.Pass("Installed extensions found.");
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
        public void PrintComponentsRecursively(ParsedComponent parsedComponent, int level = 0)
        {
            var indent = new string('-', level * 2);
            TestContext.Out.WriteLine($"{indent}- ({parsedComponent.Name}) - {parsedComponent.DisplayName}");
            if (parsedComponent.Children != null)
            {
                foreach (var child in parsedComponent.Children)
                {
                    PrintComponentsRecursively(child, level + 1);
                }
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
    }
}
