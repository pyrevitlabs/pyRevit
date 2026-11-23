using NUnit.Framework;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.TargetApps.Revit.Tests {
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class RevitProductLanguageTests {
        [Test]
        public void ToString_LeavesOutTheLanguageWhenItIsUnknown_Issue4216() {
            var product = RevitProduct.FromProductYear(2025);

            Assert.That(product.ToString(), Does.Not.Contain("Language"));
        }

        [Test]
        public void ToString_ShowsTheLanguageOfARegisteredInstall_Issue4216() {
            var product = RevitProduct.FromProductYear(2025);
            product.LanguageCode = 1033;

            Assert.That(product.ToString(), Does.Contain("Language: 1033"));
        }

        [Test]
        public void FindInstalledLanguageCode_ReturnsZeroForAMissingPath_Issue4216() {
            Assert.Multiple(() => {
                Assert.That(RevitProduct.FindInstalledLanguageCode(null), Is.EqualTo(0));
                Assert.That(RevitProduct.FindInstalledLanguageCode(string.Empty), Is.EqualTo(0));
            });
        }
    }
}
