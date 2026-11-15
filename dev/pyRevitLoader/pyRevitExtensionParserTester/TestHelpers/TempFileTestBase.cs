using System;
using System.IO;
using NUnit.Framework;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini.Extensions;

namespace pyRevitExtensionParserTest.TestHelpers
{
    /// <summary>
    /// Isolates parser fixtures from user configuration and owns their temporary files.
    /// DevTools is enabled explicitly so smoke fixtures work on a clean machine.
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
            var configPath = Path.Combine(TestTempDir, "pyRevit_config.ini");
            PyRevitConfigStore.Reset();
            File.WriteAllText(configPath, "[core]\nread_script_metadata = true\nuser_locale = en_us\n[pyRevitDevTools.extension]\ndisabled = false\n");
            PyRevitConfigStore.SetFactory(() => new ConfigurationBuilder(false).AddIniConfiguration(configPath).Build());
            pyRevitExtensionParser.PyRevitConfig.ClearCache();
            pyRevitExtensionParser.ExtensionParser.ClearAllCaches();
        }

        [TearDown]
        public virtual void BaseTearDown()
        {
            PyRevitConfigStore.Reset();
            pyRevitExtensionParser.PyRevitConfig.ClearCache();
            pyRevitExtensionParser.ExtensionParser.ClearAllCaches();
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
