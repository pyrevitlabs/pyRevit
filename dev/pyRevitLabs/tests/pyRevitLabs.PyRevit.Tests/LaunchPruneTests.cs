using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Tests;

/// <summary>
///     Verifies which launch directories <see cref="PyRevitLauncher.PruneAbandoned"/> removes.
/// </summary>
[TestFixture]
[NonParallelizable]
[Category("HostFree")]
[Category("Integration")]
public class LaunchPruneTests {
    private const int NoSuchProcessId = 2147483000;

    private readonly string temp = Path.Combine(Path.GetTempPath(), "pyRevit-prune-tests-" + Guid.NewGuid());
    private readonly string? previousTemp = Environment.GetEnvironmentVariable("TEMP");
    private readonly string? previousTmp = Environment.GetEnvironmentVariable("TMP");

    /// <summary>
    ///     Points the temp folder, and so the launch root, at an isolated folder.
    /// </summary>
    /// <exception cref="InvalidOperationException">The launch root does not resolve under the isolated folder, so pruning could reach real launch directories.</exception>
    [SetUp]
    public void SetUp() {
        Directory.CreateDirectory(temp);
        Environment.SetEnvironmentVariable("TEMP", temp);
        Environment.SetEnvironmentVariable("TMP", temp);
        if (!PyRevitLauncher.LaunchRoot.StartsWith(temp, StringComparison.OrdinalIgnoreCase)) {
            TearDown();
            throw new InvalidOperationException("The launch root does not resolve under the isolated temp folder: " + PyRevitLauncher.LaunchRoot);
        }
    }

    /// <summary>
    ///     Restores the process-wide state the test changed and deletes its folder.
    /// </summary>
    [TearDown]
    public void TearDown() {
        Environment.SetEnvironmentVariable("TEMP", previousTemp);
        Environment.SetEnvironmentVariable("TMP", previousTmp);
        Directory.Delete(temp, true);
    }

    private string CreateLaunch(string name, string? processIdContent, bool old) {
        var directory = Path.Combine(PyRevitLauncher.LaunchRoot, name);
        Directory.CreateDirectory(directory);
        File.WriteAllText(Path.Combine(directory, "pyRevit.addin"), "manifest");
        if (processIdContent != null)
            File.WriteAllText(Path.Combine(directory, "pid"), processIdContent);
        if (old)
            Directory.SetCreationTimeUtc(directory, DateTime.UtcNow.AddDays(-2));
        return directory;
    }

    /// <summary>
    ///     Verifies that a launch whose recorded process is gone is removed.
    /// </summary>
    [Test]
    public void ADirectoryWhoseProcessIsGoneIsPruned() {
        var directory = CreateLaunch("gone", NoSuchProcessId.ToString(), old: false);

        PyRevitLauncher.PruneAbandoned();

        Assert.That(Directory.Exists(directory), Is.False);
    }

    /// <summary>
    ///     Verifies that a missing, empty or invalid process id file does not get a fresh directory pruned.
    /// </summary>
    [TestCase(null)]
    [TestCase("")]
    [TestCase("not a number")]
    public void AFreshDirectoryWithoutAReadableProcessIdIsKept(string? processIdContent) {
        var directory = CreateLaunch("fresh", processIdContent, old: false);

        PyRevitLauncher.PruneAbandoned();

        Assert.That(Directory.Exists(directory), Is.True);
    }

    /// <summary>
    ///     Verifies that a directory without a readable process id is pruned once it is a day old.
    /// </summary>
    [TestCase(null)]
    [TestCase("")]
    [TestCase("not a number")]
    public void AnOldDirectoryWithoutAReadableProcessIdIsPruned(string? processIdContent) {
        var directory = CreateLaunch("old", processIdContent, old: true);

        PyRevitLauncher.PruneAbandoned();

        Assert.That(Directory.Exists(directory), Is.False);
    }

    /// <summary>
    ///     Verifies that pruning never probes the manifest, which a starting session reads without write or exclusive access.
    /// </summary>
    [Test]
    public void AnOpenManifestDoesNotKeepADirectoryWhoseProcessIsGone() {
        var directory = CreateLaunch("manifest-read", NoSuchProcessId.ToString(), old: false);
        using var reader = new FileStream(Path.Combine(directory, "pyRevit.addin"), FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);

        PyRevitLauncher.PruneAbandoned();

        Assert.That(Directory.Exists(directory), Is.False);
    }

    /// <summary>
    ///     Verifies that a directory with a journal file held open, as Revit holds it, is never pruned.
    /// </summary>
    [TestCase(null, true)]
    [TestCase("", true)]
    [TestCase("2147483000", false)]
    public void ADirectoryWithAnOpenFileIsKept(string? processIdContent, bool old) {
        var directory = CreateLaunch("running", processIdContent, old);
        using var journal = new FileStream(Path.Combine(directory, "journal.0001.txt"), FileMode.Create, FileAccess.Write, FileShare.Read);

        PyRevitLauncher.PruneAbandoned();

        Assert.That(Directory.Exists(directory), Is.True);
        Assert.That(File.Exists(Path.Combine(directory, "pyRevit.addin")), Is.True);
    }
}
