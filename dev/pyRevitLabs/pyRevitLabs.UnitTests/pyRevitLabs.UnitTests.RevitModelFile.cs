using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.IO;
using System.Linq;
using System.Text;

using OpenMcdf;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.UnitTests.RevitModelFiles {
    /// <summary>
    /// Covers how the Revit version of a model is read from its BasicFileInfo stream.
    /// </summary>
    /// <remarks>
    /// The fixtures are minimal structured storage files laid out like a real model: binary
    /// header, ASCII CRLF, the UTF-16 info text, ASCII CRLF. The info texts are copied from the
    /// Revit 2023 and 2026 sample projects, whose builds are not in the host database.
    /// </remarks>
    [TestClass()]
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

        private string _modelPath;

        [TestInitialize]
        public void CreateModelPath() {
            _modelPath = Path.Combine(Path.GetTempPath(), "pyrevit-modelfile-" + Guid.NewGuid().ToString("N") + ".rvt");
        }

        [TestCleanup]
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

        [TestMethod()]
        public void BuildWithoutDate_FallsBackToTheFormatYear() {
            var model = new RevitModelFile(WriteModel(Revit2026SampleInfo));

            Assert.AreEqual(2026, model.FormatYear);
            Assert.IsNotNull(model.RevitProduct);
            Assert.AreEqual(2026, model.RevitProduct.ProductYear);
            Assert.IsFalse(model.RevitProduct.IsListedInHostsDatabase);
            Assert.AreEqual(@"C:\Autodesk\Snowdon Towers Sample Architectural.rvt", model.LastSavedPath);
        }

        [TestMethod()]
        public void UnlistedBuild_FallsBackToTheFormatYear_AndKeepsTheBuildNumber() {
            var model = new RevitModelFile(WriteModel(Revit2023SampleInfo));

            Assert.IsNotNull(model.RevitProduct);
            Assert.AreEqual(2023, model.RevitProduct.ProductYear);
            Assert.AreEqual("20220108_1515", model.RevitProduct.BuildNumber);
            Assert.IsFalse(model.RevitProduct.IsListedInHostsDatabase);
        }

        [TestMethod()]
        public void UnknownBuild_WithoutFormatYear_StaysUndetected() {
            var model = new RevitModelFile(WriteModel(NoFormatUnknownBuildInfo));

            Assert.AreEqual(0, model.FormatYear);
            Assert.IsNull(model.RevitProduct);
        }

        [TestMethod()]
        public void FromProductYear_IsAYearOnlyProduct() {
            var product = RevitProduct.FromProductYear(2025);

            Assert.AreEqual(2025, product.ProductYear);
            Assert.IsNull(product.Version);
            Assert.AreEqual(string.Empty, product.BuildNumber);
            Assert.IsFalse(product.IsListedInHostsDatabase);
        }
    }
}
