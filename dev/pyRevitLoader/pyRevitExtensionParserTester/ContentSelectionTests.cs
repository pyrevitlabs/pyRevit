using System;
using System.IO;
using System.Linq;
using NUnit.Framework;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Regression coverage for versioned family selection and generated command caching.
    /// </summary>
    /// <remarks>Regression tests for PR #3947.</remarks>
    [TestFixture]
    [Category("HostFree")]
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
        [TestCase("_", 2024, "content_2024.rfa", "other_2024.rfa")]
        [TestCase("_", 2025, "content.rfa", "other.rfa")]
        [TestCase("", 2024, "content_2024.rfa", "other_2024.rfa")]
        [TestCase("", 2025, "content.rfa", "other.rfa")]
        [TestCase(".", 2024, "content_2024.rfa", "other_2024.rfa")]
        [TestCase(".", 2025, "content.rfa", "other.rfa")]
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

        /// <summary>Restores an unversioned family button and uses its primary for Ctrl+Click.</summary>
        [Category("Unit")]
        [Property("Level", "Unit")]
        [TestCase("Window.rfa", 2026)]
        [TestCase("WINDOW.RFA", 2026)]
        [TestCase("Window.rfa", 0)]
        public void SelectsSingleLegacyFamily(string family, int revitYear)
        {
            AddFamilies(family);

            var button = ParseButton(revitYear);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile(family)));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(button?.ScriptPath));
        }

        /// <summary>Conventional primary content takes precedence over arbitrary legacy families.</summary>
        [TestCase(2024, "Z_content_2024.rfa")]
        [TestCase(2026, "Z_content.rfa")]
        [TestCase(0, "Z_content.rfa")]
        public void ConventionalPrimaryPrecedesLegacyFamily(int revitYear, string expected)
        {
            AddFamilies("A_Window.rfa", "Z_content.rfa", "Z_content_2024.rfa");

            Assert.That(ParseButton(revitYear)?.ScriptPath, Is.EqualTo(BundleFile(expected)));
        }

        /// <summary>Exact filenames win over prefixed names for both primary and alternate content.</summary>
        [TestCase(2024, "content_2024.rfa", "other_2024.rfa")]
        [TestCase(2026, "content.rfa", "other.rfa")]
        public void ExactNamesPrecedePrefixedNames(int revitYear, string primary, string alternative)
        {
            AddFamilies("A_" + primary, "A_" + alternative, primary, alternative);

            var button = ParseButton(revitYear);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile(primary)));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(BundleFile(alternative)));
        }

        /// <summary>Unambiguous conventional stems win over accidental legacy suffix matches.</summary>
        [TestCase("_", 2024)]
        [TestCase("-", 2024)]
        [TestCase(" ", 2024)]
        [TestCase(".", 2024)]
        [TestCase("_", 2026)]
        public void ConventionalStemsPrecedeMisleadingSuffixes(string separator, int revitYear)
        {
            var suffix = revitYear == 2024 ? "_2024" : "";
            var primary = "Z" + separator + "content" + suffix + ".rfa";
            var alternative = "Z" + separator + "other" + suffix + ".rfa";
            AddFamilies("A_notcontent" + suffix + ".rfa", "another" + suffix + ".rfa", primary, alternative);

            var button = ParseButton(revitYear);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile(primary)));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(BundleFile(alternative)));
        }

        /// <summary>Matching-year legacy names retain precedence over generic conventional names.</summary>
        [Test]
        public void DelimiterFreeMatchingYearPrecedesGenericConvention()
        {
            AddFamilies("Familycontent_2024.rfa", "Familyother_2024.rfa", "content.rfa", "other.rfa");

            var button = ParseButton(2024);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile("Familycontent_2024.rfa")));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(BundleFile("Familyother_2024.rfa")));
        }

        /// <summary>Incompatible versioned primaries block legacy fallback in mixed bundles.</summary>
        [TestCase("old_content_2024.rfa", 2026)]
        [TestCase("Family-content_2024.rfa", 2026)]
        [TestCase("Family content_2024.rfa", 2026)]
        [TestCase("Familycontent_2024.rfa", 2026)]
        [TestCase("Family_CONTENT_2024.RFA", 0)]
        public void IncompatiblePrimaryBlocksLegacyFallback(string primary, int revitYear)
        {
            AddFamilies(primary, "Window.rfa");

            Assert.That(ParseButton(revitYear), Is.Null);
        }

        /// <summary>Fallback never promotes an alternative or an explicitly versioned arbitrary family.</summary>
        [TestCase("other.rfa")]
        [TestCase("other_2024.rfa")]
        [TestCase("Family-other.rfa")]
        [TestCase("Familyother_2024.rfa")]
        [TestCase("Window_2024.rfa")]
        public void IneligibleLegacyFamilyDoesNotCreateButton(string family)
        {
            AddFamilies(family);

            Assert.That(ParseButton(2026), Is.Null);
        }

        /// <summary>RFA-looking backup filenames do not qualify as primary content.</summary>
        [Test]
        public void RejectsNonFamilyExtensions()
        {
            AddFamilies("content_2026.rfa.bak", "Window.rfa.bak", "script.py");

            Assert.That(ParseButton(2026), Is.Null);
        }

        /// <summary>Legacy primary selection retains matching, generic and primary-fallback alternatives.</summary>
        [TestCase(2024, "Family_other_2024.rfa")]
        [TestCase(2026, "Family_other.rfa")]
        public void LegacyPrimaryUsesConventionalAlternative(int revitYear, string expected)
        {
            AddFamilies("Window.rfa", "Family_other_2024.rfa", "Family_other.rfa");

            var button = ParseButton(revitYear);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile("Window.rfa")));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(BundleFile(expected)));
        }

        /// <summary>An incompatible alternate does not replace a legacy primary on Ctrl+Click.</summary>
        [Test]
        public void LegacyPrimaryIgnoresIncompatibleAlternative()
        {
            AddFamilies("Window.rfa", "other_2024.rfa");

            var button = ParseButton(2026);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile("Window.rfa")));
            Assert.That(button?.ConfigScriptPath, Is.EqualTo(button?.ScriptPath));
        }

        /// <summary>Missing YAML paths allow legacy primary selection without inventing an explicit alternative.</summary>
        [Test]
        public void MissingExplicitPathsPreserveLegacyAlternativeContract()
        {
            AddFamilies("Window.rfa", "other.rfa");
            CreateFile(Bundle + "bundle.yaml", "content: 'missing.rfa'\ncontent_alt: 'missing-other.rfa'");

            var button = ParseButton(2026);

            Assert.That(button?.ScriptPath, Is.EqualTo(BundleFile("Window.rfa")));
            Assert.That(button?.ConfigScriptPath, Is.Null);
        }

        /// <summary>A valid explicit primary overrides incompatible conventional families and legacy candidates.</summary>
        [Test]
        public void ExplicitPrimaryOverridesIncompatibleConventions()
        {
            AddFamilies("content_2024.rfa", "Window.rfa");
            var primary = CreateFile(Panel + "Primary.rfa", "");
            CreateFile(Bundle + "bundle.yaml", "content: '../Primary.rfa'");

            Assert.That(ParseButton(2026)?.ScriptPath, Is.EqualTo(Path.GetFullPath(primary)));
        }

        /// <summary>Changes the assembly filename when only the selected family changes.</summary>
        [Test]
        public void AssemblyFileNameTracksResolvedContentPaths()
        {
            AddFamilies("content.rfa", "other_2023.rfa", "other_2024.rfa");

            var first = ParseExtension(2023);
            var second = ParseExtension(2024);
            var builder = CreateAssemblyBuilder();

            Assert.That(first.GetHash(), Is.Not.EqualTo(second.GetHash()));
            Assert.That(builder.GetAssemblyFileName(first, null, false),
                Is.Not.EqualTo(builder.GetAssemblyFileName(second, null, false)));
        }

        /// <summary>Identical tracked inputs keep their parser hash after relocation and get distinct cached assemblies.</summary>
        [Test]
        public void IdenticalExtensionsUseDistinctAssemblyFileNames()
        {
            var timestamp = new DateTime(2024, 1, 1, 0, 0, 0, DateTimeKind.Utc);
            var sharedFamily = CreateFile("Shared.rfa", "");

            ParsedExtension CreateExtension(string parent)
            {
                CreateFile(parent + "/" + Panel + "Primary.rfa", "");
                CreateFile(parent + "/" + Bundle + "other_2024.rfa", "");
                var metadata = CreateFile(parent + "/" + Bundle + "bundle.yaml", "content: '../Primary.rfa'");
                var sharedMetadata = CreateFile(parent + "/" + Panel + "Shared.content/bundle.yaml",
                    $"content: '{sharedFamily}'\ncontent_alt: 'missing.rfa'");
                File.SetLastWriteTimeUtc(metadata, timestamp);
                File.SetLastWriteTimeUtc(sharedMetadata, timestamp);

                var root = Path.Combine(TestTempDir, parent, Extension);
                foreach (var family in Directory.EnumerateFiles(root, "*.rfa", SearchOption.AllDirectories))
                    File.SetLastWriteTimeUtc(family, timestamp);
                foreach (var directory in Directory.EnumerateDirectories(root, "*", SearchOption.AllDirectories))
                    Directory.SetLastWriteTimeUtc(directory, timestamp);
                Directory.SetLastWriteTimeUtc(root, timestamp);

                return ExtensionParser.ParseInstalledExtensions(root, 2024).Single();
            }

            var first = CreateExtension("First");
            var second = CreateExtension("Second/Nested");
            var builder = CreateAssemblyBuilder();
            var generator = new RoslynCommandTypeGenerator(new MockLogger());
            var firstButton = first.CollectCommandComponents().Single(button => button.ConfigScriptPath != null);
            var secondButton = second.CollectCommandComponents().Single(button => button.ConfigScriptPath != null);

            Assert.That(second.GetHash("Roslyn"), Is.EqualTo(first.GetHash("Roslyn")));
            Assert.That(generator.GenerateExtensionCode(first, "2024"),
                Does.Contain(firstButton.ScriptPath).And.Contain(firstButton.ConfigScriptPath));
            Assert.That(generator.GenerateExtensionCode(second, "2024"),
                Does.Contain(secondButton.ScriptPath).And.Contain(secondButton.ConfigScriptPath)
                    .And.Not.Contain(firstButton.ScriptPath));
            Assert.That(builder.GetAssemblyFileName(second, null, false),
                Is.Not.EqualTo(builder.GetAssemblyFileName(first, null, false)));
        }

        /// <summary>Reuses the assembly filename across builders and equivalent spellings of the same root.</summary>
        [Test]
        public void AssemblyFileNameIsStableForTheSameExtensionLocation()
        {
            AddFamilies("content_2024.rfa");
            var first = ParseExtension(2024);
            var second = ParseExtension(2024);
            second.Directory = Path.Combine(second.Directory, ".") + Path.DirectorySeparatorChar;

            Assert.That(CreateAssemblyBuilder().GetAssemblyFileName(second, null, false),
                Is.EqualTo(CreateAssemblyBuilder().GetAssemblyFileName(first, null, false)));
        }

        private static AssemblyBuilderService CreateAssemblyBuilder()
        {
            return new AssemblyBuilderService("2024", AssemblyBuildStrategy.Roslyn, new MockLogger());
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
