using System.IO;
using System.Linq;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Regression coverage for versioned family selection and generated command caching.
    /// </summary>
    [TestFixture]
    [Property("Level", "Integration")]
    [Property("Environment", "HostFree")]
    public class ContentSelectionTests : TempFileTestBase
    {
        private const string Extension = "Families.extension";
        private const string Panel = Extension + "/Test.tab/Test.panel/";
        private const string Bundle = Panel + "Family.content/";

        [TestCase(2023, "Family_content_2023.rfa", "Family_other_2023.rfa")]
        [TestCase(2024, "Family_CONTENT_2024.RFA", "Family_other.rfa")]
        [TestCase(2025, "Family_content_2025.rfa", "Family_other_2025.rfa")]
        [TestCase(2026, "Family_content_2026.rfa", "Family_other_2026.rfa")]
        [TestCase(2027, "Family_content.rfa", "Family_other.rfa")]
        [TestCase(0, "Family_content.rfa", "Family_other.rfa")]
        public void SelectsExactYearThenGeneric(int revitYear, string primary, string alternative)
        {
            AddFamilies("Family_content_2019.rfa", "Family_content_2023.rfa",
                "Family_CONTENT_2024.RFA", "Family_content_2025.rfa", "Family_content_2026.rfa",
                "Family_content.rfa", "Family_other_2019.rfa", "Family_other_2023.rfa",
                "Family_other_2025.rfa", "Family_other_2026.rfa", "Family_other.rfa");

            var button = ParseButton(revitYear);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile(primary)));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(BundleFile(alternative)));
        }

        [Test]
        public void RecognizesUnprefixedNamesAndUsesPrimaryWhenAlternativeYearDoesNotMatch()
        {
            AddFamilies("content.rfa", "content_2024.rfa", "other_2019.rfa");

            var button = ParseButton(2024);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile("content_2024.rfa")));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(button?.ScriptPath));
        }

        [TestCase(2023)]
        [TestCase(2025)]
        [TestCase(2026)]
        [TestCase(0)]
        public void SkipsButtonWithoutMatchingOrGenericPrimary(int revitYear)
        {
            AddFamilies("Family_content_2019.rfa", "content_2024.rfa", "other.rfa", "Unrelated.rfa");
            CreateFile(Bundle + "script.py", "pass");

            Assert.That(ParseButton(revitYear), Is.Null);
        }

        [Test]
        public void ExplicitRelativeAndAbsoluteYamlPathsOverrideConventions()
        {
            AddFamilies("content_2024.rfa", "other_2024.rfa");
            var primary = CreateFile(Panel + "Primary.rfa", "");
            var alternative = CreateFile("Alternate.rfa", "");
            CreateFile(Bundle + "bundle.yaml", $"content: '../Primary.rfa'\ncontent_alt: '{alternative}'");

            var button = ParseButton(2024);

            Assert.That(button?.ScriptPath, Is.EqualTo(Path.GetFullPath(primary)));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(alternative));
        }

        [Test]
        public void MissingExplicitPrimaryUsesMatchingConvention()
        {
            AddFamilies("Family_content_2019.rfa", "Family_content_2024.rfa");
            CreateFile(Bundle + "bundle.yaml", "content: 'missing.rfa'\ncontent_alt: 'missing-other.rfa'");

            var button = ParseButton(2024);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile("Family_content_2024.rfa")));
            Assert.That(button?.ConfigScriptPath, Is.Null);
        }

        [Test]
        public void CommandCacheKeyTracksResolvedContentPaths()
        {
            AddFamilies("content.rfa", "other_2023.rfa", "other_2024.rfa");

            Assert.That(ParseExtension(2023).GetHash(), Is.Not.EqualTo(ParseExtension(2024).GetHash()));
        }

        private ParsedExtension ParseExtension(int revitYear)
        {
            return ExtensionParser.ParseInstalledExtensions(Path.Combine(TestTempDir, Extension), revitYear)
                .Single();
        }

        private ParsedComponent? ParseButton(int revitYear)
        {
            return ParseExtension(revitYear).Children.Single().Children.Single().Children.SingleOrDefault();
        }

        private void AddFamilies(params string[] names)
        {
            foreach (var name in names)
                CreateFile(Bundle + name, "");
        }

        private string BundleFile(string name)
        {
            return Path.GetFullPath(Path.Combine(TestTempDir, Bundle, name));
        }
    }
}
