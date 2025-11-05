using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    internal class QuotedValueTests
    {
        private string _tempTestFile;

        [SetUp]
        public void Setup()
        {
            // Create a temporary test file
            _tempTestFile = Path.GetTempFileName();
        }

        [TearDown]
        public void TearDown()
        {
            // Clean up the temporary file
            if (File.Exists(_tempTestFile))
            {
                File.Delete(_tempTestFile);
            }
        }

        [Test]
        public void TestSingleQuotedValues()
        {
            // Create a test YAML with single quoted values
            var testYaml = @"title:
  ru: ?????
  en_us: 'Search'
  fa: '?????'
  bg: '?????'
  nl_nl: 'Zoek'
  fr_fr: 'Rechercher'
  de_de: 'Suche'";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Titles.Count, Is.EqualTo(7));
            Assert.That(result.Titles["ru"], Is.EqualTo("?????")); // No quotes
            Assert.That(result.Titles["en_us"], Is.EqualTo("Search")); // Single quotes stripped
            Assert.That(result.Titles["fa"], Is.EqualTo("?????")); // Single quotes stripped
            Assert.That(result.Titles["bg"], Is.EqualTo("?????")); // Single quotes stripped
            Assert.That(result.Titles["nl_nl"], Is.EqualTo("Zoek")); // Single quotes stripped
            Assert.That(result.Titles["fr_fr"], Is.EqualTo("Rechercher")); // Single quotes stripped
            Assert.That(result.Titles["de_de"], Is.EqualTo("Suche")); // Single quotes stripped
        }

        [Test]
        public void TestDoubleQuotedValues()
        {
            // Create a test YAML with double quoted values
            var testYaml = @"title:
  es_es: ""Buscar""
  en_us: ""Search""
  pt_br: ""Pesquisar""";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Titles.Count, Is.EqualTo(3));
            Assert.That(result.Titles["es_es"], Is.EqualTo("Buscar")); // Double quotes stripped
            Assert.That(result.Titles["en_us"], Is.EqualTo("Search")); // Double quotes stripped
            Assert.That(result.Titles["pt_br"], Is.EqualTo("Pesquisar")); // Double quotes stripped
        }

        [Test]
        public void TestMixedQuotedValues()
        {
            // Create a test YAML with mixed quoted and unquoted values
            var testYaml = @"title:
  ru: ?????
  en_us: 'Search'
  fa: '?????'
  bg: '?????'
  nl_nl: 'Zoek'
  fr_fr: 'Rechercher'
  de_de: 'Suche'
  es_es: ""Buscar""
  pt_br: Plain Text";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Titles.Count, Is.EqualTo(9));
            Assert.That(result.Titles["ru"], Is.EqualTo("?????")); // No quotes
            Assert.That(result.Titles["en_us"], Is.EqualTo("Search")); // Single quotes stripped
            Assert.That(result.Titles["fa"], Is.EqualTo("?????")); // Single quotes stripped
            Assert.That(result.Titles["bg"], Is.EqualTo("?????")); // Single quotes stripped
            Assert.That(result.Titles["nl_nl"], Is.EqualTo("Zoek")); // Single quotes stripped
            Assert.That(result.Titles["fr_fr"], Is.EqualTo("Rechercher")); // Single quotes stripped
            Assert.That(result.Titles["de_de"], Is.EqualTo("Suche")); // Single quotes stripped
            Assert.That(result.Titles["es_es"], Is.EqualTo("Buscar")); // Double quotes stripped
            Assert.That(result.Titles["pt_br"], Is.EqualTo("Plain Text")); // No quotes
        }

        [Test]
        public void TestQuotedTooltipValues()
        {
            // Test that tooltips also handle quoted values correctly
            var testYaml = @"tooltip:
  en_us: 'This is a tooltip'
  es_es: ""Este es un tooltip""
  ru: ??? ?????????";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Tooltips.Count, Is.EqualTo(3));
            Assert.That(result.Tooltips["en_us"], Is.EqualTo("This is a tooltip")); // Single quotes stripped
            Assert.That(result.Tooltips["es_es"], Is.EqualTo("Este es un tooltip")); // Double quotes stripped
            Assert.That(result.Tooltips["ru"], Is.EqualTo("??? ?????????")); // No quotes
        }

        [Test]
        public void TestEmptyQuotes()
        {
            // Test edge case of empty quotes
            var testYaml = @"title:
  en_us: ''
  es_es: """"
  ru: Normal Value";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Titles.Count, Is.EqualTo(3));
            Assert.That(result.Titles["en_us"], Is.EqualTo("")); // Empty single quotes
            Assert.That(result.Titles["es_es"], Is.EqualTo("")); // Empty double quotes
            Assert.That(result.Titles["ru"], Is.EqualTo("Normal Value")); // No quotes
        }

        [Test]
        public void TestPartialQuotes()
        {
            // Test edge case of partial quotes (should not be stripped)
            var testYaml = @"title:
  en_us: 'Incomplete quote
  es_es: Missing end quote""
  ru: ""Missing start quote";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Titles.Count, Is.EqualTo(3));
            Assert.That(result.Titles["en_us"], Is.EqualTo("'Incomplete quote")); // Single quote at start only
            Assert.That(result.Titles["es_es"], Is.EqualTo("Missing end quote\"")); // Double quote at end only
            Assert.That(result.Titles["ru"], Is.EqualTo("\"Missing start quote")); // Double quote at start only
        }

        [Test]
        public void TestSpecificUserCase()
        {
            // Test the exact case reported by the user
            var testYaml = "title:\n" +
                          "  ru: ????\n" +
                          "  en_us: \"Blog\"\n" +
                          "  fa: \"?????\"\n" +
                          "  ar: \"????\"\n" +
                          "  es_es: 'Blog'\n" +
                          "  de_de: \"Blog\"";

            File.WriteAllText(_tempTestFile, testYaml, System.Text.Encoding.UTF8);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Titles.Count, Is.EqualTo(6));
            Assert.That(result.Titles["ru"], Is.EqualTo("????")); // No quotes
            Assert.That(result.Titles["en_us"], Is.EqualTo("Blog")); // Double quotes stripped
            Assert.That(result.Titles["fa"], Is.EqualTo("?????")); // Double quotes stripped
            Assert.That(result.Titles["ar"], Is.EqualTo("????")); // Double quotes stripped
            Assert.That(result.Titles["es_es"], Is.EqualTo("Blog")); // Single quotes stripped
            Assert.That(result.Titles["de_de"], Is.EqualTo("Blog")); // Double quotes stripped
        }
    }
}