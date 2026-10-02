using System;
using System.IO;
using System.Reflection;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    public class PyRevitBuildVersionTests {
        private const string CommitHash = "0746b7c45feca2ad0a1efaa9232585b0402a3980";

        [TestMethod]
        public void Normalize_DropsSdkAppendedCommitHash() {
            Assert.AreEqual(
                "7.0.0.26273+1554",
                PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273+1554." + CommitHash));
        }

        [TestMethod]
        public void Normalize_DropsCommitHashAfterPlus() {
            Assert.AreEqual(
                "7.0.0.26273",
                PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273+" + CommitHash));
        }

        [TestMethod]
        public void Normalize_KeepsPlainBuildMetadata() {
            Assert.AreEqual(
                "7.0.0.26237+2139",
                PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26237+2139"));
        }

        [TestMethod]
        public void Normalize_KeepsChannelSuffix() {
            Assert.AreEqual(
                "7.0.0.26273-wip+1554",
                PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273-wip+1554." + CommitHash));
        }

        [TestMethod]
        public void Normalize_KeepsVersionWithoutBuildMetadata() {
            Assert.AreEqual(
                "7.0.0.26273",
                PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273"));
        }

        [TestMethod]
        public void Normalize_TrimsWhitespace() {
            Assert.AreEqual(
                "7.0.0.26273+1554",
                PyRevitBuildVersion.NormalizeInformationalVersion("  7.0.0.26273+1554\r\n"));
        }

        [TestMethod]
        public void Normalize_UnusableValuesReturnNull() {
            Assert.IsNull(PyRevitBuildVersion.NormalizeInformationalVersion(null));
            Assert.IsNull(PyRevitBuildVersion.NormalizeInformationalVersion(""));
            Assert.IsNull(PyRevitBuildVersion.NormalizeInformationalVersion("   "));
        }

        [TestMethod]
        public void Normalize_DropsEmptyBuildMetadata() {
            Assert.AreEqual(
                "7.0.0.26273",
                PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273+"));
        }

        [TestMethod]
        public void FromAssembly_ReadsLoadedAssemblyStamp() {
            var assembly = typeof(PyRevitBuildVersionTests).Assembly;

            var version = PyRevitBuildVersion.FromAssembly(assembly);

            Assert.IsNotNull(version, "The test assembly must carry an informational version.");
            Assert.IsFalse(
                version.Contains(CommitHash),
                "The commit hash must not be part of the reported version: " + version);
            Assert.IsTrue(
                Version.TryParse(
                    version.Split('+')[0],
                    out _),
                "Reported version must start with a parsable version: " + version);
        }

        [TestMethod]
        public void FromAssembly_MissingAssemblyReturnsNull() {
            Assert.IsNull(PyRevitBuildVersion.FromAssembly(null));
        }

        [TestMethod]
        public void FromAssemblyFile_ReadsStampFromDisk() {
            var assemblyPath = typeof(PyRevitBuildVersionTests).Assembly.Location;

            var version = PyRevitBuildVersion.FromAssemblyFile(assemblyPath);

            Assert.IsNotNull(version, "Must read the version from the assembly on disk: " + assemblyPath);
            Assert.IsFalse(
                version.Contains(CommitHash),
                "The commit hash must not be part of the reported version: " + version);
        }

        [TestMethod]
        public void FromAssemblyFile_MissingFileReturnsNull() {
            Assert.IsNull(PyRevitBuildVersion.FromAssemblyFile(null));
            Assert.IsNull(PyRevitBuildVersion.FromAssemblyFile(string.Empty));
            Assert.IsNull(PyRevitBuildVersion.FromAssemblyFile(
                Path.Combine(Path.GetTempPath(), "no-such-pyrevit-build-7.0.0.26273.dll")));
        }

        [TestMethod]
        public void FromAssemblyFile_NonAssemblyFileReturnsNull() {
            var notAnAssembly = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".dll");
            File.WriteAllText(notAnAssembly, "not a PE image");

            try {
                Assert.IsNull(PyRevitBuildVersion.FromAssemblyFile(notAnAssembly));
            }
            finally {
                File.Delete(notAnAssembly);
            }
        }
    }
}
