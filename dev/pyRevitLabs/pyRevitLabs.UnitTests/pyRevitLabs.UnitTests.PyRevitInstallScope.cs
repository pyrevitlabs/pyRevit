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
        private string _previousConfigScopeOverride;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitInstallScope_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            _previousPyRevitPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
            _previousProgramDataPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
            _previousConfigScopeOverride = Environment.GetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                Path.Combine(_tempRoot, "AppDataPyRevit"));
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                Path.Combine(_tempRoot, "ProgramDataPyRevit"));
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
        }

        [TestCleanup]
        public void Cleanup() {
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                _previousPyRevitPathOverride);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                _previousProgramDataPathOverride);
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                _previousConfigScopeOverride);
            if (Directory.Exists(_tempRoot))
                Directory.Delete(_tempRoot, recursive: true);
        }

        [TestMethod]
        public void GetConfigDirectory_WithoutMachineScope_UsesAppDataPath() {
            Assert.IsFalse(PyRevitInstallScope.IsAllUsersInstall());
            Assert.AreEqual(PyRevitLabsConsts.PyRevitPath, PyRevitInstallScope.GetConfigDirectory());
        }

        [TestMethod]
        public void GetConfigDirectory_WithLegacyMarker_UsesProgramDataPath() {
            string programDataPyRevit = PyRevitLabsConsts.PyRevitProgramDataPath;
            Directory.CreateDirectory(programDataPyRevit);
            string markerPath = Path.Combine(programDataPyRevit, PyRevitLabsConsts.InstallAllUsersMarkerFileName);
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
        public void GetConfigDirectory_WithScopeOverride_UsesProgramDataPath() {
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();
            Assert.IsTrue(PyRevitInstallScope.IsAllUsersInstall());
            Assert.AreEqual(PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitInstallScope.GetConfigDirectory());
        }

        [TestMethod]
        public void IsAllUsersInstall_DetectsProgramFilesInstallRoot() {
            var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            if (string.IsNullOrWhiteSpace(programFiles))
                Assert.Inconclusive("Program Files folder is not available on this machine.");

            try {
                PyRevitInstallScope.SetRuntimeInstallRoot(Path.Combine(programFiles, "pyRevit-Master"));
                PyRevitInstallScope.ClearCachedInstallScope();
                Assert.IsTrue(PyRevitInstallScope.IsAllUsersInstall());
            }
            finally {
                PyRevitInstallScope.SetRuntimeInstallRoot(null);
                PyRevitInstallScope.ClearCachedInstallScope();
            }
        }

        [TestMethod]
        public void MigrateSplitAdminConfig_MergesClonesAndExtensionSections() {
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);

            string programDataPyRevit = PyRevitLabsConsts.PyRevitProgramDataPath;
            string appDataPyRevit = PyRevitLabsConsts.PyRevitPath;
            Directory.CreateDirectory(programDataPyRevit);
            Directory.CreateDirectory(appDataPyRevit);

            string appDataConfig = Path.Combine(appDataPyRevit, PyRevitLabsConsts.DefaultConfigsFileName);
            string programDataConfig = Path.Combine(programDataPyRevit, PyRevitLabsConsts.DefaultConfigsFileName);

            try {
                File.WriteAllText(appDataConfig,
                    "[environment]\r\nclones = {\"master\":\"C:\\\\TestClone\"}\r\n" +
                    "[pyRevitTags.extension]\r\ndisabled = true\r\n");
                File.WriteAllText(programDataConfig,
                    "[pyRevitTemplates.extension]\r\ndisabled = true\r\n");

                PyRevitInstallScope.ClearCachedInstallScope();
                PyRevitConfigs.GetConfigFile();

                string merged = File.ReadAllText(programDataConfig);
                StringAssert.Contains(merged, "clones");
                StringAssert.Contains(merged, "TestClone");
                StringAssert.Contains(merged, "pyRevitTags.extension");
                StringAssert.Contains(merged, "pyRevitTemplates.extension");
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                if (File.Exists(appDataConfig))
                    File.Delete(appDataConfig);
                if (File.Exists(programDataConfig))
                    File.Delete(programDataConfig);
            }
        }

        [TestMethod]
        public void SeedShippedExtensionDefaults_WritesDisabledForOptOutExtensions() {
            string appDataPyRevit = PyRevitLabsConsts.PyRevitPath;
            Directory.CreateDirectory(appDataPyRevit);
            string configPath = Path.Combine(appDataPyRevit, PyRevitLabsConsts.DefaultConfigsFileName);

            string cloneRoot = Path.Combine(_tempRoot, "TestClone");
            string extensionsRoot = Path.Combine(cloneRoot, "extensions");
            string extDir = Path.Combine(extensionsRoot, "OptOutExt.extension");
            Directory.CreateDirectory(extDir);
            File.WriteAllText(
                Path.Combine(extDir, "extension.json"),
                "{\"builtin\":\"False\",\"default_enabled\":\"False\",\"type\":\"extension\"," +
                "\"rocket_mode_compatible\":\"False\",\"name\":\"OptOutExt\",\"description\":\"test\"}\n");

            try {
                File.WriteAllText(configPath, "[core]\r\n");
                var probe = new PyRevitExtension(extDir);
                Assert.IsNotNull(probe.Definition, "extension.json should parse");
                Assert.IsFalse(probe.Definition.DefaultEnabled, "default_enabled should be false");
                PyRevitInstallScope.ClearCachedInstallScope();
                PyRevitConfigs.SeedShippedExtensionDefaults(cloneRoot);

                string seeded = File.ReadAllText(configPath);
                StringAssert.Contains(seeded, "OptOutExt.extension");
                StringAssert.Contains(seeded, "disabled");
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                if (File.Exists(configPath))
                    File.Delete(configPath);
            }
        }
    }
}
