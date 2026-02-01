using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using System.IO;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    internal class QuotedValueTests : TempFileTestBase
    {
        private string _tempTestFile;

        [SetUp]
        public override void BaseSetUp()
        {
            base.BaseSetUp();
            // Create a temporary test file in the test temp directory
            _tempTestFile = Path.Combine(TestTempDir, "test.yaml");
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

        [Test]
        public void TestMultilineTooltipWithPipeOperator()
        {
            // Test YAML multiline block scalar (|) at the top level
            var testYaml = @"tooltip: |
  Test pyRevit Bundle Tooltip
  Second line of tooltip
  Third line";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Tooltips.Count, Is.EqualTo(1));
            Assert.That(result.Tooltips["en_us"], Is.EqualTo("Test pyRevit Bundle Tooltip\nSecond line of tooltip\nThird line"));
        }

        [Test]
        public void TestMultilineTooltipWithLiteralPipe()
        {
            // Test YAML literal block scalar (|-) at the top level
            var testYaml = @"tooltip: |-
  Test pyRevit Bundle Tooltip
  Line two
  Line three";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Tooltips.Count, Is.EqualTo(1));
            Assert.That(result.Tooltips["en_us"], Is.EqualTo("Test pyRevit Bundle Tooltip\nLine two\nLine three"));
        }

        [Test]
        public void TestMultilineTitleWithPipeOperator()
        {
            // Test YAML multiline block scalar (|) for title
            var testYaml = @"title: |
  My Custom
  Button Title";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Titles.Count, Is.EqualTo(1));
            Assert.That(result.Titles["en_us"], Is.EqualTo("My Custom\nButton Title"));
        }

        [Test]
        public void TestTemplateVariables()
        {
            // Test that template variables are parsed from bundle.yaml
            // Note: 'author' is a known property and is NOT stored as a template
            var testYaml = @"template_test: Bundle liquid templating works
docpath: https://example.com/docs
custom_var: Some custom value
title:
  en_us: Test Button";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Templates.Count, Is.EqualTo(3));
            Assert.That(result.Templates["template_test"], Is.EqualTo("Bundle liquid templating works"));
            Assert.That(result.Templates["docpath"], Is.EqualTo("https://example.com/docs"));
            Assert.That(result.Templates["custom_var"], Is.EqualTo("Some custom value"));
        }

        [Test]
        public void TestTemplatesSection()
        {
            // Test that template variables are parsed from nested templates section
            var testYaml = @"templates:
  custom_var: Custom value
  another_var: Another value
title:
  en_us: Test Button";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Templates.Count, Is.EqualTo(2));
            Assert.That(result.Templates["custom_var"], Is.EqualTo("Custom value"));
            Assert.That(result.Templates["another_var"], Is.EqualTo("Another value"));
        }

        [Test]
        public void TestMultilineWithTemplateVariables()
        {
            // Test multiline tooltip with template variable syntax
            var testYaml = @"tooltip: |
  Test pyRevit Bundle Tooltip
  {{template_test}}
template_test: Substitution placeholder";

            File.WriteAllText(_tempTestFile, testYaml);

            var result = BundleParser.BundleYamlParser.Parse(_tempTestFile);

            Assert.That(result.Tooltips.Count, Is.EqualTo(1));
            // The tooltip contains the template variable syntax
            Assert.That(result.Tooltips["en_us"], Does.Contain("{{template_test}}"));
            // The template variable is also captured
            Assert.That(result.Templates["template_test"], Is.EqualTo("Substitution placeholder"));
        }
    }
}
