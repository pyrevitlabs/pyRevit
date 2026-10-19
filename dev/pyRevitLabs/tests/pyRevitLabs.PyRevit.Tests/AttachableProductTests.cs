using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;

using pyRevitLabs.Common;
using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;
using pyRevitLabs.PyRevit;
using pyRevitLabs.TargetApps.Revit;

using Assert = Microsoft.VisualStudio.TestTools.UnitTesting.Assert;
using CollectionAssert = Microsoft.VisualStudio.TestTools.UnitTesting.CollectionAssert;
using StringAssert = Microsoft.VisualStudio.TestTools.UnitTesting.StringAssert;
namespace pyRevitLabs.PyRevit.Tests {
    /// <summary>
    /// Covers which installed Revits a clone may be attached to.
    /// </summary>
    /// <remarks>
    /// An attachment is a manifest file, so writing one for a product this line
    /// cannot run on leaves a host pointing at a loader it will fail to load, and
    /// writing one for a stale registry entry points a Revit that is not installed.
    /// "Installed" is therefore not the same question as "attachable".
    /// </remarks>
    [TestClass()]
    [DoNotParallelize]
    [TestCategory("Revit")]
    [TestCategory("Integration")]
    public class AttachableProductTests {
        private const string LevelSeparator = "|";
        private const string NotAttaching = "Not attaching to Revit";

        private LoggingConfiguration? _previousConfig;
        private MemoryTarget _capture = null!;

        [TestInitialize()]
        public void StartCapturingLog() {
            _previousConfig = LogManager.Configuration;
            _capture = new MemoryTarget("attachableProductReports") {
                Layout = "${level}" + LevelSeparator + "${message}"
            };
            var config = new LoggingConfiguration();
            config.AddTarget(_capture);
            config.AddRuleForAllLevels(_capture);
            LogManager.Configuration = config;
            LogManager.ReconfigExistingLoggers();
        }

        [TestCleanup()]
        public void StopCapturingLog() {
            LogManager.Configuration = _previousConfig;
            LogManager.ReconfigExistingLoggers();
            _capture?.Dispose();
        }

        private string Report(string level) {
            var prefix = level + LevelSeparator;
            return string.Join(Environment.NewLine, _capture.Logs.Where(line => line.StartsWith(prefix)));
        }

        private static List<RevitProduct> BelowMinimumInstalledProducts() {
            var belowMinimum = RevitProduct.ListInstalledProducts()
                                              .Where(prod => !prod.IsSupported && prod.ProductYear > 0)
                                              .ToList();
            if (belowMinimum.Count == 0)
                Assert.Inconclusive("No Revit below the minimum supported year is installed on this machine");
            return belowMinimum;
        }

        [TestMethod()]
        public void GetAttachableProducts_NeverReturnsAProductThisLineCanNotRunOn() {
            foreach (var product in PyRevitAttachments.GetAttachableProducts()) {
                Assert.IsTrue(product.IsSupported,
                              "Revit " + product.ProductYear + " is below the minimum supported year but was offered as attachable");
                Assert.IsTrue(CommonUtils.VerifyFile(product.ExecutiveLocation),
                              "Revit " + product.ProductYear + " has no executable at \"" + product.ExecutiveLocation
                              + "\" but was offered as attachable");
            }
        }

        [TestMethod()]
        public void GetAttachableProducts_ExcludesBelowMinimumInstalledRevits() {
            var belowMinimum = BelowMinimumInstalledProducts();
            var attachableYears = PyRevitAttachments.GetAttachableProducts().Select(prod => prod.ProductYear).ToList();

            foreach (var product in belowMinimum)
                Assert.IsFalse(attachableYears.Contains(product.ProductYear),
                               "pyrevit attach --installed would write a manifest for Revit " + product.ProductYear
                               + ", pointing it at a loader that line can not load");
        }

        [TestMethod()]
        public void GetAttachableProducts_SaysWhyItSkippedEachBelowMinimumRevit() {
            var belowMinimum = BelowMinimumInstalledProducts();

            PyRevitAttachments.GetAttachableProducts();

            var report = Report("Warn");
            StringAssert.Contains(report, NotAttaching);
            foreach (var product in belowMinimum)
                StringAssert.Contains(report, product.ProductYear.ToString());
        }

