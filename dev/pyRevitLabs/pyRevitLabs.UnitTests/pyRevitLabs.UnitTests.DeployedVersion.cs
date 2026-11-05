using System;
using System.IO;
using System.Reflection;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    public class DeployedVersionTests {
        private const string VersionFileContent = "9.9.9.99999+9999";
        private const string BuiltAssemblyName = "pyRevitLabs.PyRevit.dll";

        private string _clonePath;

        /// <summary>
        /// A clone is valid to PyRevitClone as long as pyrevitlib/pyrevit exists, so the
        /// fixture is only the version file plus whichever framework trees the test needs.
        /// </summary>
        [TestInitialize]
        public void CreateClone() {
            _clonePath = Path.Combine(
                Path.GetTempPath(), "pyRevitDeployedVersion_" + Guid.NewGuid().ToString("N"));

            var moduleDir = Path.Combine(_clonePath, "pyrevitlib", "pyrevit");
            Directory.CreateDirectory(moduleDir);
            File.WriteAllText(Path.Combine(moduleDir, "version"), VersionFileContent);
        }

        [TestCleanup]
        public void RemoveClone() {
            if (Directory.Exists(_clonePath))
                Directory.Delete(_clonePath, recursive: true);
        }

        private string BuiltAssemblyVersion {
            get {
                var built = PyRevitBuildVersion.FromAssemblyFile(
                    Path.Combine(
                        _clonePath, "bin", PyRevitConsts.NetFxFolder, BuiltAssemblyName));
                return built;
            }
        }

        private void StageBuiltAssembly(string frameworkFolder) {
            var binDir = Path.Combine(_clonePath, "bin", frameworkFolder);
            Directory.CreateDirectory(binDir);
            File.Copy(
                typeof(PyRevitClone).Assembly.Location,
                Path.Combine(binDir, BuiltAssemblyName),
                overwrite: true);
        }

        [TestMethod]
        public void UnbuiltCloneReportsTheVersionFile() {
            Assert.AreEqual(
                VersionFileContent, PyRevitClone.GetDeployedVersion(_clonePath, null));
        }

        [TestMethod]
        public void BuiltCloneReportsTheAssemblyOverTheVersionFile() {
            StageBuiltAssembly(PyRevitConsts.NetFxFolder);

            Assert.AreNotEqual(
                VersionFileContent, PyRevitClone.GetDeployedVersion(_clonePath, null));
            Assert.AreEqual(BuiltAssemblyVersion, PyRevitClone.GetDeployedVersion(_clonePath, null));
        }

        [TestMethod]
        public void RequestedFrameworkSelectsTheTreeToRead() {
            StageBuiltAssembly(PyRevitConsts.NetFxFolder);

            Assert.AreEqual(
                BuiltAssemblyVersion,
                PyRevitClone.GetDeployedVersion(_clonePath, isNetCore: false),
                "A netfx host must read the netfx tree, which is the only one built here.");
        }

        [TestMethod]
        public void MissingRequestedFrameworkFallsBackToTheVersionFile() {
            StageBuiltAssembly(PyRevitConsts.NetFxFolder);

            Assert.AreEqual(
                VersionFileContent,
                PyRevitClone.GetDeployedVersion(_clonePath, isNetCore: true),
                "Asking for a tree the clone does not have must not read the other one.");
        }

        [TestMethod]
        public void VersionFileFallbackIsTrimmed() {
            File.WriteAllText(
                Path.Combine(_clonePath, "pyrevitlib", "pyrevit", "version"),
                VersionFileContent + "\n");

            Assert.AreEqual(VersionFileContent, PyRevitClone.GetDeployedVersion(_clonePath, null));
        }
    }
}
