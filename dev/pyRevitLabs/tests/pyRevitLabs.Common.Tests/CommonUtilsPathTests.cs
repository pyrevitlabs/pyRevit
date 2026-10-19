using System;
using System.IO;

using Microsoft.VisualStudio.TestTools.UnitTesting;
using Assert = Microsoft.VisualStudio.TestTools.UnitTesting.Assert;
using CollectionAssert = Microsoft.VisualStudio.TestTools.UnitTesting.CollectionAssert;
using StringAssert = Microsoft.VisualStudio.TestTools.UnitTesting.StringAssert;

using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    [TestClass]
    [DoNotParallelize]
    [TestCategory("HostFree")]
    [TestCategory("Integration")]
    public class CommonUtilsPathTests {
        private string _tempRoot = null!;
        private string? _previousTemp;
        private string? _previousLocalAppData;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitPathTests_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            _previousTemp = Environment.GetEnvironmentVariable("TEMP");
            _previousLocalAppData = Environment.GetEnvironmentVariable("LOCALAPPDATA");
        }

        [TestCleanup]
        public void Cleanup() {
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
        public void GetUserTempDirectory_FallsBackToPathGetTempPathWhenUnexpanded() {
            Environment.SetEnvironmentVariable("TEMP", "%NONEXISTENT_PYREVIT_VAR%\\Temp");
            var tempDir = CommonUtils.GetUserTempDirectory();
            Assert.IsFalse(tempDir.Contains("%"));
            var expected = Path.GetTempPath().TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            Assert.AreEqual(expected, tempDir);
        }

        [TestMethod]
        public void UserTemp_MatchesGetUserTempDirectory() {
            Environment.SetEnvironmentVariable("LOCALAPPDATA", _tempRoot);
            Environment.SetEnvironmentVariable("TEMP", "%LOCALAPPDATA%\\Temp");
            Assert.AreEqual(CommonUtils.GetUserTempDirectory(), UserEnv.UserTemp);
        }

    }
}
