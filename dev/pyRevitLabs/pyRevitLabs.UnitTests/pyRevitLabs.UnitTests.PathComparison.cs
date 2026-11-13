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
        [TestMethod]
        public void IsSamePathAs_IgnoresCaseAndTrailingSeparators() {
            Assert.IsTrue(@"C:\pyrevit\bin".IsSamePathAs(@"c:\PYREVIT\BIN\"));
            Assert.IsFalse(@"C:\pyrevit".IsSamePathAs(@"C:\pyrevit2"));
            Assert.IsFalse(@"C:\pyrevit".IsSamePathAs(null));
        }

        [TestMethod]
        public void IsPathWithin_MatchesWholeDirectoryNamesOnly() {
            Assert.IsTrue(@"C:\pyrevit\bin\netcore".IsPathWithin(@"C:\pyrevit"));
            Assert.IsTrue(@"c:\PYREVIT".IsPathWithin(@"C:\pyrevit\"));
            Assert.IsFalse(@"C:\pyrevit2\bin\netcore".IsPathWithin(@"C:\pyrevit"));
            Assert.IsFalse(@"C:\pyrevit".IsPathWithin(@"C:\pyrevit\bin"));
        }

        [TestMethod]
        public void IsPathWithin_HandlesDriveRootsUncSharesAndRelativeSegments() {
            Assert.IsTrue(@"C:\pyrevit".IsPathWithin(@"C:\"));
            Assert.IsTrue(@"\\server\share\pyrevit\bin".IsPathWithin(@"\\server\share\pyrevit\"));
            Assert.IsFalse(@"\\server\share2\pyrevit".IsPathWithin(@"\\server\share"));
            Assert.IsFalse(@"C:\pyrevit\..\other".IsPathWithin(@"C:\pyrevit"));
            Assert.IsTrue(@"C:\pyrevit\x\..\bin".IsPathWithin(@"C:\pyrevit"));
        }

        [TestMethod]
        public void ToComparablePath_UriPathsDifferingByTrailingSeparator_AreIdentical() {
            Assert.AreEqual(@"\\server\share\pyrevit\".ToComparablePath(), @"\\server\share\pyrevit".ToComparablePath());
            Assert.AreEqual("http://host/repo/".ToComparablePath(), "http://host/repo".ToComparablePath());
        }

        [TestMethod]
        public void PathComparison_InvalidOrEmptyInput_ReturnsFalseWithoutThrowing() {
            const string invalid = "C:\\bad\0path";
            Assert.IsNull(invalid.ToComparablePath());
            Assert.IsFalse(invalid.IsPathWithin(@"C:\pyrevit"));
            Assert.IsFalse(@"C:\pyrevit".IsPathWithin(invalid));
            Assert.IsFalse(invalid.IsSamePathAs(invalid));
            Assert.IsFalse("".IsSamePathAs(""));
        }

        [TestMethod]
        public void IsPathWithin_BareSeparatorParent_IsNotAMatch() {
            Assert.IsFalse(@"C:\pyrevit".IsPathWithin(@"\"));
            Assert.IsFalse(@"C:\pyrevit".IsPathWithin("/"));
            Assert.IsFalse(@"C:\pyrevit".IsPathWithin(""));
        }
    }
}
