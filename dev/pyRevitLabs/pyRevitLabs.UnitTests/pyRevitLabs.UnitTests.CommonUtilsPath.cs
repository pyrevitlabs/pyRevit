using System;
using System.IO;
using System.IO.Compression;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    public class CommonUtilsPathTests {
        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousTemp;
        private string _previousLocalAppData;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitPathTests_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            _previousPyRevitPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
            _previousTemp = Environment.GetEnvironmentVariable("TEMP");
            _previousLocalAppData = Environment.GetEnvironmentVariable("LOCALAPPDATA");
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                Path.Combine(_tempRoot, "AppDataPyRevit"));
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);
        }

        [TestCleanup]
        public void Cleanup() {
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                _previousPyRevitPathOverride);
            Environment.SetEnvironmentVariable("TEMP", _previousTemp);
            Environment.SetEnvironmentVariable("LOCALAPPDATA", _previousLocalAppData);
            if (Directory.Exists(_tempRoot))
                Directory.Delete(_tempRoot, recursive: true);
        }

        [TestMethod]
        public void ExpandEnvironmentPath_ExpandsNestedVariables() {
            Environment.SetEnvironmentVariable("LOCALAPPDATA", _tempRoot);
            var expanded = CommonUtils.ExpandEnvironmentPath("%LOCALAPPDATA%\\pyRevit");
            Assert.AreEqual(Path.Combine(_tempRoot, "pyRevit"), expanded);
        }

        [TestMethod]
        public void GetUserTempDirectory_ExpandsPercentTemp() {
            Environment.SetEnvironmentVariable("LOCALAPPDATA", _tempRoot);
            Environment.SetEnvironmentVariable("TEMP", "%LOCALAPPDATA%\\Temp");
            var tempDir = CommonUtils.GetUserTempDirectory();
            Assert.IsFalse(tempDir.Contains("%"), "Temp path should not contain unexpanded variables.");
            StringAssert.StartsWith(tempDir, _tempRoot);
            Assert.IsTrue(tempDir.EndsWith("Temp", StringComparison.OrdinalIgnoreCase));
        }

        [TestMethod]
        public void DeployFromImage_UsesExpandedTempForStaging() {
            var localAppData = Path.Combine(_tempRoot, "LocalAppData");
            Directory.CreateDirectory(localAppData);
            Environment.SetEnvironmentVariable("LOCALAPPDATA", localAppData);
            Environment.SetEnvironmentVariable("TEMP", "%LOCALAPPDATA%\\Temp");

            var zipPath = Path.Combine(_tempRoot, "testclone.zip");
            var destPath = Path.Combine(_tempRoot, "cloneDest");
            var cloneName = "TempDeployTest";
            CreateMinimalCloneZip(zipPath);

            try {
                PyRevitClones.DeployFromImage(
                    cloneName: cloneName,
                    deploymentName: "core",
                    branchName: null,
                    imagePath: zipPath,
                    destPath: destPath,
                    installBinaries: false);

                Assert.IsTrue(Directory.Exists(Path.Combine(destPath, "bin")),
                    "core deployment should copy bin when TEMP is expanded.");
                Assert.IsTrue(Directory.Exists(Path.Combine(destPath, "pyrevitlib", "pyrevit")),
                    "core deployment should copy pyrevitlib when TEMP is expanded.");

                var expandedTemp = CommonUtils.GetUserTempDirectory();
                Assert.IsFalse(expandedTemp.Contains("%"));
                Assert.IsTrue(Directory.Exists(expandedTemp),
                    "Expanded temp directory should exist after staging.");
            }
            finally {
                try {
                    var clone = PyRevitClones.GetRegisteredClone(cloneName);
                    PyRevitClones.UnregisterClone(clone);
                }
                catch {
                    // clone may not have registered if deploy failed
                }
                if (Directory.Exists(destPath))
                    CommonUtils.DeleteDirectory(destPath);
            }
        }

        private static void CreateMinimalCloneZip(string zipPath) {
            var root = Path.Combine(Path.GetDirectoryName(zipPath), "zipcontent");
            if (Directory.Exists(root))
                Directory.Delete(root, recursive: true);
            Directory.CreateDirectory(Path.Combine(root, "bin"));
            Directory.CreateDirectory(Path.Combine(root, "pyrevitlib", "pyrevit"));
            Directory.CreateDirectory(Path.Combine(root, "site-packages"));
            File.WriteAllText(
                Path.Combine(root, "pyRevitfile"),
                "[deployments]\r\ncore = ['bin', 'pyrevitlib', 'site-packages', 'pyRevitfile']\r\n");
            if (File.Exists(zipPath))
                File.Delete(zipPath);
            ZipFile.CreateFromDirectory(root, zipPath);
            Directory.Delete(root, recursive: true);
        }
    }
}
