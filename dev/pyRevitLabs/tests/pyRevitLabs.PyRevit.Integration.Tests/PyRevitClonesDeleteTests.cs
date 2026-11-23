using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using NUnit.Framework;

using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Sections;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Integration.Tests {
    /// <summary>
    /// Regression tests for #4219: deleting one clone must not delete the user config shared by every clone.
    /// </summary>
    [TestFixture]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Integration")]
    public class PyRevitClonesDeleteTests {
        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousProgramDataPathOverride;

        /// <summary>Redirects pyRevit data folders to a temporary root.</summary>
        [SetUp]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitClonesDelete_" + Guid.NewGuid().ToString("N"));
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
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
            PyRevitConfigService.Reload();
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);
        }

        /// <summary>Restores environment overrides and the install scope, then deletes the temporary root.</summary>
        [TearDown]
        public void Cleanup() {
            PyRevitConfigService.Reload();
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                _previousPyRevitPathOverride);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                _previousProgramDataPathOverride);
            if (Directory.Exists(_tempRoot))
                CommonUtils.DeleteDirectory(_tempRoot);
        }

        private string CreateClone(string name) {
            var clonePath = Path.Combine(_tempRoot, name);
            Directory.CreateDirectory(Path.Combine(clonePath, "pyrevitlib", "pyrevit"));
            return clonePath;
        }

        private void RegisterTwoClones(out string firstPath, out string secondPath) {
            firstPath = CreateClone("first");
            secondPath = CreateClone("second");
            var cfg = PyRevitConfigs.GetConfigFile();
            cfg.SaveSection(new EnvironmentSection {
                Clones = new Dictionary<string, string> {
                    { "first", firstPath },
                    { "second", secondPath },
                }
            });
            cfg.SaveSection(new CoreSection { UserLocale = "de_de" });
        }

        /// <summary>Deleting one clone removes it and its registration but keeps the config file and the other clone.</summary>
        [Test]
        public void Delete_SingleClone_KeepsConfigFileAndOtherClones() {
            RegisterTwoClones(out var firstPath, out var secondPath);
            var first = PyRevitClones.GetRegisteredClones().Single(c => c.Name == "first");

            PyRevitClones.Delete(first);

            Assert.That(Directory.Exists(firstPath), Is.False);
            Assert.That(Directory.Exists(secondPath), Is.True);
            Assert.That(File.Exists(PyRevitConsts.ConfigFilePath), Is.True);
            PyRevitConfigService.Reload();
            Assert.That(
                PyRevitClones.GetRegisteredClones().Select(c => c.Name).ToArray(),
                Is.EqualTo(new[] { "second" }));
            Assert.That(PyRevitConfigs.GetConfigFile().Core.UserLocale, Is.EqualTo("de_de"));
        }

        /// <summary>Deleting every clone without clearing configs keeps the config file.</summary>
        [Test]
        public void DeleteAllClones_WithoutClearConfigs_KeepsConfigFile() {
            RegisterTwoClones(out var firstPath, out var secondPath);

            PyRevitClones.DeleteAllClones();

            Assert.That(Directory.Exists(firstPath), Is.False);
            Assert.That(Directory.Exists(secondPath), Is.False);
            Assert.That(File.Exists(PyRevitConsts.ConfigFilePath), Is.True);
        }

        /// <summary>Deleting every clone with clearing configs also discards the user settings.</summary>
        [Test]
        public void DeleteAllClones_WithClearConfigs_DiscardsUserSettings() {
            RegisterTwoClones(out var firstPath, out var secondPath);

            PyRevitClones.DeleteAllClones(clearConfigs: true);

            Assert.That(Directory.Exists(firstPath), Is.False);
            Assert.That(Directory.Exists(secondPath), Is.False);
            PyRevitConfigService.Reload();
            Assert.That(PyRevitConfigs.GetConfigFile().Core.UserLocale, Is.Null);
            Assert.That(PyRevitClones.GetRegisteredClones(), Is.Empty);
        }
    }
}
