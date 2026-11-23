using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
    public class RevitProductLanguageTests {
        [TestMethod]
        public void ToString_LeavesOutTheLanguageWhenItIsUnknown_Issue4216() {
            var product = RevitProduct.FromProductYear(2025);

            Assert.IsFalse(product.ToString().Contains("Language"));
        }

        [TestMethod]
        public void ToString_ShowsTheLanguageOfARegisteredInstall_Issue4216() {
            var product = RevitProduct.FromProductYear(2025);
            product.LanguageCode = 1033;

            StringAssert.Contains(product.ToString(), "Language: 1033");
        }

        [TestMethod]
        public void FindInstalledLanguageCode_ReturnsZeroForAMissingPath_Issue4216() {
            Assert.AreEqual(0, RevitProduct.FindInstalledLanguageCode(null));
            Assert.AreEqual(0, RevitProduct.FindInstalledLanguageCode(string.Empty));
        }
    }
}
