using System;
using System.IO;
using System.Reflection;

using NUnit.Framework;

using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    /// <summary>Covers normalizing build version stamps, which drops the SDK-appended commit hash but keeps channel and other metadata, and reading them from assemblies.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    public class PyRevitBuildVersionTests {
        private const string CommitHash = "0746b7c45feca2ad0a1efaa9232585b0402a3980";

        /// <summary>The commit hash the SDK appends after the build number is dropped from the build metadata.</summary>
        [Test]
        public void Normalize_DropsSdkAppendedCommitHash() {
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273+1554." + CommitHash), Is.EqualTo("7.0.0.26273+1554"));
        }

        /// <summary>Build metadata that is only a commit hash is dropped together with the <c>+</c>.</summary>
        [Test]
        public void Normalize_DropsCommitHashAfterPlus() {
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273+" + CommitHash), Is.EqualTo("7.0.0.26273"));
        }

        /// <summary>Build metadata without a commit hash is kept unchanged.</summary>
        [Test]
        public void Normalize_KeepsPlainBuildMetadata() {
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26237+2139"), Is.EqualTo("7.0.0.26237+2139"));
        }

        /// <summary>Every build metadata identifier is kept except a trailing commit hash.</summary>
        [Test]
        public void Normalize_KeepsEveryMetadataIdentifierButTheCommitHash() {
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273+1554.2"), Is.EqualTo("7.0.0.26273+1554.2"));
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273+1554.2." + CommitHash), Is.EqualTo("7.0.0.26273+1554.2"));
        }

        /// <summary>A channel suffix such as <c>-wip</c> is kept while the commit hash is dropped.</summary>
        [Test]
        public void Normalize_KeepsChannelSuffix() {
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273-wip+1554." + CommitHash), Is.EqualTo("7.0.0.26273-wip+1554"));
        }

        /// <summary>A version without build metadata is returned unchanged.</summary>
        [Test]
        public void Normalize_KeepsVersionWithoutBuildMetadata() {
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273"), Is.EqualTo("7.0.0.26273"));
        }

        /// <summary>Surrounding whitespace and line breaks are trimmed.</summary>
        [Test]
        public void Normalize_TrimsWhitespace() {
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion("  7.0.0.26273+1554\r\n"), Is.EqualTo("7.0.0.26273+1554"));
        }

        /// <summary>Null, empty and whitespace-only versions normalize to null.</summary>
        [Test]
        public void Normalize_UnusableValuesReturnNull() {
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion(null), Is.Null);
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion(""), Is.Null);
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion("   "), Is.Null);
        }

        /// <summary>A trailing <c>+</c> with no build metadata is dropped.</summary>
        [Test]
        public void Normalize_DropsEmptyBuildMetadata() {
            Assert.That(PyRevitBuildVersion.NormalizeInformationalVersion("7.0.0.26273+"), Is.EqualTo("7.0.0.26273"));
        }

        /// <summary>A loaded assembly reports its informational version without the commit hash, starting with a parsable version.</summary>
        [Test]
        public void FromAssembly_ReadsLoadedAssemblyStamp() {
            var assembly = typeof(PyRevitBuildVersionTests).Assembly;

            var version = PyRevitBuildVersion.FromAssembly(assembly);

            Assert.That(version, Is.Not.Null, "The test assembly must carry an informational version.");
            Assert.That(version.Contains(CommitHash), Is.False, "The commit hash must not be part of the reported version: " + version);
            Assert.That(Version.TryParse(
                    version.Split('+')[0],
                    out _), Is.True, "Reported version must start with a parsable version: " + version);
        }

        /// <summary>A null assembly reports no version.</summary>
        [Test]
        public void FromAssembly_MissingAssemblyReturnsNull() {
            Assert.That(PyRevitBuildVersion.FromAssembly(null), Is.Null);
        }

        /// <summary>An assembly file on disk reports its informational version without the commit hash.</summary>
        [Test]
        public void FromAssemblyFile_ReadsStampFromDisk() {
            var assemblyPath = typeof(PyRevitBuildVersionTests).Assembly.Location;

            var version = PyRevitBuildVersion.FromAssemblyFile(assemblyPath);

            Assert.That(version, Is.Not.Null, "Must read the version from the assembly on disk: " + assemblyPath);
            Assert.That(version.Contains(CommitHash), Is.False, "The commit hash must not be part of the reported version: " + version);
        }

        /// <summary>A null, empty or nonexistent assembly path reports no version.</summary>
        [Test]
        public void FromAssemblyFile_MissingFileReturnsNull() {
            Assert.That(PyRevitBuildVersion.FromAssemblyFile(null), Is.Null);
            Assert.That(PyRevitBuildVersion.FromAssemblyFile(string.Empty), Is.Null);
            Assert.That(PyRevitBuildVersion.FromAssemblyFile(
                Path.Combine(Path.GetTempPath(), "no-such-pyrevit-build-7.0.0.26273.dll")), Is.Null);
        }

        /// <summary>A file that is not a PE image reports no version instead of throwing.</summary>
        [Test]
        public void FromAssemblyFile_NonAssemblyFileReturnsNull() {
            var notAnAssembly = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".dll");
            File.WriteAllText(notAnAssembly, "not a PE image");

            try {
                Assert.That(PyRevitBuildVersion.FromAssemblyFile(notAnAssembly), Is.Null);
            }
            finally {
                File.Delete(notAnAssembly);
            }
        }
    }
}
