using System;
using System.IO;
using System.Linq;

using NUnit.Framework;

using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.PyRevit;
using pyRevitExtensionParser;

namespace pyRevitLabs.PyRevit.Integration.Tests {
    /// <summary>Covers which config file per-user and all-users installs use, across elevation and missing, unreadable, locked or unwritable machine configs.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Integration")]
    public class PyRevitInstallScopeTests {
        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousProgramDataPathOverride;
        private string _previousConfigScopeOverride;
        private Func<bool> _previousElevationDetector;

        /// <summary>Redirects the user and machine config folders to a temporary root and forces a non-elevated process.</summary>
        [SetUp]
        public void Setup() {
            _previousElevationDetector = PyRevitInstallScope.ElevatedProcessDetector;
            PyRevitInstallScope.ElevatedProcessDetector = () => false;
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
            PyRevitConfigService.Reload();
        }

        private static void SetUserExtensions(string configPath, params string[] extensionPaths) {
            string encodedPaths = string.Join(
                ",",
                extensionPaths.Select(path => "\"" + path.Replace("\\", "\\\\") + "\""));
            File.WriteAllText(configPath, "[core]\r\nuserextensions = [" + encodedPaths + "]\r\n");
        }

        /// <summary>Restores the elevation detector, environment overrides and install scope, then deletes the temporary root.</summary>
        [TearDown]
        public void Cleanup() {
            PyRevitInstallScope.ElevatedProcessDetector = _previousElevationDetector;
            PyRevitConfigService.Reload();
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
            FixtureDirectory.Delete(_tempRoot);
        }

        /// <summary>Without any all-users signal the install is per-user and configs live under the AppData folder.</summary>
        [Test]
        public void GetConfigDirectory_WithoutMachineScope_UsesAppDataPath() {
            Assert.That(PyRevitInstallScope.IsAllUsersInstall(), Is.False);
            Assert.That(PyRevitInstallScope.GetConfigDirectory(), Is.EqualTo(PyRevitLabsConsts.PyRevitPath));
        }

        /// <summary>The legacy all-users marker file makes the install all-users and moves configs to ProgramData.</summary>
        [Test]
        public void GetConfigDirectory_WithLegacyMarker_UsesProgramDataPath() {
            string programDataPyRevit = PyRevitLabsConsts.PyRevitProgramDataPath;
            Directory.CreateDirectory(programDataPyRevit);
            string markerPath = Path.Combine(programDataPyRevit, PyRevitLabsConsts.InstallAllUsersMarkerFileName);
            bool createdMarker = false;
            try {
                File.WriteAllText(markerPath, "AllUsers");
                createdMarker = true;
                PyRevitInstallScope.ClearCachedInstallScope();
                Assert.That(PyRevitInstallScope.IsAllUsersInstall(), Is.True);
                Assert.That(PyRevitInstallScope.GetConfigDirectory(), Is.EqualTo(PyRevitLabsConsts.PyRevitProgramDataPath));
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                if (createdMarker && File.Exists(markerPath))
                    File.Delete(markerPath);
            }
        }

        /// <summary>The config scope environment override makes the install all-users and moves configs to ProgramData.</summary>
        [Test]
        public void GetConfigDirectory_WithScopeOverride_UsesProgramDataPath() {
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();
            Assert.That(PyRevitInstallScope.IsAllUsersInstall(), Is.True);
            Assert.That(PyRevitInstallScope.GetConfigDirectory(), Is.EqualTo(PyRevitLabsConsts.PyRevitProgramDataPath));
        }

        /// <summary>A runtime install root under Program Files is detected as an all-users install.</summary>
        [Test]
        public void IsAllUsersInstall_DetectsProgramFilesInstallRoot() {
            var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            if (string.IsNullOrWhiteSpace(programFiles))
                Assert.Inconclusive("Program Files folder is not available on this machine.");

            try {
                PyRevitInstallScope.SetRuntimeInstallRoot(Path.Combine(programFiles, "pyRevit-Master"));
                PyRevitInstallScope.ClearCachedInstallScope();
                Assert.That(PyRevitInstallScope.IsAllUsersInstall(), Is.True);
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
            Assert.That(PyRevitInstallScope.IsElevatedProcess(), Is.False);
        }

        /// <summary>A non-elevated all-users session uses a writable user config seeded from the machine config.</summary>
        [Test]
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
            Assert.That(active.ConfigPath, Is.EqualTo(expectedUserConfig));
            Assert.That(active.IsMachineConfig, Is.False);
            Assert.That(active.IsReadOnly, Is.False);
            Assert.That(File.Exists(expectedUserConfig), Is.True);
            Assert.That(File.ReadAllText(expectedUserConfig), Is.EqualTo(seedContent));
        }

