using System.IO;

using NUnit.Framework;

using pyRevitLabs.Common.Extensions;

namespace pyRevitLabs.Common.Tests {
    /// <summary>
    /// Regression tests for #4041: path identity must ignore case and respect directory boundaries.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    [Category("Regression")]
    public class PathComparisonTests {
        /// <summary>Case and trailing separators do not affect path identity.</summary>
        [Test]
        public void IsSamePathAs_IgnoresCaseAndTrailingSeparators() {
            Assert.That(@"C:\pyrevit\bin".IsSamePathAs(@"c:\PYREVIT\BIN\"), Is.True);
            Assert.That(@"C:\pyrevit".IsSamePathAs(@"C:\pyrevit2"), Is.False);
            Assert.That(@"C:\pyrevit".IsSamePathAs(null), Is.False);
        }

        /// <summary>Sibling folders sharing a name prefix are not within each other.</summary>
        [Test]
        public void IsPathWithin_MatchesWholeDirectoryNamesOnly() {
            Assert.That(@"C:\pyrevit\bin\netcore".IsPathWithin(@"C:\pyrevit"), Is.True);
            Assert.That(@"c:\PYREVIT".IsPathWithin(@"C:\pyrevit\"), Is.True);
            Assert.That(@"C:\pyrevit2\bin\netcore".IsPathWithin(@"C:\pyrevit"), Is.False);
            Assert.That(@"C:\pyrevit".IsPathWithin(@"C:\pyrevit\bin"), Is.False);
        }

        /// <summary>Drive roots, UNC shares and dot segments are resolved before comparing.</summary>
        [Test]
        public void IsPathWithin_HandlesDriveRootsUncSharesAndRelativeSegments() {
            Assert.That(@"C:\pyrevit".IsPathWithin(@"C:\"), Is.True);
            Assert.That(@"\\server\share\pyrevit\bin".IsPathWithin(@"\\server\share\pyrevit\"), Is.True);
            Assert.That(@"\\server\share2\pyrevit".IsPathWithin(@"\\server\share"), Is.False);
            Assert.That(@"C:\pyrevit\..\other".IsPathWithin(@"C:\pyrevit"), Is.False);
            Assert.That(@"C:\pyrevit\x\..\bin".IsPathWithin(@"C:\pyrevit"), Is.True);
        }

        /// <summary>UNC dot segments are resolved so they cannot escape the parent folder.</summary>
        [Test]
        public void IsPathWithin_UncDotSegments_AreResolved() {
            Assert.That(@"\\server\share\repo\..\other".IsPathWithin(@"\\server\share\repo"), Is.False);
            Assert.That(@"\\server\share\repo\x\..\bin".IsPathWithin(@"\\server\share\repo"), Is.True);
            Assert.That(@"\\server\share\repo\..\repo".IsSamePathAs(@"\\server\share\repo"), Is.True);
        }

        /// <summary>Relative paths resolve against the current directory and invalid ones are rejected.</summary>
        [Test]
        public void ToComparablePath_RelativePaths_AreResolvedAndInvalidOnesRejected() {
            var current = Directory.GetCurrentDirectory();
            Assert.That(@"sub\..\leaf".IsSamePathAs(Path.Combine(current, "leaf")), Is.True);
            Assert.That("rel\0ative".ToComparablePath(), Is.Null);
            Assert.That("rel\0ative".IsSamePathAs("rel\0ative"), Is.False);
        }

        /// <summary>UNC and URL paths differing only by a trailing separator compare identical.</summary>
        [Test]
        public void ToComparablePath_UriPathsDifferingByTrailingSeparator_AreIdentical() {
            Assert.That(@"\\server\share\pyrevit".ToComparablePath(), Is.EqualTo(@"\\server\share\pyrevit\".ToComparablePath()));
            Assert.That("http://host/repo".ToComparablePath(), Is.EqualTo("http://host/repo/".ToComparablePath()));
        }

        /// <summary>Invalid or empty input yields false or null instead of throwing.</summary>
        [Test]
        public void PathComparison_InvalidOrEmptyInput_ReturnsFalseWithoutThrowing() {
            const string invalid = "C:\\bad\0path";
            Assert.That(invalid.ToComparablePath(), Is.Null);
            Assert.That(invalid.IsPathWithin(@"C:\pyrevit"), Is.False);
            Assert.That(@"C:\pyrevit".IsPathWithin(invalid), Is.False);
            Assert.That(invalid.IsSamePathAs(invalid), Is.False);
            Assert.That("".IsSamePathAs(""), Is.False);
        }

        /// <summary>A bare separator or empty parent never matches.</summary>
        [Test]
        public void IsPathWithin_BareSeparatorParent_IsNotAMatch() {
            Assert.That(@"C:\pyrevit".IsPathWithin(@"\"), Is.False);
            Assert.That(@"C:\pyrevit".IsPathWithin("/"), Is.False);
            Assert.That(@"C:\pyrevit".IsPathWithin(""), Is.False);
        }
    }
}
