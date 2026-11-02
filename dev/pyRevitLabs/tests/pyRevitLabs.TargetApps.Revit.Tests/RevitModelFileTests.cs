using NUnit.Framework;
using System;
using System.IO;
using System.Linq;
using System.Text;

using OpenMcdf;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.TargetApps.Revit.Tests {
    /// <summary>
    /// Covers how the Revit version of a model is read from its BasicFileInfo stream.
    /// </summary>
    /// <remarks>
    /// The fixtures are minimal structured storage files laid out like a real model: binary
    /// header, ASCII CRLF, the UTF-16 info text, ASCII CRLF. The info texts are copied from the
    /// Revit 2023 and 2026 sample projects, whose builds are not in the host database. The
    /// shared-build cases resolve against the host database this machine loads, and are
    /// inconclusive when it does not list that build for both years.
    /// </remarks>
    [TestFixture()]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Integration")]
    public class RevitModelFileVersionTests {
        private const string Revit2026SampleInfo =
            "Worksharing: Not enabled\r\n"
            + "Username: \r\n"
            + "Central Model Path: \r\n"
            + "Format: 2026\r\n"
            + "Build: 1515(x64)\r\n"
            + "Last Save Path: C:\\Autodesk\\Snowdon Towers Sample Architectural.rvt\r\n"
            + "Open Workset Default: 3\r\n"
            + "Unique Document GUID: 25d81857-eeee-439d-945f-6af8736ac19b\r\n"
            + "Unique Document Increments: 126\r\n"
            + "Author: Autodesk Revit\r\n";

        private const string Revit2023SampleInfo =
            "Worksharing: Not enabled\r\n"
            + "Format: 2023\r\n"
            + "Build: 20220108_1515(x64)\r\n"
            + "Author: Autodesk Revit\r\n";

        private const string NoFormatUnknownBuildInfo =
            "Worksharing: Not enabled\r\n"
            + "Build: 1515(x64)\r\n";

        private const string Shared2022And2023Build = "20241107_1515";

        private string _modelPath;

        [SetUp]
        public void CreateModelPath() {
            _modelPath = Path.Combine(Path.GetTempPath(), "pyrevit-modelfile-" + Guid.NewGuid().ToString("N") + ".rvt");
        }

        [TearDown]
        public void DeleteModel() {
            if (File.Exists(_modelPath))
                File.Delete(_modelPath);
        }

        private string WriteModel(string basicFileInfoText) {
            byte[] header = { 0x04, 0x00, 0x00, 0x00, 0x00, 0x01 };
            byte[] asciiNewLine = { 0x0D, 0x0A };
            byte[] info = header.Concat(asciiNewLine)
                                .Concat(Encoding.Unicode.GetBytes(basicFileInfoText))
                                .Concat(asciiNewLine)
                                .ToArray();

            using (var root = RootStorage.Create(_modelPath))
            using (var stream = root.CreateStream("BasicFileInfo"))
                stream.Write(info, 0, info.Length);

            return _modelPath;
        }

        [Test()]
        public void BuildWithoutDate_FallsBackToTheFormatYear() {
            var model = new RevitModelFile(WriteModel(Revit2026SampleInfo));

            Assert.That(model.FormatYear, Is.EqualTo(2026));
            Assert.That(model.RevitProduct, Is.Not.Null);
            Assert.That(model.RevitProduct.ProductYear, Is.EqualTo(2026));
            Assert.That(model.RevitProduct.IsListedInHostsDatabase, Is.False);
            Assert.That(model.LastSavedPath, Is.EqualTo(@"C:\Autodesk\Snowdon Towers Sample Architectural.rvt"));
        }

        [Test()]
        public void UnlistedBuild_FallsBackToTheFormatYear_AndKeepsTheBuildNumber() {
            var model = new RevitModelFile(WriteModel(Revit2023SampleInfo));

            Assert.That(model.RevitProduct, Is.Not.Null);
            Assert.That(model.RevitProduct.ProductYear, Is.EqualTo(2023));
            Assert.That(model.RevitProduct.BuildNumber, Is.EqualTo("20220108_1515"));
            Assert.That(model.RevitProduct.IsListedInHostsDatabase, Is.False);
        }

        private static void RequireSharedBuildInHostDatabase() {
            var listedYears = RevitProductData.GetAllProductInfo()
                                              .Where(prodInfo => prodInfo?.build == Shared2022And2023Build)
                                              .Select(prodInfo => RevitProductData.GetProductYearFromVersionString(prodInfo.version))
                                              .ToList();
            if (!listedYears.Contains(2022) || !listedYears.Contains(2023))
                Assert.Inconclusive("The host database does not list build " + Shared2022And2023Build + " for both Revit 2022 and 2023");
        }

        [TestCase(2022, "22.1.80.32")]
        [TestCase(2023, "23.1.60.36")]
        public void SharedListedBuild_UsesTheFormatYearToPickTheRecord(int formatYear, string expectedVersion) {
            RequireSharedBuildInHostDatabase();

            var model = new RevitModelFile(WriteModel(
                "Worksharing: Not enabled\r\n"
                + "Format: " + formatYear + "\r\n"
                + "Build: " + Shared2022And2023Build + "(x64)\r\n"));

            Assert.That(model.RevitProduct, Is.Not.Null);
            Assert.That(model.RevitProduct.ProductYear, Is.EqualTo(formatYear));
            Assert.That(model.RevitProduct.Version.ToString(), Is.EqualTo(expectedVersion));
            Assert.That(model.RevitProduct.IsListedInHostsDatabase, Is.True);
        }

        [Test()]
        public void UnknownBuild_WithoutFormatYear_StaysUndetected() {
            var model = new RevitModelFile(WriteModel(NoFormatUnknownBuildInfo));

            Assert.That(model.FormatYear, Is.EqualTo(0));
            Assert.That(model.RevitProduct, Is.Null);
        }

        [Test()]
        public void UnlistedProduct_DescribesTheRecordedBuild() {
            var revit2026 = new RevitModelFile(WriteModel(Revit2026SampleInfo));
            Assert.That(revit2026.CreatedIn, Is.EqualTo("Autodesk Revit 2026 (build 1515(x64), not listed in pyrevit-hosts.json)"));

            DeleteModel();
            var revit2023 = new RevitModelFile(WriteModel(Revit2023SampleInfo));
            Assert.That(revit2023.CreatedIn, Is.EqualTo("Autodesk Revit 2023 (build 20220108_1515(x64), not listed in pyrevit-hosts.json)"));
        }

        [Test()]
        public void FromProductYear_IsAYearOnlyProduct() {
            var product = RevitProduct.FromProductYear(2025);

            Assert.That(product.ProductYear, Is.EqualTo(2025));
            Assert.That(product.Version, Is.Null);
            Assert.That(product.BuildNumber, Is.EqualTo(string.Empty));
            Assert.That(product.IsListedInHostsDatabase, Is.False);
        }
    }
}
