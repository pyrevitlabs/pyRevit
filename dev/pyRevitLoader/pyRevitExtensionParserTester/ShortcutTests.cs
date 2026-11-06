using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    internal class ShortcutTests
    {
        private static ParsedBundle ParseYaml(string yamlContent)
        {
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);

            try
            {
                return BundleParser.BundleYamlParser.Parse(tempFile);
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestShortcutsList()
        {
            var bundle = ParseYaml(@"title:
  en_us: Test Command
shortcuts:
  - ZQ
  - Ctrl+Shift+K
");

            Assert.That(bundle.Shortcuts, Is.EqualTo(new[] { "ZQ", "Ctrl+Shift+K" }));
        }

        [Test]
        public void TestShortcutsInlineList()
        {
            var bundle = ParseYaml(@"shortcuts: [ZQ, ""Ctrl+K""]
");

            Assert.That(bundle.Shortcuts, Is.EqualTo(new[] { "ZQ", "Ctrl+K" }));
        }

        [Test]
        public void TestShortcutsSingleScalar()
        {
            var bundle = ParseYaml(@"shortcuts: ZQ
");

            Assert.That(bundle.Shortcuts, Is.EqualTo(new[] { "ZQ" }));
        }

        [Test]
        public void TestShortcutsAreTrimmedAndEmptyEntriesDropped()
        {
            var bundle = ParseYaml(@"shortcuts:
  - ""  ZQ  ""
  - """"
  - ""   ""
");

            Assert.That(bundle.Shortcuts, Is.EqualTo(new[] { "ZQ" }));
        }

        [Test]
        public void TestShortcutsMappingIsIgnored()
        {
            var bundle = ParseYaml(@"shortcuts:
  default: ZQ
");

            Assert.That(bundle.Shortcuts, Is.Empty);
        }

        [Test]
        public void TestShortcutsNotLeakedIntoTemplates()
        {
            var bundle = ParseYaml(@"shortcuts: ZQ
");

            Assert.That(bundle.Templates.ContainsKey("shortcuts"), Is.False);
        }

        [Test]
        public void TestNoShortcutsSpecified()
        {
            var bundle = ParseYaml(@"title:
  en_us: Test Command
");

            Assert.That(bundle.Shortcuts, Is.Empty);
        }
    }
}
