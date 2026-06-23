using System;
using System.IO;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    public class PyRevitInstallScopeTests {
        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousProgramDataPathOverride;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitInstallScope_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            _previousPyRevitPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
            _previousProgramDataPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                Path.Combine(_tempRoot, "AppDataPyRevit"));
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                Path.Combine(_tempRoot, "ProgramDataPyRevit"));
            PyRevitInstallScope.ClearCachedInstallScope();
        }

        [TestCleanup]
        public void Cleanup() {
            PyRevitInstallScope.ClearCachedInstallScope();
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                _previousPyRevitPathOverride);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                _previousProgramDataPathOverride);
            if (Directory.Exists(_tempRoot))
                Directory.Delete(_tempRoot, recursive: true);
        }

        [TestMethod]
        public void GetConfigDirectory_WithoutMarker_UsesAppDataPath() {
            Assert.IsFalse(PyRevitInstallScope.IsAllUsersInstall());
            Assert.AreEqual(PyRevitLabsConsts.PyRevitPath, PyRevitInstallScope.GetConfigDirectory());
        }

        [TestMethod]
        public void GetConfigDirectory_WithMarker_UsesProgramDataPath() {
            string programDataPyRevit = PyRevitLabsConsts.PyRevitProgramDataPath;
            Directory.CreateDirectory(programDataPyRevit);
            string markerPath = Path.Combine(programDataPyRevit, PyRevitInstallScope.InstallAllUsersMarkerFileName);
            bool createdMarker = false;
            try {
                File.WriteAllText(markerPath, "AllUsers");
                createdMarker = true;
                PyRevitInstallScope.ClearCachedInstallScope();
                Assert.IsTrue(PyRevitInstallScope.IsAllUsersInstall());
                Assert.AreEqual(PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitInstallScope.GetConfigDirectory());
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                if (createdMarker && File.Exists(markerPath))
                    File.Delete(markerPath);
            }
        }

        [TestMethod]
        public void MigrateSplitAdminConfig_CopiesClonesFromAppDataToProgramData() {
            string programDataPyRevit = PyRevitLabsConsts.PyRevitProgramDataPath;
            string appDataPyRevit = PyRevitLabsConsts.PyRevitPath;
            Directory.CreateDirectory(programDataPyRevit);
            Directory.CreateDirectory(appDataPyRevit);

            string markerPath = Path.Combine(programDataPyRevit, PyRevitInstallScope.InstallAllUsersMarkerFileName);
            string appDataConfig = Path.Combine(appDataPyRevit, PyRevitConsts.DefaultConfigsFileName);
            string programDataConfig = Path.Combine(programDataPyRevit, PyRevitConsts.DefaultConfigsFileName);

            bool createdMarker = false;
            try {
                File.WriteAllText(markerPath, "AllUsers");
                createdMarker = true;
                File.WriteAllText(appDataConfig,
                    "[environment]\r\nclones = {\"master\":\"C:\\\\TestClone\"}\r\n");
                if (File.Exists(programDataConfig))
                    File.Delete(programDataConfig);

                PyRevitInstallScope.ClearCachedInstallScope();
                PyRevitConfigs.GetConfigFile();

                Assert.IsTrue(File.Exists(programDataConfig));
                string migrated = File.ReadAllText(programDataConfig);
                StringAssert.Contains(migrated, "clones");
                StringAssert.Contains(migrated, "TestClone");
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                if (createdMarker && File.Exists(markerPath))
                    File.Delete(markerPath);
                if (File.Exists(appDataConfig))
                    File.Delete(appDataConfig);
                if (File.Exists(programDataConfig))
                    File.Delete(programDataConfig);
            }
        }
    }
}
