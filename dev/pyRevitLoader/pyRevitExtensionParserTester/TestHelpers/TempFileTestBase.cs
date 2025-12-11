using System;
using System.IO;
using NUnit.Framework;

namespace pyRevitExtensionParserTest.TestHelpers
{
    /// <summary>
    /// Base class for tests that need temporary file/directory management.
    /// Automatically creates a unique temp directory for each test and cleans it up afterward.
    /// </summary>
    public abstract class TempFileTestBase
    {
        /// <summary>
        /// Set to false to preserve test artifacts for inspection.
        /// </summary>
        protected static bool CleanupAfterTest = true;

        /// <summary>
        /// Gets the temporary directory path for the current test.
        /// This directory is created fresh for each test and deleted in TearDown.
        /// </summary>
        protected string TestTempDir { get; private set; }

        [SetUp]
        public virtual void BaseSetUp()
        {
            TestTempDir = Path.Combine(Path.GetTempPath(), $"pyRevitTest_{Guid.NewGuid():N}");
            Directory.CreateDirectory(TestTempDir);
        }

        [TearDown]
        public virtual void BaseTearDown()
        {
            if (CleanupAfterTest && !string.IsNullOrEmpty(TestTempDir) && Directory.Exists(TestTempDir))
            {
                try
                {
                    Directory.Delete(TestTempDir, recursive: true);
                }
                catch (IOException)
                {
                    // Best effort cleanup - some files may be locked
                    TestContext.Out.WriteLine($"Warning: Could not fully clean up temp directory: {TestTempDir}");
                }
            }
            else if (!CleanupAfterTest)
            {
                TestContext.Out.WriteLine($"Test artifacts preserved at: {TestTempDir}");
            }
        }

        /// <summary>
        /// Creates a subdirectory within the test temp directory.
        /// </summary>
        protected string CreateSubDirectory(string relativePath)
        {
            var fullPath = Path.Combine(TestTempDir, relativePath);
            Directory.CreateDirectory(fullPath);
            return fullPath;
        }

        /// <summary>
        /// Creates a file within the test temp directory with the specified content.
        /// </summary>
        protected string CreateFile(string relativePath, string content)
        {
            var fullPath = Path.Combine(TestTempDir, relativePath);
            var directory = Path.GetDirectoryName(fullPath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }
            File.WriteAllText(fullPath, content);
            return fullPath;
        }

        /// <summary>
        /// Creates a file within the test temp directory with the specified byte content.
        /// </summary>
        protected string CreateFile(string relativePath, byte[] content)
        {
            var fullPath = Path.Combine(TestTempDir, relativePath);
            var directory = Path.GetDirectoryName(fullPath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }
            File.WriteAllBytes(fullPath, content);
            return fullPath;
        }
    }
}
