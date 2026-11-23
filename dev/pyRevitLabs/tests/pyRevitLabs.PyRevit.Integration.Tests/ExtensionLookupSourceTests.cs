using System.IO;

using NUnit.Framework;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Integration.Tests {
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    public class ExtensionLookupSourceTests {
        private string _folder;

        [SetUp]
        public void CreateFolder() {
            _folder = Path.Combine(Path.GetTempPath(), "pyrevit-sources-" + Path.GetRandomFileName());
            Directory.CreateDirectory(_folder);
        }

        [TearDown]
        public void DeleteFolder() {
            Directory.Delete(_folder, recursive: true);
        }

        private string WriteSource(string fileName, string content) {
            var path = Path.Combine(_folder, fileName);
            File.WriteAllText(path, content);
            return path;
        }

        [Test]
        public void VerifyExtensionLookupSource_AcceptsAnExtensionList_Issue4216() {
            var source = WriteSource("extensions.json", @"{ ""extensions"": [] }");

            Assert.DoesNotThrow(() => PyRevitExtensions.VerifyExtensionLookupSource(source));
        }

        [Test]
        public void VerifyExtensionLookupSource_RejectsAMissingFile_Issue4216() {
            Assert.Throws<PyRevitException>(
                () => PyRevitExtensions.VerifyExtensionLookupSource(Path.Combine(_folder, "missing.json")));
        }

        [Test]
        public void VerifyExtensionLookupSource_RejectsJsonWithoutAnExtensionList_Issue4216() {
            var source = WriteSource("other.json", @"{ ""something"": 1 }");

            Assert.Throws<PyRevitException>(() => PyRevitExtensions.VerifyExtensionLookupSource(source));
        }

        [Test]
        public void VerifyExtensionLookupSource_RejectsInvalidJson_Issue4216() {
            var source = WriteSource("broken.json", "not json");

            Assert.Throws<PyRevitException>(() => PyRevitExtensions.VerifyExtensionLookupSource(source));
        }
    }
}