        [TestMethod()]
        public void GetAttachableProducts_KeepsEverySupportedInstalledRevit() {
            var supported = RevitProduct.ListInstalledProducts()
                                           .Where(prod => prod.IsSupported
                                                         && prod.ProductYear > 0
                                                         && CommonUtils.VerifyFile(prod.ExecutiveLocation))
                                           .ToList();
            if (supported.Count == 0)
                Assert.Inconclusive("No supported Revit with a readable executable is installed on this machine");
            var attachableYears = PyRevitAttachments.GetAttachableProducts().Select(prod => prod.ProductYear).ToList();

            foreach (var product in supported)
                Assert.IsTrue(attachableYears.Contains(product.ProductYear),
                              "Revit " + product.ProductYear + " is supported and installed, so it must stay attachable");
        }
    }

    /// <summary>
    /// Covers the attachable-product filter against a known set of products, so the
    /// rule is checked on every machine rather than only where an old Revit happens
    /// to be installed.
    /// </summary>
    [TestClass()]
    [DoNotParallelize]
    [TestCategory("HostFree")]
    [TestCategory("Integration")]
    public class AttachableProductFilterTests {
        private const int BelowMinimumYear = 2017;
        private const int SupportedYear = 2025;
        private const string BelowMinimumVersion = "17.0.416.0";
        private const string SupportedVersion = "25.0.2.419";

        private string _tempRoot = null!;

        [TestInitialize()]
        public void CreateFakeRevitInstalls() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyrevit-attachable-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
        }

        [TestCleanup()]
        public void RemoveFakeRevitInstalls() {
            if (_tempRoot != null && Directory.Exists(_tempRoot))
                Directory.Delete(_tempRoot, recursive: true);
        }

        /// <summary>
        /// Build a product the way the registry scan would, then point it at a fake
        /// install directory so the executable check is decided by that directory.
        /// </summary>
        private static RevitProduct FakeProduct(string release, string version, string installPath, bool withExecutable) {
            var hostInfo = new HostProductInfo {
                meta = new HostProductInfoMeta { schema = "1.0" },
                product = "Autodesk Revit",
                release = release,
                version = version,
                build = "20200101_0000",
                target = "x64"
            };
            var product = (RevitProduct)Activator.CreateInstance(
                typeof(RevitProduct),
                BindingFlags.Instance | BindingFlags.NonPublic,
                null,
                new object[] { hostInfo, false },
                null)!;
            Directory.CreateDirectory(installPath);
            if (withExecutable)
                File.WriteAllText(Path.Combine(installPath, "Revit.exe"), string.Empty);
            product.InstallLocation = installPath;
            return product;
        }

        private RevitProduct BelowMinimumWithExecutable() {
            return FakeProduct("Autodesk Revit 2017", BelowMinimumVersion,
                               Path.Combine(_tempRoot, "Revit 2017"), withExecutable: true);
        }

        private RevitProduct SupportedWithExecutable() {
            return FakeProduct("2025 First Customer Ship", SupportedVersion,
                               Path.Combine(_tempRoot, "Revit 2025"), withExecutable: true);
        }

        private RevitProduct SupportedWithoutExecutable() {
            return FakeProduct("2026 First Customer Ship", "26.0.4.409",
                               Path.Combine(_tempRoot, "Revit 2026"), withExecutable: false);
        }

        private RevitProduct Supported2025WithoutExecutable() {
            return FakeProduct("2025 First Customer Ship - German", SupportedVersion,
                               Path.Combine(_tempRoot, "Revit 2025 German"), withExecutable: false);
        }

        [TestMethod()]
        public void IsAttachableProductYear_RejectsBelowMinimumAndAcceptsSupported() {
            Assert.IsFalse(PyRevitAttachments.IsAttachableProductYear(BelowMinimumYear));
            Assert.IsTrue(PyRevitAttachments.IsAttachableProductYear(SupportedYear));
            Assert.IsTrue(PyRevitAttachments.IsAttachableProductYear(RevitProductData.MinimumSupportedProductYear));
        }

        [TestMethod()]
        public void IsAttachable_RejectsBelowMinimumEvenWithAWorkingExecutable() {
            Assert.IsFalse(PyRevitAttachments.IsAttachable(BelowMinimumWithExecutable()));
        }