        /// <summary>An elevated all-users session uses the writable machine config directly.</summary>
        [Test]
        public void GetActiveConfig_AllUsers_WritableMachineConfig_Elevated_UsesMachineConfig() {
            PyRevitInstallScope.ElevatedProcessDetector = () => true;
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("Elevation detection is only available on Windows.");
            Assert.That(PyRevitInstallScope.IsElevatedProcess(), Is.True);

            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();

            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            File.WriteAllText(machineConfig, "[core]\r\n");

            var active = PyRevitInstallScope.GetActiveConfig();
            Assert.That(active.ConfigPath, Is.EqualTo(machineConfig));
            Assert.That(active.IsMachineConfig, Is.True);
            Assert.That(active.IsReadOnly, Is.False);
        }

        /// <summary>A non-elevated all-users session with no machine config creates a user config and no machine config.</summary>
        [Test]
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
            Assert.That(active.ConfigPath, Is.EqualTo(expectedUserConfig));
            Assert.That(active.IsMachineConfig, Is.False);
            Assert.That(active.IsReadOnly, Is.False);
            Assert.That(File.Exists(expectedUserConfig), Is.True);
            Assert.That(File.Exists(expectedMachineConfig), Is.False);
        }

        /// <summary>An elevated all-users session with no machine config creates and uses a writable machine config.</summary>
        [Test]
        public void GetActiveConfig_AllUsers_MissingMachineConfig_Elevated_CreatesMachineConfig() {
            PyRevitInstallScope.ElevatedProcessDetector = () => true;
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("Elevation detection is only available on Windows.");
            Assert.That(PyRevitInstallScope.IsElevatedProcess(), Is.True);

            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                PyRevitInstallScope.ConfigScopeAllUsers);
            PyRevitInstallScope.ClearCachedInstallScope();

