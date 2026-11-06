using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies which launch directories <see cref="PyRevitLauncher.PruneAbandoned"/> removes.
/// </summary>
[Collection(CliGlobalState.Name)]
public class LaunchPruneTests : IDisposable {
    private const int NoSuchProcessId = 2147483000;

    private readonly string temp = Path.Combine(Path.GetTempPath(), "pyRevit-prune-tests-" + Guid.NewGuid());
    private readonly string previousTemp = Environment.GetEnvironmentVariable("TEMP");

    /// <summary>
    ///     Initializes a new instance of the <see cref="LaunchPruneTests"/> class with an isolated temporary folder.
    /// </summary>
    public LaunchPruneTests() {
        Directory.CreateDirectory(temp);
        Environment.SetEnvironmentVariable("TEMP", temp);
    }

    /// <inheritdoc />
    public void Dispose() {
        Environment.SetEnvironmentVariable("TEMP", previousTemp);
        Directory.Delete(temp, true);
    }

    private string CreateLaunch(string name, string processIdContent, bool old) {
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
    [Fact]
    public void ADirectoryWhoseProcessIsGoneIsPruned() {
        var directory = CreateLaunch("gone", NoSuchProcessId.ToString(), old: false);

        PyRevitLauncher.PruneAbandoned();

        Assert.False(Directory.Exists(directory));
    }

    /// <summary>
    ///     Verifies that a missing, empty or invalid process id file does not get a fresh directory pruned.
    /// </summary>
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("not a number")]
    public void AFreshDirectoryWithoutAReadableProcessIdIsKept(string processIdContent) {
        var directory = CreateLaunch("fresh", processIdContent, old: false);

        PyRevitLauncher.PruneAbandoned();

        Assert.True(Directory.Exists(directory));
    }

    /// <summary>
    ///     Verifies that a directory without a readable process id is pruned once it is a day old.
    /// </summary>
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("not a number")]
    public void AnOldDirectoryWithoutAReadableProcessIdIsPruned(string processIdContent) {
        var directory = CreateLaunch("old", processIdContent, old: true);

        PyRevitLauncher.PruneAbandoned();

        Assert.False(Directory.Exists(directory));
    }

    /// <summary>
    ///     Verifies that a directory with a file held open, as Revit holds its journal, is never pruned.
    /// </summary>
    [Theory]
    [InlineData(null, true)]
    [InlineData("", true)]
    [InlineData("2147483000", false)]
    public void ADirectoryWithAnOpenFileIsKept(string processIdContent, bool old) {
        var directory = CreateLaunch("running", processIdContent, old);
        using var journal = new FileStream(Path.Combine(directory, "journal.0001.txt"), FileMode.Create, FileAccess.Write, FileShare.Read);

        PyRevitLauncher.PruneAbandoned();

        Assert.True(Directory.Exists(directory));
        Assert.True(File.Exists(Path.Combine(directory, "pyRevit.addin")));
    }
}
