using System;
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
    /// <remarks>Regression tests for PR #3947.</remarks>
    [TestFixture]
    [Property("Level", "Integration")]
    [Property("Environment", "HostFree")]
    public class ContentSelectionTests : TempFileTestBase
    {
        private const string Extension = "Families.extension";
        private const string Panel = Extension + "/Test.tab/Test.panel/";
        private const string Bundle = Panel + "Family.content/";

        /// <summary>Prefers matching families and falls back to generic files when the year is unavailable.</summary>
        /// <param name="revitYear">The host year, or zero if it is unknown.</param>
        /// <param name="primary">The expected primary filename.</param>
        /// <param name="alternative">The expected alternative filename.</param>
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

        /// <summary>Preserves postfix matching for both versioned and generic content with legacy prefixes.</summary>
        /// <param name="separator">The separator between the prefix and the content postfix.</param>
        /// <param name="revitYear">The host year used for selection.</param>
        /// <param name="primary">The expected primary postfix.</param>
        /// <param name="alternative">The expected alternative postfix.</param>
        [TestCase("-", 2024, "content_2024.rfa", "other_2024.rfa")]
        [TestCase("-", 2025, "content.rfa", "other.rfa")]
        [TestCase(" ", 2024, "content_2024.rfa", "other_2024.rfa")]
        [TestCase(" ", 2025, "content.rfa", "other.rfa")]
        public void RecognizesLegacyPrefixedNames(string separator, int revitYear, string primary, string alternative)
        {
            var prefix = "Family" + separator;
            AddFamilies(prefix + "content_2024.rfa", prefix + "content.rfa",
                prefix + "other_2024.rfa", prefix + "other.rfa");

            var button = ParseButton(revitYear);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile(prefix + primary)));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(BundleFile(prefix + alternative)));
        }

        /// <summary>Uses the primary family for Ctrl+Click when the unprefixed bundle lacks a compatible alternative.</summary>
        [Test]
        public void RecognizesUnprefixedNamesAndUsesPrimaryWhenAlternativeYearDoesNotMatch()
        {
            AddFamilies("content.rfa", "content_2024.rfa", "other_2019.rfa");

            var button = ParseButton(2024);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile("content_2024.rfa")));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(button?.ScriptPath));
        }

        /// <summary>Excludes bundles whose primary families target other Revit versions.</summary>
        /// <param name="revitYear">The host year, or zero if it is unknown.</param>
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

        /// <summary>Preserves valid explicit paths when conventional families are also present.</summary>
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

        /// <summary>Falls back to conventional primary content when the YAML path cannot be resolved.</summary>
        [Test]
        public void MissingExplicitPrimaryUsesMatchingConvention()
        {
            AddFamilies("Family_content_2019.rfa", "Family_content_2024.rfa");
            CreateFile(Bundle + "bundle.yaml", "content: 'missing.rfa'\ncontent_alt: 'missing-other.rfa'");

            var button = ParseButton(2024);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile("Family_content_2024.rfa")));
            Assert.That(button?.ConfigScriptPath, Is.Null);
        }

        /// <summary>Distinguishes generated commands when the resolved alternative changes without file edits.</summary>
        [Test]
        public void CommandCacheKeyTracksResolvedContentPaths()
        {
            AddFamilies("content.rfa", "other_2023.rfa", "other_2024.rfa");

            Assert.That(ParseExtension(2023).GetHash(), Is.Not.EqualTo(ParseExtension(2024).GetHash()));
        }

        /// <summary>Preserves the cache key when an identical content extension is copied to another directory.</summary>
        [Test]
        public void CommandCacheKeyIsIndependentOfExtensionLocation()
        {
            var timestamp = new DateTime(2024, 1, 1, 0, 0, 0, DateTimeKind.Utc);
            var sharedFamily = CreateFile("Shared.rfa", "");

            string HashExtension(string parent)
            {
                CreateFile(parent + "/" + Panel + "Primary.rfa", "");
                CreateFile(parent + "/" + Bundle + "other_2024.rfa", "");
                var metadata = CreateFile(parent + "/" + Bundle + "bundle.yaml", "content: '../Primary.rfa'");
                var sharedMetadata = CreateFile(parent + "/" + Panel + "Shared.content/bundle.yaml",
                    $"content: '{sharedFamily}'\ncontent_alt: 'missing.rfa'");
                File.SetLastWriteTimeUtc(metadata, timestamp);
                File.SetLastWriteTimeUtc(sharedMetadata, timestamp);

                var root = Path.Combine(TestTempDir, parent, Extension);
                foreach (var directory in Directory.EnumerateDirectories(root, "*", SearchOption.AllDirectories))
                    Directory.SetLastWriteTimeUtc(directory, timestamp);
                Directory.SetLastWriteTimeUtc(root, timestamp);

                return ExtensionParser.ParseInstalledExtensions(root, 2024).Single().GetHash("Roslyn");
            }

            Assert.That(HashExtension("Second/Nested"), Is.EqualTo(HashExtension("First")));
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
