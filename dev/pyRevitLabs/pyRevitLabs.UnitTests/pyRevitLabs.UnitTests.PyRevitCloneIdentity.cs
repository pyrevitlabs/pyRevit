using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Sections;
using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    /// <summary>
    /// Regression tests for #4041: clone identity comparisons and the reporting of rejected registered clones.
    /// </summary>
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
    public class PyRevitCloneIdentityTests {
        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousProgramDataPathOverride;
        private LoggingConfiguration _previousLogConfiguration;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitCloneIdentity_" + Guid.NewGuid().ToString("N"));
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
            _previousLogConfiguration = LogManager.Configuration;
        }

        [TestCleanup]
        public void Cleanup() {
            LogManager.Configuration = _previousLogConfiguration;
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

        [TestMethod]
        public void Equals_NullAndForeignTypes_AreNotEqual() {
            var clone = new PyRevitClone(CreateClone("a"), name: "a");

            Assert.IsFalse(clone.Equals(null));
            Assert.IsFalse(clone.Equals("not a clone"));
        }

        [TestMethod]
        public void Equals_PathsDifferingOnlyInCase_AreEqualAndHashAlike() {
            var path = CreateClone("CaseClone");
            var first = new PyRevitClone(path, name: "first");
            var second = new PyRevitClone(path.ToUpperInvariant(), name: "second");

            Assert.IsTrue(first.Equals(second));
            Assert.AreEqual(first.GetHashCode(), second.GetHashCode());
        }

        [TestMethod]
        public void Matches_PathDifferingOnlyInCase_Matches() {
            var path = CreateClone("MatchClone");
            var clone = new PyRevitClone(path, name: "named");

            Assert.IsTrue(clone.Matches(path.ToUpperInvariant()));
            Assert.IsFalse(clone.Matches(path + "2"));
        }

        [TestMethod]
        public void GetRegisteredClones_RejectedClone_IsWarnedWithPathAndReasonAndStaysRegistered() {
            var rejectedPath = Path.Combine(_tempRoot, "rejected");
            Directory.CreateDirectory(rejectedPath);
            var validPath = CreateClone("valid");
            var cfg = PyRevitConfigs.GetConfigFile();
            cfg.SaveSection(new EnvironmentSection {
                Clones = new Dictionary<string, string> {
                    { "rejected", rejectedPath },
                    { "valid", validPath },
                }
            });
            var target = new MemoryTarget("memory") { Layout = "${level}|${message}" };
            var logConfiguration = new LoggingConfiguration();
            logConfiguration.AddRule(LogLevel.Warn, LogLevel.Fatal, target);
            LogManager.Configuration = logConfiguration;

            var clones = PyRevitClones.GetRegisteredClones();

            CollectionAssert.AreEqual(new[] { "valid" }, clones.Select(c => c.Name).ToArray());
            var warning = target.Logs.Single(line => line.StartsWith("Warn|"));
            StringAssert.Contains(warning, rejectedPath);
            StringAssert.Contains(warning, "not a valid");
            Assert.IsTrue(PyRevitConfigs.GetConfigFile().Environment.Clones.ContainsKey("rejected"));
        }

        [TestMethod]
        public void GetRegisteredClones_SameRejectedCloneRepeatedly_IsWarnedOnce() {
            var rejectedPath = Path.Combine(_tempRoot, "rejected-repeat");
            Directory.CreateDirectory(rejectedPath);
            var cfg = PyRevitConfigs.GetConfigFile();
            cfg.SaveSection(new EnvironmentSection {
                Clones = new Dictionary<string, string> { { "rejected-repeat", rejectedPath } }
            });
            var target = new MemoryTarget("memory") { Layout = "${level}|${message}" };
            var logConfiguration = new LoggingConfiguration();
            logConfiguration.AddRule(LogLevel.Warn, LogLevel.Fatal, target);
            LogManager.Configuration = logConfiguration;

            PyRevitClones.GetRegisteredClones();
            PyRevitClones.GetRegisteredClones();
            PyRevitClones.GetRegisteredClones();

            Assert.AreEqual(1, target.Logs.Count(line => line.StartsWith("Warn|")));
        }

        private MemoryTarget CaptureLogs(LogLevel minLevel) {
            var target = new MemoryTarget("memory") { Layout = "${level}|${message}" };
            var logConfiguration = new LoggingConfiguration();
            logConfiguration.AddRule(minLevel, LogLevel.Fatal, target);
            LogManager.Configuration = logConfiguration;
            return target;
        }

        private void RegisterClones(Dictionary<string, string> clones) {
            PyRevitConfigs.GetConfigFile().SaveSection(new EnvironmentSection { Clones = clones });
        }

        [TestMethod]
        public void GetRegisteredClones_RegisteredSubfolderOfValidClone_IsAcceptedWithoutWarning() {
            var parentPath = CreateClone("parent");
            var subfolder = Path.Combine(parentPath, "extensions");
            Directory.CreateDirectory(subfolder);
            RegisterClones(new Dictionary<string, string> { { "sub", subfolder } });
            var target = CaptureLogs(LogLevel.Warn);

            var clones = PyRevitClones.GetRegisteredClones();

            Assert.AreEqual(1, clones.Count);
            Assert.IsTrue(clones[0].ClonePath.IsSamePathAs(parentPath));
            Assert.AreEqual(0, target.Logs.Count);
        }

        [TestMethod]
        public void GetRegisteredClones_CloneRepairedThenBrokenAgain_IsWarnedAgain() {
            var path = Path.Combine(_tempRoot, "flaky");
            Directory.CreateDirectory(path);
            RegisterClones(new Dictionary<string, string> { { "flaky", path } });
            var target = CaptureLogs(LogLevel.Warn);

            PyRevitClones.GetRegisteredClones();
            Directory.CreateDirectory(Path.Combine(path, "pyrevitlib", "pyrevit"));
            Assert.AreEqual(1, PyRevitClones.GetRegisteredClones().Count);
            Directory.Delete(Path.Combine(path, "pyrevitlib"), true);
            PyRevitClones.GetRegisteredClones();

            Assert.AreEqual(2, target.Logs.Count(line => line.StartsWith("Warn|")));
        }

        [TestMethod]
        public void GetRegisteredClones_DuplicateDifferingInCase_IsKeptOnceAndLoggedWhenPruned() {
            var path = CreateClone("dup");
            var missing = Path.Combine(_tempRoot, "missing");
            RegisterClones(new Dictionary<string, string> {
                { "first", path },
                { "alias", path.ToUpperInvariant() },
                { "gone", missing },
            });
            var target = CaptureLogs(LogLevel.Info);

            var clones = PyRevitClones.GetRegisteredClones();

            CollectionAssert.AreEqual(new[] { "first" }, clones.Select(c => c.Name).ToArray());
            var info = target.Logs.Single(line => line.StartsWith("Info|"));
            StringAssert.Contains(info, "alias");
            StringAssert.Contains(info, "first");
        }
    }
}
