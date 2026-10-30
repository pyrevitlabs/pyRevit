using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies attachment replacement ordering, temporary-file cleanup, and bulk failure reporting.
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AttachmentManifestTests : IDisposable {
    private readonly string directory = Path.Combine(Path.GetTempPath(), "pyRevit-attach-tests-" + Guid.NewGuid());

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
        RevitAddons.CreateManifestFile(2026, "pyRevit.addin", PyRevitConsts.AddinName, "missing-loader.dll",
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
            Assert.Equal(PyRevitConsts.AddinName, new RevitAddonManifest(stagedManifest).Name);
            File.Delete(previousManifest);
            detached = true;
        });

        Assert.True(detached);
        Assert.False(File.Exists(previousManifest));
        Assert.Equal(PyRevitConsts.AddinName, new RevitAddonManifest(target).Name);
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

        Assert.Equal(PyRevitConsts.AddinName, new RevitAddonManifest(target).Name);
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
        Action<int> attach = year => {
            attemptedYears.Add(year);
            if (year != 2026)
                throw new IOException("blocked " + year);
            CreateManifest(directory);
        };

        var exception = Assert.Throws<PyRevitException>(() =>
            PyRevitAttachments.AttachToAll(new[] { 2025, 2026, 2026, 2027 }, attach));

        Assert.Contains("Revit 2025: blocked 2025", exception.Message);
        Assert.Contains("Revit 2027: blocked 2027", exception.Message);
        Assert.Equal(new[] { 2025, 2026, 2027 }, attemptedYears);
        Assert.True(File.Exists(Path.Combine(directory, "pyRevit.addin")));
    }

    /// <summary>
    ///     Verifies that successful bulk attachment completes without a failure report.
    /// </summary>
    [Fact]
    public void AttachToAllReturnsNormallyWhenEveryYearSucceeds() {
        var attemptedYears = new List<int>();
        PyRevitAttachments.AttachToAll(new[] { 2025, 2026 }, attemptedYears.Add);

        Assert.Equal(new[] { 2025, 2026 }, attemptedYears);
    }

    /// <summary>
    ///     Verifies that every scope is attempted and every failed deletion is reported.
    /// </summary>
    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    [InlineData(true, true)]
    public void RemoveManifestAttemptsBothScopesWhenDeletionsFail(bool lockCurrentUser, bool lockAllUsers) {
        var addinName = "pyRevit-attach-tests-" + Guid.NewGuid();
        var currentUser = RevitAddons.GetRevitAddonsFilePath(2026, addinName);
        var allUsers = RevitAddons.GetRevitAddonsFilePath(2026, addinName, allusers: true);
        try {
            RevitAddons.CreateManifestFile(2026, addinName, addinName, "missing-loader.dll",
                "test-id", "Loader.Application", "TEST");
            RevitAddons.CreateManifestFile(2026, addinName, addinName, "missing-loader.dll",
                "test-id", "Loader.Application", "TEST", allusers: true);
            using (lockCurrentUser ? File.Open(currentUser, FileMode.Open, FileAccess.Read, FileShare.Read) : null)
            using (lockAllUsers ? File.Open(allUsers, FileMode.Open, FileAccess.Read, FileShare.Read) : null) {
                var exception = Assert.Throws<PyRevitException>(() =>
                    RevitAddons.RemoveManifestFile(2026, addinName, currentAndAllUsers: true));
                if (lockCurrentUser)
                    Assert.Contains(currentUser, exception.Message);
                else
                    Assert.False(File.Exists(currentUser));
                if (lockAllUsers)
                    Assert.Contains(allUsers, exception.Message);
                else
                    Assert.False(File.Exists(allUsers));
            }
        }
        finally {
            if (File.Exists(currentUser))
                File.Delete(currentUser);
            if (File.Exists(allUsers))
                File.Delete(allUsers);
        }
    }

    /// <summary>
    ///     Verifies that attach removes expired manifests with a nonstandard filename before installing its replacement.
    /// </summary>
    [Fact]
    public void AttachRemovesExistingManifestBeforeInstallingReplacement() {
        const int revitYear = 2099;
        var addonDirectory = RevitAddons.GetRevitAddonsFolder(revitYear);
        var target = RevitAddons.GetRevitAddonsFilePath(revitYear, PyRevitConsts.AddinFileName);
        var previousManifest = Path.Combine(addonDirectory, "expired-clone.addin");
        Assert.False(Directory.Exists(addonDirectory));
        Directory.CreateDirectory(PyRevitClone.GetPyRevitPath(directory));
        File.WriteAllText(Path.Combine(directory, "pyRevitfile"), """
            [engines.DEFAULT]
            kernel = "ironpython"
            version = 2712
            path = "IPY2712PR"
            description = "Attachment test engine"
            """);
        var clone = new PyRevitClone(directory, "attach-test");
        try {
            CreateManifest(addonDirectory);
            File.Move(target, previousManifest);

            PyRevitAttachments.Attach(revitYear, clone, PyRevitEngineVersion.Default);

            Assert.False(File.Exists(previousManifest));
            Assert.Equal(PyRevitConsts.AddinName, new RevitAddonManifest(target).Name);
            Assert.Empty(Directory.GetFiles(addonDirectory, "*.tmp"));
        }
        finally {
            if (Directory.Exists(addonDirectory))
                Directory.Delete(addonDirectory, true);
        }
    }

    /// <summary>
    ///     Verifies that a locked staging file cannot replace the original attachment failure with a cleanup error.
    /// </summary>
    [Fact]
    public void StagingCleanupDoesNotMaskTheOriginalFailure() {
        FileStream stagedStream = null;
        try {
            var exception = Assert.Throws<UnauthorizedAccessException>(() => CreateManifest(directory, () => {
                var stagedFile = Assert.Single(Directory.GetFiles(directory, "pyRevit-manifest-*.tmp"));
                stagedStream = File.Open(stagedFile, FileMode.Open, FileAccess.Read, FileShare.None);
                throw new UnauthorizedAccessException("original detach failure");
            }));

            Assert.Equal("original detach failure", exception.Message);
        }
        finally {
            stagedStream?.Dispose();
        }
    }
}
