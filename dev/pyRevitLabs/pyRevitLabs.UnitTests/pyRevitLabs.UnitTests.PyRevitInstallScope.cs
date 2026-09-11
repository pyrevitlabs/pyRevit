using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;
using pyRevitExtensionParser;
using ExtensionParserConfig = pyRevitExtensionParser.PyRevitConfig;

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

        private static void AssertRequiresNonElevatedWindowsProcess() {
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                return;
            if (UserEnv.IsRunAsElevated())
                Assert.Inconclusive("Test requires a non-elevated Windows process.");
        }

        [TestMethod]
        public void GetActiveConfig_AllUsers_WritableMachineConfig_NonElevated_UsesUserConfig() {
            AssertRequiresNonElevatedWindowsProcess();
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();

            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            const string seedContent = "[core]\r\ncheckupdates = false\r\n";
            File.WriteAllText(machineConfig, seedContent);

            var active = PyRevitInstallScope.GetActiveConfig();
            string expectedUserConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Assert.AreEqual(expectedUserConfig, active.ConfigPath);
            Assert.IsFalse(active.IsMachineConfig);
            Assert.IsFalse(active.IsReadOnly);
            Assert.IsTrue(File.Exists(expectedUserConfig));
            Assert.AreEqual(seedContent, File.ReadAllText(expectedUserConfig));
        }

        [TestMethod]
        public void GetActiveConfig_AllUsers_WritableMachineConfig_Elevated_UsesMachineConfig() {
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("Elevation detection is only available on Windows.");
            if (!UserEnv.IsRunAsElevated())
                Assert.Inconclusive("Test requires an elevated Windows process.");

            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();

            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            File.WriteAllText(machineConfig, "[core]\r\n");

            var active = PyRevitInstallScope.GetActiveConfig();
            Assert.AreEqual(machineConfig, active.ConfigPath);
            Assert.IsTrue(active.IsMachineConfig);
            Assert.IsFalse(active.IsReadOnly);
        }

        [TestMethod]
        public void GetActiveConfig_AllUsers_MissingMachineConfig_NonElevated_CreatesUserConfig() {
            AssertRequiresNonElevatedWindowsProcess();
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();

            var active = PyRevitInstallScope.GetActiveConfig();
            string expectedUserConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            string expectedMachineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Assert.AreEqual(expectedUserConfig, active.ConfigPath);
            Assert.IsFalse(active.IsMachineConfig);
            Assert.IsFalse(active.IsReadOnly);
            Assert.IsTrue(File.Exists(expectedUserConfig));
            Assert.IsFalse(File.Exists(expectedMachineConfig));
        }

        [TestMethod]
        public void GetActiveConfig_AllUsers_MissingMachineConfig_Elevated_CreatesMachineConfig() {
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("Elevation detection is only available on Windows.");
            if (!UserEnv.IsRunAsElevated())
                Assert.Inconclusive("Test requires an elevated Windows process.");

            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();

            var active = PyRevitInstallScope.GetActiveConfig();
            string expected = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Assert.AreEqual(expected, active.ConfigPath);
            Assert.IsTrue(active.IsMachineConfig);
            Assert.IsFalse(active.IsReadOnly);
            Assert.IsTrue(File.Exists(expected));
        }

        [TestMethod]
        public void GetActiveConfig_AllUsers_UnreadableMachineSeed_CreatesWritableUserConfig() {
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("Exclusive file sharing is only enforced on Windows.");
            AssertRequiresNonElevatedWindowsProcess();

            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();

            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            const string seedContent = "[core]\r\ncheckupdates = false\r\n";
            File.WriteAllText(machineConfig, seedContent);

            // exclusive share blocks seeding but must not block creating a user ini
            using (File.Open(machineConfig, FileMode.Open, FileAccess.ReadWrite, FileShare.None)) {
                var active = PyRevitInstallScope.GetActiveConfig();

                string expectedUserConfig = Path.Combine(
                    PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
                Assert.AreEqual(expectedUserConfig, active.ConfigPath);
                Assert.IsFalse(active.IsMachineConfig);
                Assert.IsFalse(active.IsReadOnly);
                Assert.IsTrue(File.Exists(expectedUserConfig));
            }
        }

        [TestMethod]
        public void GetActiveConfig_AllUsers_LockedMachineConfig_IsReadOnlyMachineConfig() {
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();

            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            File.WriteAllText(machineConfig, "[core]\r\n");
            File.SetAttributes(machineConfig, FileAttributes.ReadOnly);

            try {
                var active = PyRevitInstallScope.GetActiveConfig();
                Assert.AreEqual(machineConfig, active.ConfigPath);
                Assert.IsTrue(active.IsMachineConfig);
                Assert.IsTrue(active.IsReadOnly);
            }
            finally {
                File.SetAttributes(machineConfig, FileAttributes.Normal);
            }
        }

        [TestMethod]
        public void GetActiveConfig_AllUsers_UnwritableMachineConfig_NonElevated_FallsBackToSeededUserConfig() {
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("File sharing violations are only enforced on Windows.");
            AssertRequiresNonElevatedWindowsProcess();

            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();

            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            const string seedContent = "[core]\r\ncheckupdates = false\r\n";
            File.WriteAllText(machineConfig, seedContent);

            // holding a read-only share on the file denies the resolver's
            // open-for-write probe, mimicking an ACL-restricted installer config
            using (File.Open(machineConfig, FileMode.Open, FileAccess.Read, FileShare.Read)) {
                var active = PyRevitInstallScope.GetActiveConfig();

                string expectedUserConfig = Path.Combine(
                    PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
                Assert.AreEqual(expectedUserConfig, active.ConfigPath);
                Assert.IsFalse(active.IsMachineConfig);
                Assert.IsFalse(active.IsReadOnly);
                Assert.IsTrue(File.Exists(expectedUserConfig));
                Assert.AreEqual(seedContent, File.ReadAllText(expectedUserConfig));
            }
        }

        [TestMethod]
        public void GetActiveConfig_AllUsers_UnwritableMachineConfig_Elevated_UsesMachineConfig() {
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("File sharing violations are only enforced on Windows.");
            if (!UserEnv.IsRunAsElevated())
                Assert.Inconclusive("Test requires an elevated Windows process.");

            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();

            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            File.WriteAllText(machineConfig, "[core]\r\n");

            using (File.Open(machineConfig, FileMode.Open, FileAccess.Read, FileShare.Read)) {
                var active = PyRevitInstallScope.GetActiveConfig();

                Assert.AreEqual(machineConfig, active.ConfigPath);
                Assert.IsTrue(active.IsMachineConfig);
                Assert.IsTrue(active.IsReadOnly);
            }
        }

        [TestMethod]
        public void GetActiveConfig_PerUser_SeedsUserConfigFromMachineConfig() {
            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            const string seedContent = "[core]\r\nrocketmode = true\r\n";
            File.WriteAllText(machineConfig, seedContent);

            Assert.IsFalse(PyRevitInstallScope.IsAllUsersInstall());
            var active = PyRevitInstallScope.GetActiveConfig();

            string expectedUserConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Assert.AreEqual(expectedUserConfig, active.ConfigPath);
            Assert.IsFalse(active.IsMachineConfig);
            Assert.IsFalse(active.IsReadOnly);
            Assert.AreEqual(seedContent, File.ReadAllText(expectedUserConfig));
        }

        [TestMethod]
        public void GetActiveConfig_PerUser_LockedMachineConfig_IsReadOnlyMachineConfig() {
            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            File.WriteAllText(machineConfig, "[core]\r\n");
            File.SetAttributes(machineConfig, FileAttributes.ReadOnly);

            try {
                Assert.IsFalse(PyRevitInstallScope.IsAllUsersInstall());
                var active = PyRevitInstallScope.GetActiveConfig();
                Assert.AreEqual(machineConfig, active.ConfigPath);
                Assert.IsTrue(active.IsMachineConfig);
                Assert.IsTrue(active.IsReadOnly);
            }
            finally {
                File.SetAttributes(machineConfig, FileAttributes.Normal);
            }
        }

        [TestMethod]
        public void GetActiveConfig_PerUser_ExistingUserConfig_IsUsedDirectly() {
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);
            string userConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            File.WriteAllText(userConfig, "[core]\r\n");

            var active = PyRevitInstallScope.GetActiveConfig();
            Assert.AreEqual(userConfig, active.ConfigPath);
            Assert.IsFalse(active.IsMachineConfig);
            Assert.IsFalse(active.IsReadOnly);
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

        [TestMethod]
        public void GetExtensionRoots_AllUsers_WritableMachine_MergesPerUserExtensions() {
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();
            ExtensionParser.ClearAllCaches();

            string machineConfigPath = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            string userConfigPath = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);

            string machineExtDir = Path.Combine(_tempRoot, "MachineExt");
            string userExtDir = Path.Combine(_tempRoot, "UserExt");
            Directory.CreateDirectory(machineExtDir);
            Directory.CreateDirectory(userExtDir);

            try {
                new ExtensionParserConfig(machineConfigPath).UserExtensionsList = new List<string> { machineExtDir };
                new ExtensionParserConfig(userConfigPath).UserExtensionsList = new List<string> { userExtDir };

                var roots = ExtensionParser.GetExtensionRoots();

                CollectionAssert.Contains(roots, machineExtDir);
                CollectionAssert.Contains(roots, userExtDir);
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        [TestMethod]
        public void GetExtensionRoots_AllUsers_LockedMachine_SkipsPerUserExtensions() {
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();
            ExtensionParser.ClearAllCaches();

            string machineConfigPath = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            string userConfigPath = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);

            string machineExtDir = Path.Combine(_tempRoot, "MachineExt");
            string userExtDir = Path.Combine(_tempRoot, "UserExt");
            Directory.CreateDirectory(machineExtDir);
            Directory.CreateDirectory(userExtDir);

            try {
                new ExtensionParserConfig(machineConfigPath).UserExtensionsList = new List<string> { machineExtDir };
                new ExtensionParserConfig(userConfigPath).UserExtensionsList = new List<string> { userExtDir };
                File.SetAttributes(machineConfigPath, FileAttributes.ReadOnly);

                var roots = ExtensionParser.GetExtensionRoots();

                CollectionAssert.Contains(roots, machineExtDir);
                CollectionAssert.DoesNotContain(roots, userExtDir);
            }
            finally {
                if (File.Exists(machineConfigPath))
                    File.SetAttributes(machineConfigPath, FileAttributes.Normal);
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        [TestMethod]
        public void GetExtensionRoots_AllUsers_UnwritableMachineFallback_MergesMachineExtensions() {
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("File sharing violations are only enforced on Windows.");

            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();
            ExtensionParser.ClearAllCaches();

            string machineConfigPath = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            string userConfigPath = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);

            string machineExtDir = Path.Combine(_tempRoot, "MachineExt");
            string userExtDir = Path.Combine(_tempRoot, "UserExt");
            Directory.CreateDirectory(machineExtDir);
            Directory.CreateDirectory(userExtDir);

            try {
                new ExtensionParserConfig(machineConfigPath).UserExtensionsList = new List<string> { machineExtDir };
                File.WriteAllText(userConfigPath, "[core]\r\n");
                File.SetAttributes(userConfigPath, FileAttributes.Normal);

                using (File.Open(machineConfigPath, FileMode.Open, FileAccess.Read, FileShare.Read)) {
                    var roots = ExtensionParser.GetExtensionRoots();

                    CollectionAssert.Contains(roots, machineExtDir);
                }
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        [TestMethod]
        public void GetExtensionRoots_AllUsers_DedupesAcrossScopes() {
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();
            ExtensionParser.ClearAllCaches();

            string machineConfigPath = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            string userConfigPath = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);

            string sharedExtDir = Path.Combine(_tempRoot, "SharedExt");
            string machineOnlyExtDir = Path.Combine(_tempRoot, "MachineOnlyExt");
            Directory.CreateDirectory(sharedExtDir);
            Directory.CreateDirectory(machineOnlyExtDir);

            try {
                new ExtensionParserConfig(machineConfigPath).UserExtensionsList = new List<string> {
                    sharedExtDir, machineOnlyExtDir
                };
                new ExtensionParserConfig(userConfigPath).UserExtensionsList = new List<string> {
                    sharedExtDir.ToUpperInvariant(), sharedExtDir
                };

                var roots = ExtensionParser.GetExtensionRoots();

                int sharedOccurrences = roots.Count(r =>
                    string.Equals(r, sharedExtDir, StringComparison.OrdinalIgnoreCase));
                Assert.AreEqual(1, sharedOccurrences,
                    "shared path must be deduped across machine and per-user configs (case-insensitive)");
                CollectionAssert.Contains(roots, machineOnlyExtDir);
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        [TestMethod]
        public void GetExtensionRoots_AllUsers_FallbackWithoutMachineExtensions_ReturnsUserOnly() {
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("File sharing violations are only enforced on Windows.");

            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();
            ExtensionParser.ClearAllCaches();

            string machineConfigPath = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            string userConfigPath = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);

            string userExtDir = Path.Combine(_tempRoot, "UserOnlyExt");
            Directory.CreateDirectory(userExtDir);

            try {
                File.WriteAllText(machineConfigPath, "[core]\r\n");
                new ExtensionParserConfig(userConfigPath).UserExtensionsList = new List<string> { userExtDir };

                using (File.Open(machineConfigPath, FileMode.Open, FileAccess.Read, FileShare.Read)) {
                    var roots = ExtensionParser.GetExtensionRoots();

                    CollectionAssert.Contains(roots, userExtDir);
                }
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }
    }
}