        [TestMethod()]
        public void IsAttachable_RejectsSupportedYearWithNoExecutableOnDisk() {
            Assert.IsFalse(PyRevitAttachments.IsAttachable(SupportedWithoutExecutable()));
        }

        [TestMethod()]
        public void IsAttachable_AcceptsSupportedYearWithExecutableOnDisk() {
            Assert.IsTrue(PyRevitAttachments.IsAttachable(SupportedWithExecutable()));
        }

        /// <summary>
        /// A bulk reattachment must not apply a looser rule than a direct attach, so
        /// the two have to agree about every product in a known set.
        /// </summary>
        [TestMethod()]
        public void IsAttachable_AgreesWithTheFilterUsedForBulkAttach() {
            var products = new[] {
                BelowMinimumWithExecutable(),
                SupportedWithExecutable(),
                SupportedWithoutExecutable()
            };
            var filtered = PyRevitAttachments.GetAttachableProducts(products);

            foreach (var product in products) {
                var expected = PyRevitAttachments.IsAttachable(product);
                Assert.AreEqual(expected, filtered.Contains(product),
                                "Revit " + product.ProductYear + ": the bulk filter and the per-product rule disagree");
            }
        }

        /// <summary>
        /// The registry scan also matches localized installs such as "Revit 2025 - German"
        /// and does not merge them, so one year can come back twice. A stale entry must
        /// not veto the year when a good install of the same year also exists.
        /// </summary>
        [TestMethod()]
        public void SelectProductForAttach_PrefersTheInstallThatWorksOverAStaleOneOfTheSameYear() {
            var staleLocalized = Supported2025WithoutExecutable();
            var good = SupportedWithExecutable();

            var selected = PyRevitAttachments.SelectProductForAttach(SupportedYear, new[] { staleLocalized, good });

            Assert.AreSame(good, selected,
                           "A broken 2025 entry must not block attaching to a working 2025 install");
        }

        [TestMethod()]
        public void SelectProductForAttach_FallsBackToAStaleEntrySoTheReasonIsStillReported() {
            var stale = Supported2025WithoutExecutable();

            var selected = PyRevitAttachments.SelectProductForAttach(SupportedYear, new[] { stale });

            Assert.AreSame(stale, selected,
                           "With only a stale entry the year must still be reported rather than silently accepted");
        }

        [TestMethod()]
        public void SelectProductForAttach_ReturnsNullForAYearThatIsNotInstalled() {
            Assert.IsNull(PyRevitAttachments.SelectProductForAttach(
                              SupportedYear,
                              new[] { BelowMinimumWithExecutable() }),
                          "Attaching ahead of an install must keep working");
        }

        [TestMethod()]
        public void GetAttachableProducts_DropsBelowMinimumProductFromAKnownSet() {
            var belowMinimum = BelowMinimumWithExecutable();

            var attachable = PyRevitAttachments.GetAttachableProducts(new[] { belowMinimum });

            Assert.AreEqual(0, attachable.Count,
                            "A below-minimum product with a perfectly good executable is still not attachable");
        }

        [TestMethod()]
        public void GetAttachableProducts_KeepsSupportedProductFromAKnownSet() {
            var supported = SupportedWithExecutable();

            var attachable = PyRevitAttachments.GetAttachableProducts(new[] { supported });

            Assert.AreEqual(1, attachable.Count);
            Assert.AreEqual(SupportedYear, attachable[0].ProductYear);
        }

        [TestMethod()]
        public void GetAttachableProducts_DropsSupportedProductWithNoExecutableOnDisk() {
            var missing = SupportedWithoutExecutable();

            var attachable = PyRevitAttachments.GetAttachableProducts(new[] { missing });

            Assert.AreEqual(0, attachable.Count,
                            "A registry entry whose Revit.exe is gone must not get a manifest written for it");
        }

        [TestMethod()]
        public void GetAttachableProducts_KeepsOnlyTheSupportedOnesFromAMixedSet() {
            var attachable = PyRevitAttachments.GetAttachableProducts(new[] {
                BelowMinimumWithExecutable(),
                SupportedWithExecutable(),
                SupportedWithoutExecutable()
            });

            Assert.AreEqual(1, attachable.Count);
            Assert.AreEqual(SupportedYear, attachable[0].ProductYear);
        }
    }
}
