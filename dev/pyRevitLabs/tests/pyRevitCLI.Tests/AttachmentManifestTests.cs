using System.Reflection;
using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies attachment replacement ordering, temporary-file cleanup, and bulk failure reporting.
/// </summary>
public class AttachmentManifestTests : IDisposable {
    private readonly string directory = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());

    /// <summary>
    ///     Initializes a new instance of the <see cref="AttachmentManifestTests"/> class with an isolated temporary directory.
    /// </summary>
    public AttachmentManifestTests() {
        Directory.CreateDirectory(directory);
    }

    /// <inheritdoc />
    public void Dispose() {
        Directory.Delete(directory, true);
    }

    private void CreateManifest(string targetDirectory, Action beforeReplace = null) {
        RevitAddons.CreateManifestFile(2026, "pyRevit.addin", "pyRevit", "missing-loader.dll",
                                      "test-id", "Loader.Application", "TEST",
                                      addinPath: targetDirectory, beforeReplace: beforeReplace);
    }

    /// <summary>
    ///     Verifies that a destination rejecting staging leaves the working attachment untouched.
    /// </summary>
    [Fact]
    public void StagingFailureDoesNotRemoveTheWorkingManifest() {
        var previousManifest = Path.Combine(directory, "working.addin");
        File.WriteAllText(previousManifest, "working attachment");
        var blockedDirectory = Path.Combine(directory, "blocked");
        File.WriteAllText(blockedDirectory, "not a directory");
        var detached = false;

        Assert.ThrowsAny<IOException>(() => CreateManifest(blockedDirectory, () => {
            detached = true;
            File.Delete(previousManifest);
        }));

        Assert.False(detached);
        Assert.Equal("working attachment", File.ReadAllText(previousManifest));
        Assert.Empty(Directory.GetFiles(directory, "*.tmp"));
    }

    /// <summary>
    ///     Verifies that expired-clone attachments are removed only after staging closes and before installation.
    /// </summary>
    [Fact]
    public void DetachRunsAfterStagingClosesAndBeforeTheManifestIsInstalled() {
        var previousManifest = Path.Combine(directory, "expired-clone.addin");
        File.WriteAllText(previousManifest, "expired attachment");
        var target = Path.Combine(directory, "pyRevit.addin");
        var detached = false;

        CreateManifest(directory, () => {
            Assert.True(File.Exists(previousManifest));
            Assert.False(File.Exists(target));
            var stagedManifest = Assert.Single(Directory.GetFiles(directory, "*.tmp"));
            using (var stream = File.Open(stagedManifest, FileMode.Open, FileAccess.Read, FileShare.None))
                Assert.True(stream.Length > 0);
            Assert.Equal("pyRevit", new RevitAddonManifest(stagedManifest).Name);
            File.Delete(previousManifest);
            detached = true;
        });

        Assert.True(detached);
        Assert.False(File.Exists(previousManifest));
        Assert.Equal("pyRevit", new RevitAddonManifest(target).Name);
        Assert.Empty(Directory.GetFiles(directory, "*.tmp"));
    }

    /// <summary>
    ///     Verifies that replacement installs a readable manifest without temporary-file residue.
    /// </summary>
    [Fact]
    public void ExistingManifestIsReplacedWithoutLeavingTemporaryFiles() {
        var target = Path.Combine(directory, "pyRevit.addin");
        File.WriteAllText(target, "old manifest");

        CreateManifest(directory);

        Assert.Equal("pyRevit", new RevitAddonManifest(target).Name);
        Assert.Single(Directory.GetFiles(directory));
    }

    /// <summary>
    ///     Verifies that attachment-removal failures preserve the existing manifest and clean staging.
    /// </summary>
    [Fact]
    public void DetachFailureCleansTheStagedFile() {
        var target = Path.Combine(directory, "pyRevit.addin");
        File.WriteAllText(target, "working attachment");

        Assert.Throws<UnauthorizedAccessException>(() => CreateManifest(directory,
            () => throw new UnauthorizedAccessException("cannot detach")));

        Assert.Equal("working attachment", File.ReadAllText(target));
        Assert.Empty(Directory.GetFiles(directory, "*.tmp"));
    }

    /// <summary>
    ///     Verifies that an installation failure leaves no staged file.
    /// </summary>
    [Fact]
    public void InstallFailureCleansTheStagedFile() {
        Directory.CreateDirectory(Path.Combine(directory, "pyRevit.addin"));

        Assert.ThrowsAny<IOException>(() => CreateManifest(directory));

        Assert.Empty(Directory.GetFiles(directory, "*.tmp"));
    }

    /// <summary>
    ///     Verifies that bulk attachment attempts every distinct year before reporting all failures.
    /// </summary>
    [Fact]
    public void AttachToAllContinuesAfterFailuresAndReportsEveryFailedYear() {
        var attemptedYears = new List<int>();
        var attachToAll = typeof(PyRevitAttachments).GetMethod("AttachToAll",
            BindingFlags.NonPublic | BindingFlags.Static, null,
            new[] { typeof(IEnumerable<int>), typeof(Action<int>) }, null);
        Action<int> attach = year => {
            attemptedYears.Add(year);
            if (year != 2026)
                throw new IOException("blocked " + year);
            CreateManifest(directory);
        };

        var invocation = Assert.Throws<TargetInvocationException>(() => attachToAll.Invoke(null,
            new object[] { new[] { 2025, 2026, 2026, 2027 }, attach }));

        Assert.IsType<PyRevitException>(invocation.InnerException);
        Assert.Contains("Revit 2025: blocked 2025", invocation.InnerException.Message);
        Assert.Contains("Revit 2027: blocked 2027", invocation.InnerException.Message);
        Assert.Equal(new[] { 2025, 2026, 2027 }, attemptedYears);
        Assert.True(File.Exists(Path.Combine(directory, "pyRevit.addin")));
    }

    /// <summary>
    ///     Verifies that successful bulk attachment completes without a failure report.
    /// </summary>
    [Fact]
    public void AttachToAllReturnsNormallyWhenEveryYearSucceeds() {
        var attemptedYears = new List<int>();
        var attachToAll = typeof(PyRevitAttachments).GetMethod("AttachToAll",
            BindingFlags.NonPublic | BindingFlags.Static, null,
            new[] { typeof(IEnumerable<int>), typeof(Action<int>) }, null);

        attachToAll.Invoke(null, new object[] { new[] { 2025, 2026 }, (Action<int>)attemptedYears.Add });

        Assert.Equal(new[] { 2025, 2026 }, attemptedYears);
    }
}
