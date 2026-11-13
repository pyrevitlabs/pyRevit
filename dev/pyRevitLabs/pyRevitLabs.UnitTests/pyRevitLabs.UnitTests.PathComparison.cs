using System.IO;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common.Extensions;

namespace pyRevitLabs.UnitTests {
    /// <summary>
    /// Regression tests for #4041: path identity must ignore case and respect directory boundaries.
    /// </summary>
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
    public class PathComparisonTests {
        /// <summary>Case and trailing separators do not affect path identity.</summary>
        [TestMethod]
        public void IsSamePathAs_IgnoresCaseAndTrailingSeparators() {
            Assert.IsTrue(@"C:\pyrevit\bin".IsSamePathAs(@"c:\PYREVIT\BIN\"));
            Assert.IsFalse(@"C:\pyrevit".IsSamePathAs(@"C:\pyrevit2"));
            Assert.IsFalse(@"C:\pyrevit".IsSamePathAs(null));
        }

        /// <summary>Sibling folders sharing a name prefix are not within each other.</summary>
        [TestMethod]
        public void IsPathWithin_MatchesWholeDirectoryNamesOnly() {
            Assert.IsTrue(@"C:\pyrevit\bin\netcore".IsPathWithin(@"C:\pyrevit"));
            Assert.IsTrue(@"c:\PYREVIT".IsPathWithin(@"C:\pyrevit\"));
            Assert.IsFalse(@"C:\pyrevit2\bin\netcore".IsPathWithin(@"C:\pyrevit"));
            Assert.IsFalse(@"C:\pyrevit".IsPathWithin(@"C:\pyrevit\bin"));
        }

        /// <summary>Drive roots, UNC shares and dot segments are resolved before comparing.</summary>
        [TestMethod]
        public void IsPathWithin_HandlesDriveRootsUncSharesAndRelativeSegments() {
            Assert.IsTrue(@"C:\pyrevit".IsPathWithin(@"C:\"));
            Assert.IsTrue(@"\\server\share\pyrevit\bin".IsPathWithin(@"\\server\share\pyrevit\"));
            Assert.IsFalse(@"\\server\share2\pyrevit".IsPathWithin(@"\\server\share"));
            Assert.IsFalse(@"C:\pyrevit\..\other".IsPathWithin(@"C:\pyrevit"));
            Assert.IsTrue(@"C:\pyrevit\x\..\bin".IsPathWithin(@"C:\pyrevit"));
        }

        /// <summary>UNC dot segments are resolved so they cannot escape the parent folder.</summary>
        [TestMethod]
        public void IsPathWithin_UncDotSegments_AreResolved() {
            Assert.IsFalse(@"\\server\share\repo\..\other".IsPathWithin(@"\\server\share\repo"));
            Assert.IsTrue(@"\\server\share\repo\x\..\bin".IsPathWithin(@"\\server\share\repo"));
            Assert.IsTrue(@"\\server\share\repo\..\repo".IsSamePathAs(@"\\server\share\repo"));
        }

        /// <summary>Relative paths resolve against the current directory and invalid ones are rejected.</summary>
        [TestMethod]
        public void ToComparablePath_RelativePaths_AreResolvedAndInvalidOnesRejected() {
            var current = Directory.GetCurrentDirectory();
            Assert.IsTrue(@"sub\..\leaf".IsSamePathAs(Path.Combine(current, "leaf")));
            Assert.IsNull("rel\0ative".ToComparablePath());
            Assert.IsFalse("rel\0ative".IsSamePathAs("rel\0ative"));
        }

        /// <summary>UNC and URL paths differing only by a trailing separator compare identical.</summary>
        [TestMethod]
        public void ToComparablePath_UriPathsDifferingByTrailingSeparator_AreIdentical() {
            Assert.AreEqual(@"\\server\share\pyrevit\".ToComparablePath(), @"\\server\share\pyrevit".ToComparablePath());
            Assert.AreEqual("http://host/repo/".ToComparablePath(), "http://host/repo".ToComparablePath());
        }

        /// <summary>Invalid or empty input yields false or null instead of throwing.</summary>
        [TestMethod]
        public void PathComparison_InvalidOrEmptyInput_ReturnsFalseWithoutThrowing() {
            const string invalid = "C:\\bad\0path";
            Assert.IsNull(invalid.ToComparablePath());
            Assert.IsFalse(invalid.IsPathWithin(@"C:\pyrevit"));
            Assert.IsFalse(@"C:\pyrevit".IsPathWithin(invalid));
            Assert.IsFalse(invalid.IsSamePathAs(invalid));
            Assert.IsFalse("".IsSamePathAs(""));
        }

        /// <summary>A bare separator or empty parent never matches.</summary>
        [TestMethod]
        public void IsPathWithin_BareSeparatorParent_IsNotAMatch() {
            Assert.IsFalse(@"C:\pyrevit".IsPathWithin(@"\"));
            Assert.IsFalse(@"C:\pyrevit".IsPathWithin("/"));
            Assert.IsFalse(@"C:\pyrevit".IsPathWithin(""));
        }
    }
}
