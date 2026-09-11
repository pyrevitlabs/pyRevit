using System;
using System.IO;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    public class PyRevitConfigsTests {
        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousProgramDataPathOverride;
        private string _previousConfigScopeOverride;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitConfigs_" + Guid.NewGuid().ToString("N"));
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
            if (Directory.Exists(_tempRoot)) {
                // seed lock tests may leave read-only files behind
                foreach (var file in Directory.GetFiles(_tempRoot, "*", SearchOption.AllDirectories))
                    File.SetAttributes(file, FileAttributes.Normal);
                Directory.Delete(_tempRoot, recursive: true);
            }
        }

        private void SetScope(string scope) {
            Environment.SetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar, scope);
            PyRevitInstallScope.ClearCachedInstallScope();
        }

        // an admin-locked (read-only) machine config makes the active config
        // resolve to the ProgramData file for any process, elevated or not,
        // reproducing the all-users same-path seeding scenario deterministically
        private string CreateLockedMachineConfig(string content) {
            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath,
                PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(Path.GetDirectoryName(machineConfig));
            File.WriteAllText(machineConfig, content);
            File.SetAttributes(machineConfig, FileAttributes.ReadOnly);
            return machineConfig;
        }

        [TestMethod]
        public void SeedConfig_SamePath_DoesNotThrow() {
            SetScope(PyRevitInstallScope.ConfigScopeAllUsers);
            string machineConfig = CreateLockedMachineConfig("[core]\r\n");

            Assert.AreEqual(
                Path.GetFullPath(machineConfig),
                Path.GetFullPath(PyRevitConsts.ConfigFilePath));
            Assert.AreEqual(
                Path.GetFullPath(machineConfig),
                Path.GetFullPath(PyRevitConsts.AdminConfigFilePath));

            PyRevitConfigs.SeedConfig();

            Assert.AreEqual("[core]\r\n", File.ReadAllText(machineConfig));
        }

        [TestMethod]
        public void SeedConfig_SamePath_WithLock_SetsReadOnly() {
            SetScope(PyRevitInstallScope.ConfigScopeAllUsers);
            string machineConfig = CreateLockedMachineConfig("[core]\r\n");

            PyRevitConfigs.SeedConfig(lockSeedConfig: true);

            Assert.IsTrue(File.GetAttributes(machineConfig).HasFlag(FileAttributes.ReadOnly));
        }

        [TestMethod]
        public void SeedConfig_DifferentPath_CopiesToAdminConfig() {
            SetScope(PyRevitInstallScope.ConfigScopePerUser);

            string configFile = PyRevitConsts.ConfigFilePath;
            string adminConfigFile = PyRevitConsts.AdminConfigFilePath;
            Assert.AreNotEqual(
                Path.GetFullPath(configFile),
                Path.GetFullPath(adminConfigFile));

            Directory.CreateDirectory(Path.GetDirectoryName(adminConfigFile));
            File.WriteAllText(configFile, "[core]\r\nuserlocale = en_us\r\n");

            PyRevitConfigs.SeedConfig();

            Assert.IsTrue(File.Exists(adminConfigFile));
            Assert.AreEqual(File.ReadAllText(configFile), File.ReadAllText(adminConfigFile));
        }
    }
}