            var active = PyRevitInstallScope.GetActiveConfig();
            string expected = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Assert.That(active.ConfigPath, Is.EqualTo(expected));
            Assert.That(active.IsMachineConfig, Is.True);
            Assert.That(active.IsReadOnly, Is.False);
            Assert.That(File.Exists(expected), Is.True);
        }

        /// <summary>A machine config held open exclusively does not stop a non-elevated session from creating a writable user config.</summary>
        [Test]
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
                Assert.That(active.ConfigPath, Is.EqualTo(expectedUserConfig));
                Assert.That(active.IsMachineConfig, Is.False);
                Assert.That(active.IsReadOnly, Is.False);
                Assert.That(File.Exists(expectedUserConfig), Is.True);
            }
        }

        /// <summary>A read-only machine config in an all-users install is used as the active config and reported read-only.</summary>
        [Test]
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
                Assert.That(active.ConfigPath, Is.EqualTo(machineConfig));
                Assert.That(active.IsMachineConfig, Is.True);
                Assert.That(active.IsReadOnly, Is.True);
            }
            finally {
                File.SetAttributes(machineConfig, FileAttributes.Normal);
            }
        }

        /// <summary>A non-elevated session that cannot write the machine config falls back to a writable user config seeded from it.</summary>
        [Test]
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
                Assert.That(active.ConfigPath, Is.EqualTo(expectedUserConfig));
                Assert.That(active.IsMachineConfig, Is.False);
                Assert.That(active.IsReadOnly, Is.False);
                Assert.That(File.Exists(expectedUserConfig), Is.True);
                Assert.That(File.ReadAllText(expectedUserConfig), Is.EqualTo(seedContent));
            }
        }

        /// <summary>An elevated session that cannot write the machine config still uses it, reported read-only.</summary>
        [Test]
        public void GetActiveConfig_AllUsers_UnwritableMachineConfig_Elevated_UsesMachineConfig() {
            PyRevitInstallScope.ElevatedProcessDetector = () => true;
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("File sharing violations are only enforced on Windows.");
            Assert.That(PyRevitInstallScope.IsElevatedProcess(), Is.True);

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

                Assert.That(active.ConfigPath, Is.EqualTo(machineConfig));
                Assert.That(active.IsMachineConfig, Is.True);
                Assert.That(active.IsReadOnly, Is.True);
            }
        }

        /// <summary>A per-user install with no user config seeds a writable user config from the machine config.</summary>
        [Test]
        public void GetActiveConfig_PerUser_SeedsUserConfigFromMachineConfig() {
            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            const string seedContent = "[core]\r\nrocketmode = true\r\n";
            File.WriteAllText(machineConfig, seedContent);

            Assert.That(PyRevitInstallScope.IsAllUsersInstall(), Is.False);
            var active = PyRevitInstallScope.GetActiveConfig();

            string expectedUserConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Assert.That(active.ConfigPath, Is.EqualTo(expectedUserConfig));
            Assert.That(active.IsMachineConfig, Is.False);
            Assert.That(active.IsReadOnly, Is.False);
            Assert.That(File.ReadAllText(expectedUserConfig), Is.EqualTo(seedContent));
        }

        /// <summary>A read-only machine config takes precedence in a per-user install and is reported read-only.</summary>
        [Test]
        public void GetActiveConfig_PerUser_LockedMachineConfig_IsReadOnlyMachineConfig() {
            string machineConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath, PyRevitLabsConsts.DefaultConfigsFileName);
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            File.WriteAllText(machineConfig, "[core]\r\n");
            File.SetAttributes(machineConfig, FileAttributes.ReadOnly);

            try {
                Assert.That(PyRevitInstallScope.IsAllUsersInstall(), Is.False);
                var active = PyRevitInstallScope.GetActiveConfig();
                Assert.That(active.ConfigPath, Is.EqualTo(machineConfig));
                Assert.That(active.IsMachineConfig, Is.True);
                Assert.That(active.IsReadOnly, Is.True);
            }
            finally {
                File.SetAttributes(machineConfig, FileAttributes.Normal);
            }
        }

        /// <summary>A per-user install with an existing user config uses it as a writable user config.</summary>
        [Test]
        public void GetActiveConfig_PerUser_ExistingUserConfig_IsUsedDirectly() {
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);
            string userConfig = Path.Combine(
                PyRevitLabsConsts.PyRevitPath, PyRevitLabsConsts.DefaultConfigsFileName);
            File.WriteAllText(userConfig, "[core]\r\n");

            var active = PyRevitInstallScope.GetActiveConfig();
            Assert.That(active.ConfigPath, Is.EqualTo(userConfig));
            Assert.That(active.IsMachineConfig, Is.False);
            Assert.That(active.IsReadOnly, Is.False);
        }

        /// <summary>Loading the config in an elevated all-users install merges the user config's clones and extension sections into the machine config.</summary>
        [Test]
        public void MigrateSplitAdminConfig_MergesClonesAndExtensionSections() {
            PyRevitInstallScope.ElevatedProcessDetector = () => true;

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
                PyRevitConfigService.Reload();
                PyRevitConfigs.GetConfigFile();

                string merged = File.ReadAllText(programDataConfig);
                Assert.That(merged, Does.Contain("clones"));
                Assert.That(merged, Does.Contain("TestClone"));
                Assert.That(merged, Does.Contain("pyRevitTags.extension"));
                Assert.That(merged, Does.Contain("pyRevitTemplates.extension"));
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                if (File.Exists(appDataConfig))
                    File.Delete(appDataConfig);
                if (File.Exists(programDataConfig))
                    File.Delete(programDataConfig);
            }
        }

        /// <summary>Seeding shipped defaults writes a disabled entry for an extension whose <c>default_enabled</c> is false.</summary>
        [Test]
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
                Assert.That(probe.Definition, Is.Not.Null, "extension.json should parse");
                Assert.That(probe.Definition.DefaultEnabled, Is.False, "default_enabled should be false");
                PyRevitInstallScope.ClearCachedInstallScope();
                PyRevitConfigs.SeedShippedExtensionDefaults(cloneRoot);

                string seeded = File.ReadAllText(configPath);
                Assert.That(seeded, Does.Contain("OptOutExt.extension"));
                Assert.That(seeded, Does.Contain("disabled"));
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                if (File.Exists(configPath))
                    File.Delete(configPath);
            }
        }

        /// <summary>A standard user's extension roots come from the user config, so a machine path the user already removed does not return.</summary>
        [Test]
        public void GetExtensionRoots_AllUsers_StandardUser_ReadsOnlyTheActiveConfig() {
            AssertRequiresNonElevatedWindowsProcess();

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
                SetUserExtensions(machineConfigPath, machineExtDir);
                File.WriteAllText(
                    userConfigPath,
                    "[core]\r\nuserextensions = [\"" + userExtDir.Replace("\\", "\\\\") + "\"]\r\n"
                    + "syncedmachineuserextensions = [\"" + machineExtDir.Replace("\\", "\\\\") + "\"]\r\n");

                var roots = ExtensionParser.GetExtensionRoots();

                Assert.That(roots, Does.Contain(userExtDir));
                Assert.That(roots, Does.Not.Contain(machineExtDir),
                    "a machine path the user already removed must not come back from the machine config");
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        /// <summary>With a read-only machine config only the machine extension paths load and per-user paths are ignored.</summary>
        [Test]
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
                SetUserExtensions(machineConfigPath, machineExtDir);
                SetUserExtensions(userConfigPath, userExtDir);
                File.SetAttributes(machineConfigPath, FileAttributes.ReadOnly);

                var roots = ExtensionParser.GetExtensionRoots();

                Assert.That(roots, Does.Contain(machineExtDir));
                Assert.That(roots, Does.Not.Contain(userExtDir));
            }
            finally {
                if (File.Exists(machineConfigPath))
                    File.SetAttributes(machineConfigPath, FileAttributes.Normal);
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        /// <summary>When an unwritable machine config forces the user-config fallback, its extension paths are still loaded.</summary>
        [Test]
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
                SetUserExtensions(machineConfigPath, machineExtDir);
                File.WriteAllText(userConfigPath, "[core]\r\n");
                File.SetAttributes(userConfigPath, FileAttributes.Normal);

                using (File.Open(machineConfigPath, FileMode.Open, FileAccess.Read, FileShare.Read)) {
                    var roots = ExtensionParser.GetExtensionRoots();

                    Assert.That(roots, Does.Contain(machineExtDir));
                }
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        /// <summary>An extension path listed in both machine and user configs appears once, compared case-insensitively.</summary>
        [Test]
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
                SetUserExtensions(machineConfigPath, sharedExtDir, machineOnlyExtDir);
                SetUserExtensions(userConfigPath, sharedExtDir.ToUpperInvariant(), sharedExtDir);

                var roots = ExtensionParser.GetExtensionRoots();

                int sharedOccurrences = roots.Count(r =>
                    string.Equals(r, sharedExtDir, StringComparison.OrdinalIgnoreCase));
                Assert.That(sharedOccurrences, Is.EqualTo(1), "shared path must be deduped across machine and per-user configs (case-insensitive)");
                Assert.That(roots, Does.Contain(machineOnlyExtDir));
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        /// <summary>A per-user install loads only the user config's extension paths, not the machine config's.</summary>
        [Test]
        public void GetExtensionRoots_PerUser_IgnoresMachineExtensions() {
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
                SetUserExtensions(machineConfigPath, machineExtDir);
                SetUserExtensions(userConfigPath, userExtDir);
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();

                var roots = ExtensionParser.GetExtensionRoots();

                Assert.That(roots, Does.Contain(userExtDir));
                Assert.That(roots, Does.Not.Contain(machineExtDir));
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        /// <summary>A new machine extension path is loaded for a standard user and written into the user config.</summary>
        [Test]
        public void GetExtensionRoots_AllUsers_StandardUser_PicksUpNewMachinePaths() {
            AssertRequiresNonElevatedWindowsProcess();

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
                SetUserExtensions(machineConfigPath, machineExtDir);
                SetUserExtensions(userConfigPath, userExtDir);

                var roots = ExtensionParser.GetExtensionRoots();

                Assert.That(roots, Does.Contain(userExtDir));
                Assert.That(roots, Does.Contain(machineExtDir));
                Assert.That(File.ReadAllText(userConfigPath), Does.Contain("MachineExt"),
                    "the machine path must land in the per-user config so Settings can show and remove it");
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        /// <summary>New machine extension paths still load for the session when the user config cannot be saved.</summary>
        [Test]
        public void GetExtensionRoots_AllUsers_WriteBlockedUserConfig_StillLoadsNewMachinePaths() {
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("File sharing violations are only enforced on Windows.");
            AssertRequiresNonElevatedWindowsProcess();

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
                SetUserExtensions(machineConfigPath, machineExtDir);
                SetUserExtensions(userConfigPath, userExtDir);

                using (File.Open(machineConfigPath, FileMode.Open, FileAccess.Read, FileShare.Read))
                using (File.Open(userConfigPath, FileMode.Open, FileAccess.Read, FileShare.Read)) {
                    var roots = ExtensionParser.GetExtensionRoots();

                    Assert.That(roots, Does.Contain(userExtDir));
                    Assert.That(roots, Does.Contain(machineExtDir),
                        "a sync that cannot be saved must still apply for the session");
                }
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }

        /// <summary>The user-config fallback with no machine extension paths still returns the user's extension paths.</summary>
        [Test]
        public void GetExtensionRoots_AllUsers_FallbackWithoutMachineExtensions_ReturnsUserOnly() {
            if (!System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                    System.Runtime.InteropServices.OSPlatform.Windows))
                Assert.Inconclusive("File sharing violations are only enforced on Windows.");
            AssertRequiresNonElevatedWindowsProcess();

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
                SetUserExtensions(userConfigPath, userExtDir);

                using (File.Open(machineConfigPath, FileMode.Open, FileAccess.Read, FileShare.Read)) {
                    var roots = ExtensionParser.GetExtensionRoots();

                    Assert.That(roots, Does.Contain(userExtDir));
                }
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                ExtensionParser.ClearAllCaches();
            }
        }
    }
}
