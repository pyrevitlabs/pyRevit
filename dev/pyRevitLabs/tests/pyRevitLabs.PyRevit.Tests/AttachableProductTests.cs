using NUnit.Framework;
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
    [TestFixture()]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [NonParallelizable]
    [Category("Revit")]
    [Category("Integration")]
    public class AttachableProductTests {
        private const string LevelSeparator = "|";
        private const string NotAttaching = "Not attaching to Revit";

        private LoggingConfiguration? _previousConfig;
        private MemoryTarget _capture = null!;

        [SetUp()]
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

        [TearDown()]
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

        [Test()]
        public void GetAttachableProducts_NeverReturnsAProductThisLineCanNotRunOn() {
            foreach (var product in PyRevitAttachments.GetAttachableProducts()) {
                Assert.That(product.IsSupported, Is.True, "Revit " + product.ProductYear + " is below the minimum supported year but was offered as attachable");
                Assert.That(CommonUtils.VerifyFile(product.ExecutiveLocation), Is.True, "Revit " + product.ProductYear + " has no executable at \"" + product.ExecutiveLocation
                              + "\" but was offered as attachable");
            }
        }

        [Test()]
        public void GetAttachableProducts_ExcludesBelowMinimumInstalledRevits() {
            var belowMinimum = BelowMinimumInstalledProducts();
            var attachableYears = PyRevitAttachments.GetAttachableProducts().Select(prod => prod.ProductYear).ToList();

            foreach (var product in belowMinimum)
                Assert.That(attachableYears.Contains(product.ProductYear), Is.False, "pyrevit attach --installed would write a manifest for Revit " + product.ProductYear
                               + ", pointing it at a loader that line can not load");
        }

        [Test()]
        public void GetAttachableProducts_SaysWhyItSkippedEachBelowMinimumRevit() {
            var belowMinimum = BelowMinimumInstalledProducts();

            PyRevitAttachments.GetAttachableProducts();

            var report = Report("Warn");
            Assert.That(report, Does.Contain(NotAttaching));
            foreach (var product in belowMinimum)
                Assert.That(report, Does.Contain(product.ProductYear.ToString()));
        }

        [Test()]
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
                Assert.That(attachableYears.Contains(product.ProductYear), Is.True, "Revit " + product.ProductYear + " is supported and installed, so it must stay attachable");
        }
    }

    /// <summary>
    /// Covers the attachable-product filter against a known set of products, so the
    /// rule is checked on every machine rather than only where an old Revit happens
    /// to be installed.
    /// </summary>
    [TestFixture()]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Integration")]
    public class AttachableProductFilterTests {
        private const int BelowMinimumYear = 2017;
        private const int SupportedYear = 2025;
        private const string BelowMinimumVersion = "17.0.416.0";
        private const string SupportedVersion = "25.0.2.419";

        private string _tempRoot = null!;

        [SetUp()]
        public void CreateFakeRevitInstalls() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyrevit-attachable-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
        }

        [TearDown()]
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

        [Test()]
        public void IsAttachableProductYear_RejectsBelowMinimumAndAcceptsSupported() {
            Assert.That(PyRevitAttachments.IsAttachableProductYear(BelowMinimumYear), Is.False);
            Assert.That(PyRevitAttachments.IsAttachableProductYear(SupportedYear), Is.True);
            Assert.That(PyRevitAttachments.IsAttachableProductYear(RevitProductData.MinimumSupportedProductYear), Is.True);
        }

        [Test()]
        public void IsAttachable_RejectsBelowMinimumEvenWithAWorkingExecutable() {
            Assert.That(PyRevitAttachments.IsAttachable(BelowMinimumWithExecutable()), Is.False);
        }

        [Test()]
        public void IsAttachable_RejectsSupportedYearWithNoExecutableOnDisk() {
            Assert.That(PyRevitAttachments.IsAttachable(SupportedWithoutExecutable()), Is.False);
        }

        [Test()]
        public void IsAttachable_AcceptsSupportedYearWithExecutableOnDisk() {
            Assert.That(PyRevitAttachments.IsAttachable(SupportedWithExecutable()), Is.True);
        }

        /// <summary>
        /// A bulk reattachment must not apply a looser rule than a direct attach, so
        /// the two have to agree about every product in a known set.
        /// </summary>
        [Test()]
        public void IsAttachable_AgreesWithTheFilterUsedForBulkAttach() {
            var products = new[] {
                BelowMinimumWithExecutable(),
                SupportedWithExecutable(),
                SupportedWithoutExecutable()
            };
            var filtered = PyRevitAttachments.GetAttachableProducts(products);

            foreach (var product in products) {
                var expected = PyRevitAttachments.IsAttachable(product);
                Assert.That(filtered.Contains(product), Is.EqualTo(expected), "Revit " + product.ProductYear + ": the bulk filter and the per-product rule disagree");
            }
        }

        /// <summary>
        /// The registry scan also matches localized installs such as "Revit 2025 - German"
        /// and does not merge them, so one year can come back twice. A stale entry must
        /// not veto the year when a good install of the same year also exists.
        /// </summary>
        [Test()]
        public void SelectProductForAttach_PrefersTheInstallThatWorksOverAStaleOneOfTheSameYear() {
            var staleLocalized = Supported2025WithoutExecutable();
            var good = SupportedWithExecutable();

            var selected = PyRevitAttachments.SelectProductForAttach(SupportedYear, new[] { staleLocalized, good });

            Assert.That(selected, Is.SameAs(good), "A broken 2025 entry must not block attaching to a working 2025 install");
        }

        [Test()]
        public void SelectProductForAttach_FallsBackToAStaleEntrySoTheReasonIsStillReported() {
            var stale = Supported2025WithoutExecutable();

            var selected = PyRevitAttachments.SelectProductForAttach(SupportedYear, new[] { stale });

            Assert.That(selected, Is.SameAs(stale), "With only a stale entry the year must still be reported rather than silently accepted");
        }

        [Test()]
        public void SelectProductForAttach_ReturnsNullForAYearThatIsNotInstalled() {
            Assert.That(PyRevitAttachments.SelectProductForAttach(
                              SupportedYear,
                              new[] { BelowMinimumWithExecutable() }), Is.Null, "Attaching ahead of an install must keep working");
        }

        [Test()]
        public void GetAttachableProducts_DropsBelowMinimumProductFromAKnownSet() {
            var belowMinimum = BelowMinimumWithExecutable();

            var attachable = PyRevitAttachments.GetAttachableProducts(new[] { belowMinimum });

            Assert.That(attachable.Count, Is.EqualTo(0), "A below-minimum product with a perfectly good executable is still not attachable");
        }

        [Test()]
        public void GetAttachableProducts_KeepsSupportedProductFromAKnownSet() {
            var supported = SupportedWithExecutable();

            var attachable = PyRevitAttachments.GetAttachableProducts(new[] { supported });

            Assert.That(attachable.Count, Is.EqualTo(1));
            Assert.That(attachable[0].ProductYear, Is.EqualTo(SupportedYear));
        }

        [Test()]
        public void GetAttachableProducts_DropsSupportedProductWithNoExecutableOnDisk() {
            var missing = SupportedWithoutExecutable();

            var attachable = PyRevitAttachments.GetAttachableProducts(new[] { missing });

            Assert.That(attachable.Count, Is.EqualTo(0), "A registry entry whose Revit.exe is gone must not get a manifest written for it");
        }

        [Test()]
        public void GetAttachableProducts_KeepsOnlyTheSupportedOnesFromAMixedSet() {
            var attachable = PyRevitAttachments.GetAttachableProducts(new[] {
                BelowMinimumWithExecutable(),
                SupportedWithExecutable(),
                SupportedWithoutExecutable()
            });

            Assert.That(attachable.Count, Is.EqualTo(1));
            Assert.That(attachable[0].ProductYear, Is.EqualTo(SupportedYear));
        }
    }
}
