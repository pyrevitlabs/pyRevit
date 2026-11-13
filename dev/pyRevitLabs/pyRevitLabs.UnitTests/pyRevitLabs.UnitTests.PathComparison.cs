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
    }
}
