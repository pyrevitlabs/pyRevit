using System;
using System.IO;

using NUnit.Framework;

using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    /// <summary>Covers environment-variable expansion and the user temp directory, including the fallback when %TEMP% does not expand.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Unit")]
    public class CommonUtilsPathTests {
        private string _tempRoot = null!;
        private string? _previousTemp;
        private string? _previousLocalAppData;

        /// <summary>Creates a temporary root and records the current TEMP and LOCALAPPDATA values.</summary>
        [SetUp]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitPathTests_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            _previousTemp = Environment.GetEnvironmentVariable("TEMP");
            _previousLocalAppData = Environment.GetEnvironmentVariable("LOCALAPPDATA");
        }

        /// <summary>Restores TEMP and LOCALAPPDATA and deletes the temporary root.</summary>
        [TearDown]
        public void Cleanup() {
            Environment.SetEnvironmentVariable("TEMP", _previousTemp);
            Environment.SetEnvironmentVariable("LOCALAPPDATA", _previousLocalAppData);
            if (Directory.Exists(_tempRoot))
                Directory.Delete(_tempRoot, recursive: true);
        }

        /// <summary>Environment variables inside a path are expanded to their current values.</summary>
        [Test]
        public void ExpandEnvironmentPath_ExpandsNestedVariables() {
            Environment.SetEnvironmentVariable("LOCALAPPDATA", _tempRoot);
            var expanded = CommonUtils.ExpandEnvironmentPath("%LOCALAPPDATA%\\pyRevit");
            Assert.That(expanded, Is.EqualTo(Path.Combine(_tempRoot, "pyRevit")));
        }

        /// <summary>A TEMP value that refers to another variable is fully expanded, with no <c>%</c> left in the result.</summary>
        [Test]
        public void GetUserTempDirectory_ExpandsPercentTemp() {
            Environment.SetEnvironmentVariable("LOCALAPPDATA", _tempRoot);
            Environment.SetEnvironmentVariable("TEMP", "%LOCALAPPDATA%\\Temp");
            var tempDir = CommonUtils.GetUserTempDirectory();
            Assert.That(tempDir.Contains("%"), Is.False, "Temp path should not contain unexpanded variables.");
            Assert.That(tempDir, Does.StartWith(_tempRoot));
            Assert.That(tempDir.EndsWith("Temp", StringComparison.OrdinalIgnoreCase), Is.True);
        }

        /// <summary>A TEMP value that cannot be expanded falls back to <c>Path.GetTempPath()</c> without its trailing separator.</summary>
        [Test]
        public void GetUserTempDirectory_FallsBackToPathGetTempPathWhenUnexpanded() {
            Environment.SetEnvironmentVariable("TEMP", "%NONEXISTENT_PYREVIT_VAR%\\Temp");
            var tempDir = CommonUtils.GetUserTempDirectory();
            Assert.That(tempDir.Contains("%"), Is.False);
            var expected = Path.GetTempPath().TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            Assert.That(tempDir, Is.EqualTo(expected));
        }

        /// <summary><c>UserEnv.UserTemp</c> returns the same directory as <c>CommonUtils.GetUserTempDirectory</c>.</summary>
        [Test]
        public void UserTemp_MatchesGetUserTempDirectory() {
            Environment.SetEnvironmentVariable("LOCALAPPDATA", _tempRoot);
            Environment.SetEnvironmentVariable("TEMP", "%LOCALAPPDATA%\\Temp");
            Assert.That(UserEnv.UserTemp, Is.EqualTo(CommonUtils.GetUserTempDirectory()));
        }

    }
}
