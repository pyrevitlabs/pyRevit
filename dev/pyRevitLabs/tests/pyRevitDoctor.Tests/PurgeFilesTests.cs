using pyRevitDoctor;

namespace pyRevitDoctor.Tests;

/// <summary>
/// Runs the folder and manifest part of <c>purge-files</c> against a temporary fake profile.
/// </summary>
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public sealed class PurgeFilesTests : IDisposable {
    private readonly string root = Path.Combine(Path.GetTempPath(), "pyrevit-doctor-tests-" + Guid.NewGuid().ToString("N"));
    private readonly MachineLocations locations;

    public PurgeFilesTests() {
        locations = new MachineLocations {
            AppData = Path.Combine(root, "Roaming"),
            LocalAppData = Path.Combine(root, "Local"),
            ProgramFiles = Path.Combine(root, "Program Files"),
            ProgramData = Path.Combine(root, "ProgramData"),
            Documents = Path.Combine(root, "Documents"),
        };
        Directory.CreateDirectory(locations.Documents);
    }

    public void Dispose() {
        if (Directory.Exists(root)) {
            foreach (var file in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories))
                File.SetAttributes(file, FileAttributes.Normal);
            Directory.Delete(root, recursive: true);
        }
    }

    private string Create(params string[] relativePath) {
        var path = Path.Combine(new[] { root }.Concat(relativePath).ToArray());
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        File.WriteAllText(path, "x");
        return path;
    }

    private (PurgeSession Session, StringWriter Output, bool Completed) Purge(PurgeOptions options) {
        var output = new StringWriter();
        var session = new PurgeSession(options, output);
        var completed = PurgeFiles.PurgeFilesAndFolders(session, locations);
        return (session, output, completed);
    }

    [Fact]
    public void DeletesMarkedFoldersAndManifestsAndBacksUpTheConfig() {
        var cloneMarker = Create("Roaming", "pyRevit-Master", "pyRevitfile");
        var readOnlyFile = Create("Roaming", "pyRevit-Master", ".git", "objects", "pack.idx");
        File.SetAttributes(readOnlyFile, FileAttributes.ReadOnly);
        var config = Create("Roaming", "pyRevit", "pyRevit_config.ini");
        var manifest = Create("Roaming", "Autodesk", "Revit", "Addins", "2025", "pyRevit.addin");
        var otherManifest = Create("Roaming", "Autodesk", "Revit", "Addins", "2025", "Other.addin");

        var (session, output, completed) = Purge(new PurgeOptions());

        Assert.True(completed);
        Assert.False(Directory.Exists(Path.GetDirectoryName(cloneMarker)));
        Assert.False(Directory.Exists(Path.GetDirectoryName(config)));
        Assert.False(File.Exists(manifest));
        Assert.True(File.Exists(otherManifest));
        Assert.Single(Directory.GetFiles(locations.Documents, "pyRevit_config.user.*.ini"));
        Assert.Equal(0, session.FailedCount);
        Assert.Contains("Skipped (not found)", output.ToString());
    }

    /// <summary>
    /// A folder that merely has the install name but holds no pyRevit marker is not ours to delete.
    /// </summary>
    [Fact]
    public void FolderWithoutMarkerIsSkipped() {
        var unrelated = Create("Program Files", "pyRevit CLI", "notes.txt");

        var (session, output, _) = Purge(new PurgeOptions());

        Assert.True(File.Exists(unrelated));
        Assert.Contains("Skipped (no pyRevit marker)", output.ToString());
        Assert.Equal(0, session.DeletedCount);
    }

    [Fact]
    public void DryRunChangesNothingAndStillReportsDeletions() {
        var config = Create("Roaming", "pyRevit", "pyRevit_config.ini");
        var clone = Create("Roaming", "pyRevit-Master", "pyRevitfile");

        var (session, output, _) = Purge(new PurgeOptions { DryRun = true });

        Assert.True(File.Exists(config));
        Assert.True(File.Exists(clone));
        Assert.Empty(Directory.GetFiles(locations.Documents));
        Assert.Equal(2, session.DeletedCount);
        Assert.Contains("Fake Deleted", output.ToString());
        Assert.False(session.Exists(Path.GetDirectoryName(clone)));
    }

    [Fact]
    public void KeepConfigPreservesTheConfigAndSkipsTheBackup() {
        var config = Create("Roaming", "pyRevit", "pyRevit_config.ini");
        var cache = Create("Roaming", "pyRevit", "2025", "cache.db");

        Purge(new PurgeOptions { KeepConfig = true });

        Assert.True(File.Exists(config));
        Assert.False(File.Exists(cache));
        Assert.Empty(Directory.GetFiles(locations.Documents));
    }

    /// <summary>
    /// A failed backup must stop the purge before anything is deleted.
    /// </summary>
    [Fact]
    public void FailedBackupDeletesNothing() {
        var config = Create("Roaming", "pyRevit", "pyRevit_config.ini");
        var clone = Create("Roaming", "pyRevit-Master", "pyRevitfile");
        Directory.Delete(locations.Documents);
        File.WriteAllText(locations.Documents, "not a folder");

        var (session, _, completed) = Purge(new PurgeOptions());

        Assert.False(completed);
        Assert.Equal(1, session.FailedCount);
        Assert.True(File.Exists(config));
        Assert.True(File.Exists(clone));
    }

    /// <summary>
    /// A config next to <c>pyRevitfile</c> in an install folder is the active one (clone-local config),
    /// so it must be backed up before the folder goes.
    /// </summary>
    [Fact]
    public void LocalConfigInInstallFolderIsBackedUp() {
        Create("Roaming", "pyRevit-Master", "pyRevitfile");
        var localConfig = Create("Roaming", "pyRevit-Master", "pyRevit_config.ini");

        Purge(new PurgeOptions());

        Assert.False(File.Exists(localConfig));
        Assert.Single(Directory.GetFiles(locations.Documents, "pyRevit_config.install*.ini"));
    }

    [Fact]
    public void KeepConfigPreservesLocalConfigInInstallFolder() {
        Create("Roaming", "pyRevit-Master", "pyRevitfile");
        var localConfig = Create("Roaming", "pyRevit-Master", "pyRevit_config.ini");

        Purge(new PurgeOptions { KeepConfig = true });

        Assert.True(File.Exists(localConfig));
        Assert.False(File.Exists(Path.Combine(root, "Roaming", "pyRevit-Master", "pyRevitfile")));
        Assert.Empty(Directory.GetFiles(locations.Documents));
    }

    /// <summary>
    /// A folder emptied except for the kept config is a cleared install, so its uninstall record
    /// is stale rather than pointing at a live install.
    /// </summary>
    [Fact]
    public void FolderEmptiedExceptForKeptConfigNoLongerCountsAsInstalled() {
        Create("Roaming", "pyRevit-Master", "pyRevitfile");
        var localConfig = Create("Roaming", "pyRevit-Master", "pyRevit_config.ini");
        var installDirectory = Path.GetDirectoryName(localConfig);

        var (session, _, _) = Purge(new PurgeOptions { KeepConfig = true });

        Assert.True(Directory.Exists(installDirectory));
        Assert.False(session.Exists(installDirectory));
    }

    /// <summary>
    /// A config kept by one run has lost its <c>pyRevitfile</c> but is still deleted by the next
    /// run, so that run must back it up.
    /// </summary>
    [Fact]
    public void ConfigKeptByEarlierRunIsBackedUpByTheNextRun() {
        Create("Roaming", "pyRevit-Master", "pyRevitfile");
        var localConfig = Create("Roaming", "pyRevit-Master", "pyRevit_config.ini");
        Purge(new PurgeOptions { KeepConfig = true });

        Purge(new PurgeOptions());

        Assert.False(File.Exists(localConfig));
        Assert.Single(Directory.GetFiles(locations.Documents, "pyRevit_config.install*.ini"));
    }
}
