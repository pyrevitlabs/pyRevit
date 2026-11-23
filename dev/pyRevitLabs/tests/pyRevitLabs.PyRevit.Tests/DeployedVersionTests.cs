using System;
using System.IO;
using System.Reflection;

using NUnit.Framework;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Tests {
    /// <summary>Covers how a clone's deployed version is read: from the built assembly for the requested framework, falling back to the trimmed version file.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    public class DeployedVersionTests {
        private const string VersionFileContent = "9.9.9.99999+9999";
        private const string BuiltAssemblyName = "pyRevitLabs.PyRevit.dll";

        private string _clonePath = null!;

        /// <summary>
        /// A clone is valid to PyRevitClone as long as pyrevitlib/pyrevit exists, so the
        /// fixture is only the version file plus whichever framework trees the test needs.
        /// </summary>
        [SetUp]
        public void CreateClone() {
            _clonePath = Path.Combine(
                Path.GetTempPath(), "pyRevitDeployedVersion_" + Guid.NewGuid().ToString("N"));

            var moduleDir = Path.Combine(_clonePath, "pyrevitlib", "pyrevit");
            Directory.CreateDirectory(moduleDir);
            File.WriteAllText(Path.Combine(moduleDir, "version"), VersionFileContent);
        }

        /// <summary>Deletes the temporary clone.</summary>
        [TearDown]
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

        /// <summary>A clone with no built binaries reports the version file content.</summary>
        [Test]
        public void UnbuiltCloneReportsTheVersionFile() {
            Assert.That(PyRevitClone.GetDeployedVersion(_clonePath, null), Is.EqualTo(VersionFileContent));
        }

        /// <summary>A built clone reports the built assembly's version instead of the version file.</summary>
        [Test]
        public void BuiltCloneReportsTheAssemblyOverTheVersionFile() {
            StageBuiltAssembly(PyRevitConsts.NetFxFolder);

            Assert.That(PyRevitClone.GetDeployedVersion(_clonePath, null), Is.Not.EqualTo(VersionFileContent));
            Assert.That(PyRevitClone.GetDeployedVersion(_clonePath, null), Is.EqualTo(BuiltAssemblyVersion));
        }

        /// <summary>Requesting .NET Framework reads the version from the netfx binaries tree.</summary>
        [Test]
        public void RequestedFrameworkSelectsTheTreeToRead() {
            StageBuiltAssembly(PyRevitConsts.NetFxFolder);

            Assert.That(PyRevitClone.GetDeployedVersion(_clonePath, isNetCore: false), Is.EqualTo(BuiltAssemblyVersion), "A netfx host must read the netfx tree, which is the only one built here.");
        }

        /// <summary>Requesting a framework tree the clone lacks falls back to the version file rather than reading the other tree.</summary>
        [Test]
        public void MissingRequestedFrameworkFallsBackToTheVersionFile() {
            StageBuiltAssembly(PyRevitConsts.NetFxFolder);

            Assert.That(PyRevitClone.GetDeployedVersion(_clonePath, isNetCore: true), Is.EqualTo(VersionFileContent), "Asking for a tree the clone does not have must not read the other one.");
        }

        /// <summary>The version file fallback is returned without trailing whitespace.</summary>
        [Test]
        public void VersionFileFallbackIsTrimmed() {
            File.WriteAllText(
                Path.Combine(_clonePath, "pyrevitlib", "pyrevit", "version"),
                VersionFileContent + "\n");

            Assert.That(PyRevitClone.GetDeployedVersion(_clonePath, null), Is.EqualTo(VersionFileContent));
        }
    }
}
