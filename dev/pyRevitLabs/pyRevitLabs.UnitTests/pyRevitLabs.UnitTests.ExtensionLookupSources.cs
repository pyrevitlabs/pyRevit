using System.IO;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
    public class ExtensionLookupSourceTests {
        private string _folder;

        [TestInitialize]
        public void CreateFolder() {
            _folder = Path.Combine(Path.GetTempPath(), "pyrevit-sources-" + Path.GetRandomFileName());
            Directory.CreateDirectory(_folder);
        }

        [TestCleanup]
        public void DeleteFolder() {
            Directory.Delete(_folder, recursive: true);
        }

        private string WriteSource(string fileName, string content) {
            var path = Path.Combine(_folder, fileName);
            File.WriteAllText(path, content);
            return path;
        }

        [TestMethod]
        public void VerifyExtensionLookupSource_AcceptsAnExtensionList_Issue4216() {
            var source = WriteSource("extensions.json", @"{ ""extensions"": [] }");

            PyRevitExtensions.VerifyExtensionLookupSource(source);
        }

        [TestMethod]
        public void VerifyExtensionLookupSource_RejectsAMissingFile_Issue4216() {
            Assert.ThrowsException<PyRevitException>(
                () => PyRevitExtensions.VerifyExtensionLookupSource(Path.Combine(_folder, "missing.json")));
        }

        [TestMethod]
        public void VerifyExtensionLookupSource_RejectsJsonWithoutAnExtensionList_Issue4216() {
            var source = WriteSource("other.json", @"{ ""something"": 1 }");

            Assert.ThrowsException<PyRevitException>(() => PyRevitExtensions.VerifyExtensionLookupSource(source));
        }

        [TestMethod]
        public void VerifyExtensionLookupSource_RejectsInvalidJson_Issue4216() {
            var source = WriteSource("broken.json", "not json");

            Assert.ThrowsException<PyRevitException>(() => PyRevitExtensions.VerifyExtensionLookupSource(source));
        }
    }
}
