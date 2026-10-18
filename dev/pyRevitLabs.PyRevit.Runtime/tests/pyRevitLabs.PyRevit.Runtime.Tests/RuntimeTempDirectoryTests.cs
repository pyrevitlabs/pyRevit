using System;
using System.IO;

namespace pyRevitLabs.PyRevit.Runtime.Tests {
    /// <summary>Owns temporary scripts without loading parser or user configuration.</summary>
    public abstract class RuntimeTempDirectoryTests {
        private string _directory = null!;

        /// <summary>Creates a private script directory for each case.</summary>
        [SetUp]
        public void CreateTemporaryDirectory() {
            _directory = Path.Combine(Path.GetTempPath(), "pyrevit-runtime-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_directory);
        }

        /// <summary>Removes scripts after runtime fixture cleanup.</summary>
        [TearDown]
        public void RemoveTemporaryDirectory() => Directory.Delete(_directory, true);

        protected string CreateFile(string relativePath, string contents) {
            var path = Path.Combine(_directory, relativePath);
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllText(path, contents);
            return path;
        }
    }
}
