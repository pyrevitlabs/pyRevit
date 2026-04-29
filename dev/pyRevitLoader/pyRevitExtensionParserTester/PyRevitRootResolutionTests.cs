using System.IO;
using NUnit.Framework;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParserTest.TestHelpers;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Regression tests for the pyRevitRoot resolution ordering bug fixed in PR #3260.
    /// <para>
    /// The root cause was that <c>SeedEnvironmentDictionary()</c> ran before
    /// <c>_pyRevitRoot</c> was resolved, so <c>EnvDictionarySeeder.Seed()</c>
    /// received an empty string and both <c>ReadPyRevitVersion</c> and
    /// <c>ReadIPYVersion</c> returned "Unknown".
    /// </para>
    /// <para>
    /// These tests verify that <c>FindPyRevitRoot</c> correctly walks up from a
    /// <c>bin/</c> directory to the repo root, and that the version helpers return
    /// real values (not "Unknown") when a valid root is supplied.
    /// </para>
    /// </summary>
    [TestFixture]
    public class PyRevitRootResolutionTests : TempFileTestBase
    {
        // ──────────────────────────────────────────────────────────────
        //  FindPyRevitRoot: marker-file resolution
        // ──────────────────────────────────────────────────────────────

        [Test]
        public void FindPyRevitRoot_FromBinDir_ResolvesViaMarkerFile()
        {
            // Arrange: simulate the standard repo layout where the executing
            // assembly lives at {root}/bin/netcore/engines/IPY342/
            var root = TestTempDir;
            CreateFile("pyRevitfile", "");                       // marker file
            var binDir = CreateSubDirectory("bin/netcore/engines/IPY342");

            // Act
            var resolved = SessionManagerService.FindPyRevitRoot(binDir);

            // Assert
            Assert.IsNotNull(resolved, "FindPyRevitRoot must resolve a non-null root from bin dir");
            Assert.AreEqual(root, resolved,
                "FindPyRevitRoot must walk up to the directory containing pyRevitfile");
        }

        [Test]
        public void FindPyRevitRoot_FromBinDir_ResolvesViaPyRevitLib()
        {
            // Arrange: some installs may lack pyRevitfile but still have pyrevitlib/
            var root = TestTempDir;
            CreateSubDirectory("pyrevitlib");                    // lib directory marker
            var binDir = CreateSubDirectory("bin/netfx/engines/IPY2712PR");

            // Act
            var resolved = SessionManagerService.FindPyRevitRoot(binDir);

            // Assert
            Assert.IsNotNull(resolved, "FindPyRevitRoot must resolve via pyrevitlib/ directory");
            Assert.AreEqual(root, resolved);
        }

        [Test]
        public void FindPyRevitRoot_NoMarkers_ReturnsNull()
        {
            // Arrange: an empty temp tree with no pyRevit markers
            var binDir = CreateSubDirectory("some/deep/path");

            // Act
            var resolved = SessionManagerService.FindPyRevitRoot(binDir);

            // Assert
            Assert.IsNull(resolved,
                "FindPyRevitRoot must return null when no marker is found");
        }

        [Test]
        public void FindPyRevitRoot_NullHintPath_ReturnsNull()
        {
            // Act
            var resolved = SessionManagerService.FindPyRevitRoot((string?)null);

            // Assert
            Assert.IsNull(resolved,
                "FindPyRevitRoot must gracefully handle null hint paths");
        }

        [Test]
        public void FindPyRevitRoot_EmptyHintPath_ReturnsNull()
        {
            // Act
            var resolved = SessionManagerService.FindPyRevitRoot(string.Empty);

            // Assert
            Assert.IsNull(resolved,
                "FindPyRevitRoot must gracefully handle empty hint paths");
        }

        // ──────────────────────────────────────────────────────────────
        //  ReadPyRevitVersion: version file read
        // ──────────────────────────────────────────────────────────────

        [Test]
        public void ReadPyRevitVersion_EmptyRoot_ReturnsUnknown()
        {
            // This is the exact scenario that caused the bug: _pyRevitRoot was
            // empty when SeedEnvironmentDictionary() called ReadPyRevitVersion.
            Assert.AreEqual("Unknown", EnvDictionarySeeder.ReadPyRevitVersion(string.Empty),
                "An empty root must yield 'Unknown' — this was the pre-fix bug path");
        }

        [Test]
        public void ReadPyRevitVersion_NullRoot_ReturnsUnknown()
        {
            Assert.AreEqual("Unknown", EnvDictionarySeeder.ReadPyRevitVersion(null!),
                "A null root must yield 'Unknown'");
        }

        [Test]
        public void ReadPyRevitVersion_ValidRoot_ReturnsActualVersion()
        {
            // Arrange: create the version file at pyrevitlib/pyrevit/version
            var expectedVersion = "6.1.0.0";
            CreateFile(Path.Combine("pyrevitlib", "pyrevit", "version"), expectedVersion);

            // Act
            var version = EnvDictionarySeeder.ReadPyRevitVersion(TestTempDir);

            // Assert
            Assert.AreEqual(expectedVersion, version,
                "ReadPyRevitVersion must return the content of the version file");
        }

        [Test]
        public void ReadPyRevitVersion_ValidRoot_TrimsWhitespace()
        {
            // Version files may have trailing newlines
            CreateFile(Path.Combine("pyrevitlib", "pyrevit", "version"), "  6.3.0.26092+0010\n");

            var version = EnvDictionarySeeder.ReadPyRevitVersion(TestTempDir);

            Assert.AreEqual("6.3.0.26092+0010", version,
                "ReadPyRevitVersion must trim surrounding whitespace");
        }

        [Test]
        public void ReadPyRevitVersion_MissingVersionFile_ReturnsUnknown()
        {
            // Root exists but pyrevitlib/pyrevit/version is absent
            CreateSubDirectory("pyrevitlib/pyrevit");

            var version = EnvDictionarySeeder.ReadPyRevitVersion(TestTempDir);

            Assert.AreEqual("Unknown", version,
                "A missing version file must degrade to 'Unknown'");
        }

        // ──────────────────────────────────────────────────────────────
        //  ReadIPYVersion: empty root scenario
        // ──────────────────────────────────────────────────────────────

        [Test]
        public void ReadIPYVersion_EmptyRoot_ReturnsUnknown()
        {
            // Same bug scenario as ReadPyRevitVersion: empty root means no
            // candidate directories are checked except the executing assembly dir.
            // In a test environment, IronPython.dll won't be beside the test runner,
            // so this should return "Unknown".
            var version = EnvDictionarySeeder.ReadIPYVersion(string.Empty);

            Assert.AreEqual("Unknown", version,
                "An empty root with no IronPython.dll beside the test runner must yield 'Unknown'");
        }

        // ──────────────────────────────────────────────────────────────
        //  End-to-end: FindPyRevitRoot → ReadPyRevitVersion pipeline
        // ──────────────────────────────────────────────────────────────

        [Test]
        public void EndToEnd_BinDir_ResolvesRoot_ThenReadsVersion()
        {
            // Arrange: full standard layout simulation
            //   {root}/pyRevitfile
            //   {root}/pyrevitlib/pyrevit/version  →  "6.1.0.0"
            //   {root}/bin/netcore/engines/IPY342/ ← executing assembly would be here
            CreateFile("pyRevitfile", "");
            CreateFile(Path.Combine("pyrevitlib", "pyrevit", "version"), "6.1.0.0");
            var binDir = CreateSubDirectory("bin/netcore/engines/IPY342");

            // Act: mimic InitializeScriptExecutor() → SeedEnvironmentDictionary() sequence
            var pyRevitRoot = SessionManagerService.FindPyRevitRoot(binDir);
            var version = EnvDictionarySeeder.ReadPyRevitVersion(pyRevitRoot ?? string.Empty);

            // Assert: the fix ensures pyRevitRoot is resolved before Seed() runs
            Assert.IsNotNull(pyRevitRoot, "pyRevitRoot must be non-null after FindPyRevitRoot");
            Assert.AreNotEqual("Unknown", version,
                "With a resolved pyRevitRoot, ReadPyRevitVersion must NOT return 'Unknown'");
            Assert.AreEqual("6.1.0.0", version);
        }

        [Test]
        public void EndToEnd_WithoutEarlyResolution_ProducesUnknown()
        {
            // Demonstrate the pre-fix bug: if _pyRevitRoot is not resolved early,
            // SeedEnvironmentDictionary receives empty string → "Unknown".
            string? pyRevitRoot = null;   // simulates the old code path (not yet resolved)
            var version = EnvDictionarySeeder.ReadPyRevitVersion(pyRevitRoot ?? string.Empty);

            Assert.AreEqual("Unknown", version,
                "Without early resolution, ReadPyRevitVersion returns 'Unknown' — the original bug");
        }
    }
}
